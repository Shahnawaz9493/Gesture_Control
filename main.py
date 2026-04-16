"""
Gesture-controlled desktop interface using MediaPipe + OpenCV.

Gestures (right hand, mirrored camera):
  ☝  Index only + open pinch  → MOVE mouse
  ☝  Index only + close pinch → DRAG (mouseDown while held)
  ✌  Index + middle, tips close → CLICK
  🤟 Index + middle + ring (3 up) → VOLUME  (thumb–index span = level)
  👍 Thumb only               → PLAY / PAUSE
  ✊ Fist                     → (neutral / drag release)

Press ESC to quit.
"""

import math
import time

import cv2
import numpy as np
import pyautogui

from hand_tracking  import HandTracker
from gesture_logic  import GestureRecognizer
from volume_control import VolumeController

pyautogui.FAILSAFE = False
pyautogui.PAUSE    = 0          # remove built-in 0.1 s delay for smoothness

cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH,  1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
cap.set(cv2.CAP_PROP_FPS,          60)

tracker    = HandTracker(max_hands=1, detection_conf=0.85, tracking_conf=0.85)
recognizer = GestureRecognizer()
vol_ctrl   = VolumeController()

SCREEN_W, SCREEN_H = pyautogui.size()

SMOOTHENING       = 7      
MARGIN            = 60    
CLICK_DELAY       = 0.35   
PLAY_PAUSE_DELAY  = 1.0    

prev_x, prev_y       = 0.0, 0.0
last_click_time      = 0.0
last_play_pause_time = 0.0
is_dragging          = False
vol_pct              = vol_ctrl.get_percent()
fps_timer            = time.time()
fps                  = 0.0


COL = {
    "MOVE":       (80,  255, 100),
    "DRAG":       (60,  130, 255),
    "CLICK":      (0,   210, 255),
    "VOLUME":     (200,  40, 255),
    "PLAY_PAUSE": (0,   255, 255),
    "FIST":       (60,   60, 255),
    "NONE":       (160, 160, 160),
}


def draw_rounded_rect(img, x1, y1, x2, y2, r, color, alpha=0.55):
    """Semi-transparent filled rounded rectangle."""
    overlay = img.copy()
    cv2.rectangle(overlay, (x1 + r, y1), (x2 - r, y2), color, -1)
    cv2.rectangle(overlay, (x1, y1 + r), (x2, y2 - r), color, -1)
    for cx, cy in [(x1+r, y1+r), (x2-r, y1+r), (x1+r, y2-r), (x2-r, y2-r)]:
        cv2.circle(overlay, (cx, cy), r, color, -1)
    cv2.addWeighted(overlay, alpha, img, 1 - alpha, 0, img)


