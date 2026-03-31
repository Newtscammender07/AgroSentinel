import time
import platform
import threading

def play_siren_win():
    import winsound
    # Play a siren-like sequence of beeps
    for _ in range(5):
        winsound.Beep(1000, 300) # Frequency 1000Hz, 300ms
        winsound.Beep(1500, 300) # Frequency 1500Hz, 300ms
        winsound.Beep(2000, 300) # Frequency 2000Hz, 300ms
        
def play_siren_unix():
    # Simple terminal bell for Unix/Mac fallback
    for _ in range(10):
        print('\a', end='', flush=True)
        time.sleep(0.5)

def trigger_alarm():
    """
    Plays a loud alarm sound to scare the intruder.
    Runs in a separate thread so it doesn't block other operations (like sending photo).
    """
    print("🔊 ALARM TRIGGERED! WEE-WOO-WEE-WOO!")
    
    if platform.system() == "Windows":
        # Run sound in a background thread to allow the camera to capture normally
        alarm_thread = threading.Thread(target=play_siren_win)
        alarm_thread.start()
    else:
        alarm_thread = threading.Thread(target=play_siren_unix)
        alarm_thread.start()

if __name__ == "__main__":
    # Test the alarm independently
    trigger_alarm()
