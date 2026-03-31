import cv2
import time
import threading
import mediapipe as mp
from flask import Flask, render_template, Response, jsonify

from alarm import trigger_alarm
from cloud_alert import send_telegram_alert

app = Flask(__name__)

# Global System State
state = {
    "armed": True,
    "last_trigger_time": 0,
    "cooldown_seconds": 5.0,
    "logs": ["System Online & Monitoring..."] # Stores the last 5 logs
}

def add_log(message):
    timestamp = time.strftime("%H:%M:%S")
    formatted_msg = f"[{timestamp}] {message}"
    state["logs"].insert(0, formatted_msg)
    if len(state["logs"]) > 5:
        state["logs"].pop()

def generate_frames():
    """ Video Streaming Generator Function that runs MediaPipe """
    cap = cv2.VideoCapture(0)
    
    # Grab dimensions
    ret, frame = cap.read()
    if not ret:
        return
        
    height, width, _ = frame.shape
    
    # Define Tree Zone (right side rectangle)
    box_w, box_h = 200, 300
    tree_box = (int(width - box_w - 50), int(height/2 - box_h/2), int(width - 50), int(height/2 + box_h/2))
    
    # Setup AI
    mp_hands = mp.solutions.hands
    mp_drawing = mp.solutions.drawing_utils
    hands_ai = mp_hands.Hands(max_num_hands=2, min_detection_confidence=0.7, min_tracking_confidence=0.7)

    while True:
        success, frame = cap.read()
        if not success:
            break
            
        if state["armed"]:
            # AI Processing
            image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = hands_ai.process(image_rgb)
            
            box_color = (0, 255, 0)
            touch_detected = False

            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                    for lm in hand_landmarks.landmark:
                        px, py = int(lm.x * width), int(lm.y * height)
                        if tree_box[0] <= px <= tree_box[2] and tree_box[1] <= py <= tree_box[3]:
                            touch_detected = True
                            break
                    if touch_detected: break

            if touch_detected:
                box_color = (0, 0, 255) # Turn Red
                
            # Draw Zone Box
            cv2.rectangle(frame, (tree_box[0], tree_box[1]), (tree_box[2], tree_box[3]), box_color, 4)
            cv2.putText(frame, "Tree Zone", (tree_box[0], tree_box[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, box_color, 2)

            # Security Trigger Payload
            if touch_detected and (time.time() - state["last_trigger_time"] > state["cooldown_seconds"]):
                state["last_trigger_time"] = time.time()
                add_log("⚠️ ALERT: AI Detected Hand in Tree Zone!")
                
                # Alarm
                trigger_alarm()
                
                # Visual Warning stamp
                cv2.putText(frame, "AI TRIGGER: INTRUDER DETECTED", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
                
                # Save & Send image asynchronously so video stream doesn't freeze
                photo_path = 'ai_intruder_catch.jpg'
                cv2.imwrite(photo_path, frame)
                
                def send_cloud_async():
                    add_log("☁️ Dispatching Telegram alert...")
                    msg = "🚨 VIRTUAL AI PERIMETER BREACH! 🚨\nThe AI detected a hand touching the plant."
                    send_telegram_alert(msg, photo_path)
                    add_log("Telegram alert sent successfully.")
                    
                threading.Thread(target=send_cloud_async).start()

        else:
            # System is Disarmed: Just show video with text
            cv2.putText(frame, "SYSTEM DISARMED (AI OFFLINE)", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)

        # Encode Frame to JPEG for Web Streaming
        ret, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()

        # Yield stream
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

    cap.release()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/status')
def status():
    return jsonify({
        "armed": state["armed"],
        "logs": state["logs"]
    })

@app.route('/api/toggle_arm', methods=['POST'])
def toggle_arm():
    state["armed"] = not state["armed"]
    status_str = "ARMED" if state["armed"] else "DISARMED"
    add_log(f"System switched to {status_str} mode manually.")
    return jsonify({"armed": state["armed"]})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
