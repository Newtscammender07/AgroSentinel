import streamlit as st
import cv2
import time
import threading
import mediapipe as mp
import av
from streamlit_webrtc import webrtc_streamer, VideoProcessorBase, WebRtcMode, RTCConfiguration
from streamlit_autorefresh import st_autorefresh

# Standard MediaPipe Initializations
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils

# WebRTC STUN servers to punch through local Wi-Fi firewalls
RTC_CONFIGURATION = RTCConfiguration(
    {"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}
)

# --- WEBRTC PROCESSOR CLASS ---
# Runs entirely on an isolated background thread to process frames from the browser!
class AIProcessor(VideoProcessorBase):
    def __init__(self):
        self.hands_ai = mp_hands.Hands(max_num_hands=2, min_detection_confidence=0.7, min_tracking_confidence=0.7)
        self.cooldown_seconds = 5.0
        self.last_trigger_time = 0.0
        # Default zone parameters (will be dynamically overwritten by Streamlit UI)
        self.zone_x = 150
        self.zone_y = 100
        self.zone_w = 350
        self.zone_h = 300
    
    def recv(self, frame: av.VideoFrame) -> av.VideoFrame:
        image_bgr = frame.to_ndarray(format="bgr24")
        height, width, _ = image_bgr.shape
        
        # Convert BGR to RGB for MediaPipe math
        image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        
        tree_box = (self.zone_x, self.zone_y, self.zone_x + self.zone_w, self.zone_y + self.zone_h)
        
        results = self.hands_ai.process(image_rgb)
        box_color = (0, 255, 0)
        touch_detected = False
        
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                mp_drawing.draw_landmarks(image_rgb, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                for lm in hand_landmarks.landmark:
                    px, py = int(lm.x * width), int(lm.y * height)
                    if tree_box[0] <= px <= tree_box[2] and tree_box[1] <= py <= tree_box[3]:
                        touch_detected = True
                        break
                if touch_detected: break
                
        if touch_detected:
            box_color = (255, 0, 0) # Red Intrusion Box
            
        cv2.rectangle(image_rgb, (tree_box[0], tree_box[1]), (tree_box[2], tree_box[3]), box_color, 4)
        cv2.putText(image_rgb, "Tree Zone", (tree_box[0], tree_box[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, box_color, 2)
        
        current_time = time.time()
        if touch_detected and (current_time - self.last_trigger_time > self.cooldown_seconds):
            self.last_trigger_time = current_time
            
            # Massive stamp on the physical video frame
            cv2.putText(image_rgb, "AI TRIGGER: INTRUDER CAUGHT", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 3)
            
            # Fire local siren
            try: trigger_alarm()
            except: pass
            
            # Save the frame properly converting back to BGR for `cv2.imwrite`
            frame_bgr = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR)
            photo_path = 'ai_intruder_catch.jpg'
            cv2.imwrite(photo_path, frame_bgr)
            
            # Dispatch Telegram quietly over Thread so video doesn't lag!
            def send_cloud_async():
                try: send_telegram_alert("🚨 VIRTUAL AI PERIMETER BREACH! 🚨\nThe AI detected a hand touching the plant. See attached evidence.", photo_path)
                except: pass
            threading.Thread(target=send_cloud_async).start()

        # Convert back to BGR for outputting to the web browser successfully
        final_bgr = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR)
        # Check if intrusion just happened to stamp it even when the bounding box isn't actively red
        if current_time - self.last_trigger_time < 2.0:
            cv2.putText(final_bgr, "🚨 INTRUDER CAUGHT!", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
            
        return av.VideoFrame.from_ndarray(final_bgr, format="bgr24")

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
    # 🔌 Trigger silent background polling every 1.5 seconds!
    # This loop allows the main Streamlit UI to routinely check on the WebRTC AI thread.
    st_autorefresh(interval=1500, limit=None, key="alarm_poller")
    
    st.success("System Armed! Stream initialized.")
    if "System Armed" not in st.session_state.logs[0]:
        log_event("🟢 System Armed! Requesting webcam access...")
        render_logs()
        
    with camera_col:
        # Launch the fully managed Streamlit WebRTC Pipeline
        ctx = webrtc_streamer(
            key="agro-sentinel",
            mode=WebRtcMode.SENDRECV,
            rtc_configuration=RTC_CONFIGURATION,
            video_processor_factory=AIProcessor,
            media_stream_constraints={"video": True, "audio": False},
            async_processing=True # Improves framerate massively!
        )
        
        # Cross-Thread Tunneling: 
        # Pass the Streamlit Slider Math into the isolated C++ Video thread instantly!
        if ctx.video_processor:
            ctx.video_processor.zone_x = zone_x
            ctx.video_processor.zone_y = zone_y
            ctx.video_processor.zone_w = zone_w
            ctx.video_processor.zone_h = zone_h
            
            # Since autorefresh checks this script every 1.5 seconds, we can check for recent triggers!
            time_since_intrusion = time.time() - ctx.video_processor.last_trigger_time
            if time_since_intrusion < 4.0:
                status_indicator.markdown("### 🔴 Intrusion detected")
                st.error("🔊 ALARM TRIGGERED: Please check video stream!")
                
                # Use Streamlit 1.55 Native AutoPlay Audio with a reliable Google Cloud sound file
                alarm_url = "https://actions.google.com/sounds/v1/alarms/digital_watch_alarm_long.ogg"
                st.audio(alarm_url, format="audio/ogg", autoplay=True)
            else:
                status_indicator.markdown("### 🟢 Active")

        
else:
    # If the system is turned off
    st.info("System is DISARMED. Toggle the switch in the Sidebar to activate the Camera & AI Node.")
    
    if "System Disarmed" not in st.session_state.logs[0]:
        log_event("System Disarmed.")
        render_logs()
