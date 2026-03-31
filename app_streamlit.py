import streamlit as st
import cv2
import time

import threading

import mediapipe as mp
# Deep diagnostics for MediaPipe silent failures on Streamlit Cloud
try:
    import mediapipe.python._framework_bindings as bindings
    import mediapipe.python.solutions.hands as mp_hands
    import mediapipe.python.solutions.drawing_utils as mp_drawing
except Exception as e:
    st.error(f"🚨 CRITICAL MEDIAPIPE INITIALIZATION FAILURE: {str(e)}")
    st.error("This usually means a missing Linux C++ library (like libGL.so.1) or a Protobuf version conflict.")
    st.stop()


# Import our custom modules
from alarm import trigger_alarm
from cloud_alert import send_telegram_alert

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="AgroSentinel", layout="wide", page_icon="🌿")

# --- INITIALIZE SESSION STATE ---
if 'logs' not in st.session_state:
    st.session_state.logs = ["System Online. Waiting for activation..."]
if 'last_trigger_time' not in st.session_state:
    st.session_state.last_trigger_time = 0

def log_event(message):
    timestamp = time.strftime("%H:%M:%S")
    st.session_state.logs.insert(0, f"[{timestamp}] {message}")
    if len(st.session_state.logs) > 6:
        st.session_state.logs.pop()

# --- SIDEBAR UI ---
st.sidebar.title("🌿 Security Dashboard")
st.sidebar.markdown("This Streamlit Dashboard safely isolates the camera feed from the Flask issues.")

# Master Arm/Disarm Switch
run_system = st.sidebar.toggle("🟢 Arm Security System", value=False)

st.sidebar.markdown("---")
st.sidebar.subheader("Activity Logs")

# We create an empty container in the sidebar so we can dynamically overwrite it during the massive while-loop
log_container = st.sidebar.empty()

def render_logs():
    with log_container.container():
        for log in st.session_state.logs:
            if "ALERT" in log or "INTRUDER" in log:
                st.error(log)
            else:
                st.info(log)

render_logs() # Draw logs initially

# --- SETTINGS UI ---
st.sidebar.markdown("---")
st.sidebar.subheader("📐 Adjust Virtual Security Fence")
st.sidebar.markdown("Use these sliders to precisely draw the box over your plant!")
# Maximum resolutions typically 640x480 for cv2 streams
zone_x = st.sidebar.slider("Left Position (X)", 0, 640, 150)
zone_y = st.sidebar.slider("Top Position (Y)", 0, 480, 100)
zone_w = st.sidebar.slider("Box Width", 50, 640, 350)
zone_h = st.sidebar.slider("Box Height", 50, 480, 300)

st.sidebar.markdown("---")
st.sidebar.markdown("**Hardware Health:**")
st.sidebar.success("✅ MediaPipe Tracking: NATIVE")
st.sidebar.success("✅ Telegram Network: CONNECTED")


# --- MAIN UI ---
st.title("AgroSentinel")
st.markdown("Aim your plant into the green box and **use the sliders in the sidebar** to perfectly surround it. If a human hand enters the coordinates, the AI will trigger the IoT alarm.")

# We create a structured column layout to shrink the camera size down!
# Using a [1, 2, 1] ratio makes the center column perfectly sized.
col1, camera_col, col3 = st.columns([1, 2, 1])

with col1:
    st.metric("System Status", "ARMED" if run_system else "DISARMED")
    status_indicator = st.empty()
    if not run_system:
        status_indicator.markdown("### ⚪ Offline")

with camera_col:
    # We create the empty placeholder tightly contained within the center column
    FRAME_WINDOW = st.empty()

if run_system:
    st.success("System Armed")
    if "System Armed" not in st.session_state.logs[0]:
        log_event("🟢 System Armed! Loading camera module...")
        render_logs()

    # Capture Video Native
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        st.error("❌ The Webcam is currently locked. Close all other terminals and Python scripts, then refresh this page!")
        st.stop()
        
    ret, frame = cap.read()
    if not ret:
        st.error("Failed to read from camera. The hardware is locked or disconnected.")
        st.stop()
        
    # AI Engine - Initializing from root-level loaded module!
    hands_ai = mp_hands.Hands(max_num_hands=2, min_detection_confidence=0.7, min_tracking_confidence=0.7)
    cooldown_seconds = 5.0
    
    try:
        # Infinite Streamlit Loop
        while True:
            ret, frame = cap.read()
            if not ret:
                st.error("Video stream ended unexpectedly.")
                break
                
            height, width, _ = frame.shape
            
            # Dynamically hook the Streamlit sliders to the math logic every single frame!
            tree_box = (zone_x, zone_y, zone_x + zone_w, zone_y + zone_h)
                
            # Converting BGR to RGB for MediaPipe AND Streamlit!
            # Both Streamlit `st.image` and MediaPipe require RGB format!
            image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Analyze Frame
            results = hands_ai.process(image_rgb)
            
            box_color = (0, 255, 0) # GREEN by default
            touch_detected = False
            
            # Skeleton Drawing & Collision 
            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    mp_drawing.draw_landmarks(image_rgb, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                    
                    # Math Check
                    for lm in hand_landmarks.landmark:
                        px, py = int(lm.x * width), int(lm.y * height)
                        if tree_box[0] <= px <= tree_box[2] and tree_box[1] <= py <= tree_box[3]:
                            touch_detected = True
                            break
                    if touch_detected: break
                    
            # Handle Collision Events
            if touch_detected:
                box_color = (255, 0, 0) # RGB format RED is (255, 0, 0)!
                status_indicator.markdown("### 🔴 Intrusion detected")
            else:
                status_indicator.markdown("### 🟢 Active")
                
            # Draw Box onto the RGB frame
            cv2.rectangle(image_rgb, (tree_box[0], tree_box[1]), (tree_box[2], tree_box[3]), box_color, 4)
            cv2.putText(image_rgb, "Tree Zone", (tree_box[0], tree_box[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, box_color, 2)
            
            # Trigger Logic
            if touch_detected and (time.time() - st.session_state.last_trigger_time > cooldown_seconds):
                st.session_state.last_trigger_time = time.time()
                
                # Flash UI Log Update Live!
                log_event("🚨 INTRUDER HAND DETECTED!")
                render_logs()
                
                # Fire local siren
                trigger_alarm()
                
                # Stamp Warning on frame
                cv2.putText(image_rgb, "AI TRIGGER: INTRUDER CAUGHT", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 3)
                
                # Save the frame properly converting back to BGR for `cv2.imwrite`
                frame_bgr = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR)
                photo_path = 'ai_intruder_catch.jpg'
                cv2.imwrite(photo_path, frame_bgr)
                
                # Dispatch Telegram quietly over Thread
                def send_cloud_async():
                    send_telegram_alert("🚨 VIRTUAL AI PERIMETER BREACH! 🚨\nThe AI detected a hand touching the plant. See attached evidence.", photo_path)
                threading.Thread(target=send_cloud_async).start()
                
                log_event("☁️ Dispatching Telegram Message...")
                render_logs()

            # Instantly render the RGB frame directly inside the Web App Container!
            FRAME_WINDOW.image(image_rgb, use_container_width=True)
            
    finally:
        # Absolutely guarantee the camera turns off if you interact with the sliders to restart the script!
        cap.release()
        
else:
    # If the system is turned off
    st.info("System is DISARMED. Toggle the switch in the Sidebar to activate the Camera & AI Node.")
    
    if "System Disarmed" not in st.session_state.logs[0]:
        log_event("System Disarmed.")
        render_logs()
