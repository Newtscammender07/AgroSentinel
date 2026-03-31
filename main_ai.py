import cv2
import time
import mediapipe as mp

# Import our custom modules
from alarm import trigger_alarm
from cloud_alert import send_telegram_alert

def main_ai():
    print("🎥 Initializing AI Hand Tracking security system...")
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("❌ Error: Could not open the webcam.")
        return

    # Grab the frame dimensions
    ret, frame = cap.read()
    if ret:
        height, width, _ = frame.shape
    else:
        print("❌ Error: Can't read from webcam.")
        return

    # Define the "Tree Zone" Box (Left, Top, Right, Bottom)
    # Let's put it on the right side of the screen where you'd angle the plant
    box_w = 200
    box_h = 300
    tree_box = (int(width - box_w - 50), int(height/2 - box_h/2), int(width - 50), int(height/2 + box_h/2))
    
    # Initialize MediaPipe Hand Tracking (tracking max 2 hands, 70% confidence)
    mp_hands = mp.solutions.hands
    mp_drawing = mp.solutions.drawing_utils
    hands_ai = mp_hands.Hands(
        max_num_hands=2,
        min_detection_confidence=0.7,
        min_tracking_confidence=0.7
    )

    print("=" * 50)
    print("🤖 AI TOUCH DETECTION ACTIVE 🤖")
    print("=" * 50)
    print("A green 'Tree Zone' box will appear on your screen.")
    print("If the AI sees a hand enter that box, it will trigger the alarm!")
    print("Press 'q' or 'ESC' to securely EXIT the system.")
    print("=" * 50)

    # Cooldown logic so it doesn't spam telegram every single camera frame (30 times a second)
    cooldown_seconds = 5.0
    last_trigger_time = 0

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # MediaPipe expects RGB images, OpenCV gives BGR
            image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = hands_ai.process(image_rgb)
            
            # Default state: draw the safe Green Tree Zone
            box_color = (0, 255, 0) # Green (BGR)
            touch_detected = False

            # Draw AI Hand Tracking if any hands are found
            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    # Draw the AI tracking nodes on the screen
                    mp_drawing.draw_landmarks(
                        frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                    
                    # Mathematical check: Did any of the 21 hand points touch the tree zone?
                    for lm in hand_landmarks.landmark:
                        # Convert AI coordinates (0.0 to 1.0) into pixel coordinates
                        pixel_x = int(lm.x * width)
                        pixel_y = int(lm.y * height)
                        
                        # Check collision with Tree Zone boundaries
                        if tree_box[0] <= pixel_x <= tree_box[2] and tree_box[1] <= pixel_y <= tree_box[3]:
                            touch_detected = True
                            break # Once we know it's a touch, no need to check other fingers
                    
                    if touch_detected:
                        break # Both hands trigger it

            # If the AI caught a touch
            if touch_detected:
                # Turn the box RED so you know it was tripped visually on screen
                box_color = (0, 0, 255) 
                
            # Actually draw our Tree Zone bounding box onto the frame so it shows up in the picture!
            cv2.rectangle(frame, (tree_box[0], tree_box[1]), (tree_box[2], tree_box[3]), box_color, 4)
            cv2.putText(frame, "Tree Zone", (tree_box[0], tree_box[1] - 10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, box_color, 2)
                        
            # Trigger Alarm and Cloud Logic
            if touch_detected:
                # Enforce the cooldown so we aren't sending 100 photos a minute
                if time.time() - last_trigger_time > cooldown_seconds:
                    print("\n🤖⚠️ AI DETECTED HUMAN TOUCH IN THE PROTECTED ZONE! ⚠️")
                    last_trigger_time = time.time()
                    
                    # 1. Trigger the loud alarm
                    trigger_alarm()
                    
                    # Draw a warning directly onto the video frame *before* snapping it
                    cv2.putText(frame, "AI TRIGGER: INTRUDER HAND DETECTED", (50, 50), 
                                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
                    
                    # 2. Extract current Live Frame (which now includes the drawn skeleton, tree box, and red warning)
                    photo_path = 'ai_intruder_catch.jpg'
                    cv2.imwrite(photo_path, frame)
                    print(f"📸 Captured proof of intrusion as {photo_path}")
                    
                    # 3. Send to Cloud (Telegram)
                    alert_msg = "🚨 VIRTUAL AI PERIMETER BREACH! 🚨\nThe AI detected a hand touching the plant. See attached evidence."
                    send_telegram_alert(alert_msg, photo_path)
                    
                    print("✅ AI Security Response Complete. 5s cooldown active...")

            # Display the final AI-processed image
            cv2.imshow("AgroSentinel AI Security View", frame)

            # Check for quit commands
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == 27:
                print("\nDeactivating AI System. Goodbye!")
                break
                
    except Exception as e:
        print(f"An error occurred in AI processing: {e}")
        
    finally:
        cap.release()
        cv2.destroyAllWindows()
        hands_ai.close()

if __name__ == "__main__":
    main_ai()
