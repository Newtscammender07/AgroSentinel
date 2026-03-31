import cv2
import time
import os

def capture_intruder_photo(filename="intruder.jpg"):
    """
    Captures a frame from the default webcam and saves it as an image file.
    """
    print("📸 Attempting to capture intruder photo...")
    
    # Initialize the camera (0 is usually the built-in webcam)
    cap = cv2.VideoCapture(0)
    
    # Check if the webcam is opened correctly
    if not cap.isOpened():
        print("❌ Error: Could not open webcam.")
        return None
        
    # Allow the camera sensor to warm up and adjust to light
    time.sleep(1)
    
    # Read a frame
    ret, frame = cap.read()
    
    # Release the camera immediately after capture
    cap.release()
    
    if ret:
        # Save the captured frame to disk
        cv2.imwrite(filename, frame)
        print(f"✅ Photo captured successfully: {os.path.abspath(filename)}")
        return os.path.abspath(filename)
    else:
        print("❌ Error: Could not read frame from webcam.")
        return None

if __name__ == "__main__":
    # Test capture when run independently
    capture_intruder_photo()
