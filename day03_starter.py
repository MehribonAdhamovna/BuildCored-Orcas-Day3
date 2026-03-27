
import cv2 #type:ignore 
import mediapipe as mp #type:ignore 
import numpy as np #type:ignore 
import platform
import subprocess
import sys
import pygame #type:ignore

# Initialize the music mixer
pygame.mixer.init()
pygame.mixer.music.load("arthur-vyncke-cherry-metal(chosic.com).mp3") 
pygame.mixer.music.play(-1)

# ============================================================
# CROSS-PLATFORM VOLUME CONTROL
# You don't need to change this section.
# It auto-detects your OS and uses the right method.
# ============================================================

OS = platform.system()


def set_system_volume(percent):
    """Set system volume to a percentage (0-100). Works on Mac, Windows, Linux."""
    percent = max(0, min(100, int(percent)))

    try:
        if OS == "Darwin":  # macOS
            subprocess.run(
                ["osascript", "-e", f"set volume output volume {percent}"],
                capture_output=True, timeout=2
            )
        elif OS == "Windows":
            try:
                from ctypes import cast, POINTER
                from comtypes import CLSCTX_ALL
                from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
                devices = AudioUtilities.GetSpeakers()
                interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                volume = cast(interface, POINTER(IAudioEndpointVolume))
                volume.SetMasterVolumeLevelScalar(percent / 100.0, None)
            except ImportError:
                pass  # Display-only mode if pycaw not installed
        else:  # Linux
            result = subprocess.run(
                ["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{percent}%"],
                capture_output=True, timeout=2
            )
            if result.returncode != 0:
                subprocess.run(
                    ["amixer", "set", "Master", f"{percent}%"],
                    capture_output=True, timeout=2
                )
    except Exception:
        pass


cap = cv2.VideoCapture(0)
if not cap.isOpened():
    cap = cv2.VideoCapture(1)
if not cap.isOpened():
    print("ERROR: No webcam found.")
    sys.exit(1)

ret, test_frame = cap.read()
FRAME_H, FRAME_W = test_frame.shape[:2]

mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    max_num_hands=1,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.6
)
mp_draw = mp.solutions.drawing_utils

WRIST = 0
current_volume = 50
smoothed_volume = 50.0
SMOOTHING = 0.3


# ============================================================
# TODO #1: Set your dead zones
# ============================================================

DEAD_ZONE_TOP = 0.10      # Top 10% = max volume
DEAD_ZONE_BOTTOM = 0.90   # Bottom 10% = min volume


# ============================================================
# TODO #2: Mapping function — the ADC concept
# ============================================================

def fist_to_volume(y_normalized):
    """Convert fist y-position (0=top, 1=bottom) to volume (0-100)."""

    # Apply dead zones first
    if y_normalized < DEAD_ZONE_TOP:
        return 100.0
    elif y_normalized > DEAD_ZONE_BOTTOM:
        return 0.0

   
    volume = np.interp(
        y_normalized,
        [DEAD_ZONE_TOP, DEAD_ZONE_BOTTOM],
        [100, 0]
    )
    return volume


# ============================================================
# MAIN LOOP — Sensor → Process → Output
# ============================================================
print("\nVolumeKnuckle is running!")
print(f"OS: {OS}")
print(f"Dead zones: top {DEAD_ZONE_TOP*100:.0f}%, bottom {(1-DEAD_ZONE_BOTTOM)*100:.0f}%")
print("Fist UP = louder. Fist DOWN = quieter.")
print("Show open hand first so MediaPipe can detect, then close fist.")
print("Press 'q' to quit.\n")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.flip(frame, 1)
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(rgb_frame)

    if results.multi_hand_landmarks:
        hand_landmarks = results.multi_hand_landmarks[0]
        mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

        # 1. FIST CHECK LOGIC
        middle_tip = hand_landmarks.landmark[12].y
        middle_base = hand_landmarks.landmark[9].y
        is_fist = middle_tip > middle_base 

        # 2. GET WRIST POSITION
        fist_y = hand_landmarks.landmark[WRIST].y

        if is_fist:
            # 1. VOLUME CONTROL
            raw_volume = fist_to_volume(fist_y)
            smoothed_volume = smoothed_volume + SMOOTHING * (raw_volume - smoothed_volume)
            
            # Update Pygame and System Volume
            pygame.mixer.music.set_volume(smoothed_volume / 100)
            
            set_system_volume(int(smoothed_volume))
            current_volume = int(smoothed_volume)

            # 2. PLAY LOGIC
            if not pygame.mixer.music.get_busy(): # Check if music is NOT playing
                pygame.mixer.music.unpause()
            
            status_msg = f"PLAYING - Vol: {int(smoothed_volume)}%"
            color = (0, 255, 0) # Green
        else:
            # 1. PAUSE LOGIC: Stop the music when the hand is open
            if pygame.mixer.music.get_busy(): # Check if music IS playing
                pygame.mixer.music.pause()
            
            # 2. VISUAL FEEDBACK: Change color and message
            status_msg = "PAUSED - Hand Open"
            color = (0, 0, 255) # Red indicates the controls are locked

        # 3. DRAW VISUALS
        cv2.putText(frame, status_msg, (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, color, 3)
        
        # Draw the volume bar (Same code from your template)
        bar_height = FRAME_H - 100
        fill_height = int(bar_height * current_volume / 100)
        cv2.rectangle(frame, (FRAME_W-60, 50), (FRAME_W-30, FRAME_H-50), (50, 50, 50), -1)
        cv2.rectangle(frame, (FRAME_W-60, FRAME_H-50-fill_height), (FRAME_W-30, FRAME_H-50), color, -1)

    else:
        cv2.putText(frame, "No hand detected", (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    cv2.imshow("VolumeKnuckle - Day 03", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

    cv2.imshow("VolumeKnuckle - Day 03", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
print(f"\nVolumeKnuckle ended. Final volume: {current_volume}%")
print("See you tomorrow for Day 04!")