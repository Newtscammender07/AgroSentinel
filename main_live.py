import cv2
import time
from alarm import trigger_alarm
from cloud_alert import send_telegram_alert

def live_camera_security():
    # Initialize the camera
    print("🎥 Initializing Live Camera monitoring...")
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("❌ Error: Could not open the webcam.")
        return

    print("=" * 50)
    print("🌿 REAL-TIME CAMERA SECURITY ACTIVE 🌿")
    print("=" * 50)
    print("A live video window should now open on your screen.")
    print("Press 'SPACEBAR' key while focused on the video window to simulate a TOUCH trigger.")
    print("Press 'q' or 'ESC' on the video window to EXIT the system.")
    print("=" * 50)

    try:
        while True:
            # Read real-time frame
            ret, frame = cap.read()
            if not ret:
                print("❌ Error: Failed to grab frame.")
                break

            # Show the live feed window
            cv2.imshow("AgroSentinel Live Feed (Press SPACE to touch)", frame)

            # Check for key presses from the OpenCV window
            # waitKey(1) means wait 1 millisecond for a key
            key = cv2.waitKey(1) & 0xFF

            if key == 32:  # ASCII for Spacebar
                print("\n⚠️ PLANT TOUCH DETECTED from Live Feed! ⚠️")
                
                # 1. Trigger Alarm Sound
                trigger_alarm()
                
                # 2. Extract current Live Frame and save it
                photo_path = 'live_intruder.jpg'
                cv2.imwrite(photo_path, frame)
                print(f"📸 Captured live frame as {photo_path}")
                
                # 3. Send to Telegram
                alert_message = "🚨 LIVE INTRUDER ALERT! 🚨\nSomeone touched your plant! Here is the actual real-time frame!"
                send_telegram_alert(alert_message, photo_path)
                
                print("✅ Live Security Response Complete.")
                print("Resuming continuous video monitoring...")

            elif key == ord('q') or key == 27:  # 'q' or ESC
                print("\nDeactivating Live Security System. Goodbye!")
                break
                
    except Exception as e:
        print(f"An error occurred: {e}")
        
    finally:
        # Clean up camera and windows
        cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    live_camera_security()