def draw_hud(frame, gesture: str, vol_percent: int, current_fps: float):
    h, w = frame.shape[:2]
    color = COL.get(gesture, COL["NONE"])

    draw_rounded_rect(frame, 10, 10, 260, 58, 8, (20, 20, 20))
    cv2.putText(frame, f"  {gesture}", (14, 44),
                cv2.FONT_HERSHEY_SIMPLEX, 0.95, color, 2, cv2.LINE_AA)

    draw_rounded_rect(frame, w - 120, 10, w - 10, 50, 8, (20, 20, 20))
    cv2.putText(frame, f"FPS {current_fps:4.0f}", (w - 115, 38),
                cv2.FONT_HERSHEY_SIMPLEX, 0.75, (200, 200, 200), 2, cv2.LINE_AA)

    bx, by, bw, bh = w - 55, 70, 28, 200
    draw_rounded_rect(frame, bx - 4, by - 20, bx + bw + 4, by + bh + 30, 6, (20, 20, 20))
    # Track
    cv2.rectangle(frame, (bx, by), (bx + bw, by + bh), (60, 60, 60), -1)
    # Fill
    fill_h = int(bh * vol_percent / 100)
    if fill_h > 0:
        fill_color = (80, 220, 80) if vol_percent < 80 else (60, 130, 255)
        cv2.rectangle(frame, (bx, by + bh - fill_h), (bx + bw, by + bh), fill_color, -1)
    cv2.putText(frame, "VOL", (bx - 2, by - 4),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1, cv2.LINE_AA)
    cv2.putText(frame, f"{vol_percent}%", (bx - 4, by + bh + 22),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (220, 220, 220), 1, cv2.LINE_AA)

    hints = [
        ("☝ move",    COL["MOVE"]),
        ("✌ click",   COL["CLICK"]),
        ("🤏 drag",   COL["DRAG"]),
        ("🤟 vol",    COL["VOLUME"]),
        ("👍 ⏯",     COL["PLAY_PAUSE"]),
    ]
    draw_rounded_rect(frame, 0, h - 36, w, h, 0, (15, 15, 15), alpha=0.7)
    step = w // len(hints)
    for i, (label, hcol) in enumerate(hints):
        cv2.putText(frame, label, (i * step + 10, h - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, hcol, 1, cv2.LINE_AA)



print("Gesture Control running — press ESC in the OpenCV window to quit.")

while True:
    ok, frame = cap.read()
    if not ok:
        continue

    frame = cv2.flip(frame, 1)
    h, w  = frame.shape[:2]

    now  = time.time()
    fps  = 1.0 / max(now - fps_timer, 1e-6)
    fps_timer = now

    frame  = tracker.find_hands(frame, draw=True)
    lm     = tracker.get_landmarks(frame)

    gesture = GestureRecognizer.GESTURE_NONE

    if lm:
        gesture, fingers = recognizer.get_gesture(lm)

        # Landmark shortcuts
        ix, iy  = lm[8]    # index tip
        mx, my  = lm[12]   # middle tip
        tx, ty  = lm[4]    # thumb tip

        pinch_dist = math.hypot(tx - ix, ty - iy)

        if gesture == GestureRecognizer.GESTURE_MOVE:
            if is_dragging:
                pyautogui.mouseUp()
                is_dragging = False

            sx = float(np.interp(ix, [MARGIN, w - MARGIN], [0, SCREEN_W]))
            sy = float(np.interp(iy, [MARGIN, h - MARGIN], [0, SCREEN_H]))

            
            cx = prev_x + (sx - prev_x) / SMOOTHENING
            cy = prev_y + (sy - prev_y) / SMOOTHENING
            pyautogui.moveTo(cx, cy)
            prev_x, prev_y = cx, cy

            cv2.circle(frame, (ix, iy), 12, COL["MOVE"], cv2.FILLED)

        elif gesture == GestureRecognizer.GESTURE_DRAG:
            if not is_dragging:
                pyautogui.mouseDown()
                is_dragging = True

            sx = float(np.interp(ix, [MARGIN, w - MARGIN], [0, SCREEN_W]))
            sy = float(np.interp(iy, [MARGIN, h - MARGIN], [0, SCREEN_H]))
            cx = prev_x + (sx - prev_x) / SMOOTHENING
            cy = prev_y + (sy - prev_y) / SMOOTHENING
            pyautogui.moveTo(cx, cy)
            prev_x, prev_y = cx, cy

            mid = ((ix + tx) // 2, (iy + ty) // 2)
            cv2.line(frame, (ix, iy), (tx, ty), COL["DRAG"], 2)
            cv2.circle(frame, mid, 10, COL["DRAG"], cv2.FILLED)

        elif gesture == GestureRecognizer.GESTURE_CLICK:
            if is_dragging:
                pyautogui.mouseUp()
                is_dragging = False

            if now - last_click_time > CLICK_DELAY:
                pyautogui.click()
                last_click_time = now

            mid = ((ix + mx) // 2, (iy + my) // 2)
            cv2.circle(frame, mid, 14, COL["CLICK"], cv2.FILLED)

        elif gesture == GestureRecognizer.GESTURE_VOLUME:
            if is_dragging:
                pyautogui.mouseUp()
                is_dragging = False

            vol_pct = vol_ctrl.update_from_distance(pinch_dist)

            cv2.line(frame, (ix, iy), (tx, ty), COL["VOLUME"], 3)
            mid = ((ix + tx) // 2, (iy + ty) // 2)
            cv2.circle(frame, mid, 10, COL["VOLUME"], cv2.FILLED)
            cv2.putText(frame, f"Vol {vol_pct}%", (mid[0] + 14, mid[1]),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, COL["VOLUME"], 2, cv2.LINE_AA)

        elif gesture == GestureRecognizer.GESTURE_PLAY_PAUSE:
            if is_dragging:
                pyautogui.mouseUp()
                is_dragging = False

            if now - last_play_pause_time > PLAY_PAUSE_DELAY:
                pyautogui.press("playpause")
                last_play_pause_time = now

            # Flash label
            cv2.putText(frame, "PLAY / PAUSE", (w // 2 - 110, h // 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.2, COL["PLAY_PAUSE"], 3, cv2.LINE_AA)

        else:
            if is_dragging:
                pyautogui.mouseUp()
                is_dragging = False

    else:
        # Hand lost — always release drag
        if is_dragging:
            pyautogui.mouseUp()
            is_dragging = False

    draw_hud(frame, gesture, vol_pct, fps)

    cv2.imshow("Gesture Control", frame)

    if cv2.waitKey(1) & 0xFF == 27:   # ESC
        break

if is_dragging:
    pyautogui.mouseUp()
cap.release()
cv2.destroyAllWindows()
print("Gesture Control stopped.")