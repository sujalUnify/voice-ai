import pyautogui
import threading
import random
from datetime import datetime

# Configure PyAutoGUI fail-safe to be less sensitive
# The fail-safe triggers when mouse is moved to a corner
# You can disable it (False) or move the safety position
pyautogui.FAILSAFE = False  # Disable fail-safe (use with caution)
# Alternative: pyautogui.FAILSAFE_POINT = (1000, 1000)  # Set to bottom-right corner

# Random interval between 90-150 seconds (1:30 to 2:30 minutes)
MIN_INTERVAL = 60  # seconds
MAX_INTERVAL = 100  # seconds

# Various harmless keys to make activity look more natural
KEYS = ["shift", "ctrl", "shiftleft", "shiftright"]

stop_event = threading.Event()

def get_random_interval():
    """Get a random interval between MIN_INTERVAL and MAX_INTERVAL"""
    return random.uniform(MIN_INTERVAL, MAX_INTERVAL)

def get_random_key():
    """Get a random key from our list of harmless keys"""
    return random.choice(KEYS)
 
def show_time(): 
    time_now = datetime.now()
    hour = time_now.hour
    minute = time_now.minute 
    if hour == 1 or hour == 2: 
        if (hour == 1 and minute >= 30) or (hour == 2 and minute <= 30): 
            return True 
        else:
            return False
    return False


try:
    while not stop_event.is_set():
        # Press a random key for variety
        break_time = show_time() 
        if not break_time:
            key = get_random_key()
            pyautogui.press(key)

            # Wait for a random interval before next press
            interval = get_random_interval()
            minutes = int(interval // 60)
            seconds = int(interval % 60)

            # Use stop_event.wait with the random interval
            stop_event.wait(interval) 
        else:
            print("Break time until 2:30 AM...")
            # Wait 10 seconds before checking time again to avoid busy loop
            stop_event.wait(120)

except KeyboardInterrupt:
    stop_event.set()
    print("\nStopped.")