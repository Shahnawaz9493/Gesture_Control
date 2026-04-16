<div align="center">

```
██████╗ ███████╗███████╗████████╗██╗   ██╗██████╗ ███████╗
██╔════╝ ██╔════╝██╔════╝╚══██╔══╝██║   ██║██╔══██╗██╔════╝
██║  ███╗█████╗  ███████╗   ██║   ██║   ██║██████╔╝█████╗  
██║   ██║██╔══╝  ╚════██║   ██║   ██║   ██║██╔══██╗██╔══╝  
╚██████╔╝███████╗███████║   ██║   ╚██████╔╝██║  ██║███████╗
 ╚═════╝ ╚══════╝╚══════╝   ╚═╝    ╚═════╝ ╚═╝  ╚═╝╚══════╝
```

# 🖐️ GestureOS — Control Your PC With Your Bare Hands

**Real-time hand gesture recognition for full desktop control.**  
Move your mouse, click, drag, adjust volume and media — all without touching your keyboard or mouse.

<br>

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![OpenCV](https://img.shields.io/badge/OpenCV-4.x-5C3EE8?style=for-the-badge&logo=opencv&logoColor=white)](https://opencv.org)
[![MediaPipe](https://img.shields.io/badge/MediaPipe-Hands-FF6F00?style=for-the-badge&logo=google&logoColor=white)](https://mediapipe.dev)
[![Platform](https://img.shields.io/badge/Platform-Windows-0078D4?style=for-the-badge&logo=windows&logoColor=white)](https://microsoft.com/windows)
[![License](https://img.shields.io/badge/License-MIT-22C55E?style=for-the-badge)](LICENSE)

<br>

> *No wearables. No special hardware. Just your webcam and your hand.*

</div>

---

## ✨ What It Does

GestureOS turns your webcam into a touchless input device using Google's **MediaPipe Hands** for 21-point landmark detection. A smart state machine maps hand poses to desktop actions — no gesture ever conflicts with another.

<br>

<div align="center">

| Gesture | Action | How to do it |
|:-------:|--------|:------------:|
| ☝️ | **Move Mouse** | Index finger up, thumb open |
| 🤏 | **Drag** | Index finger up, pinch thumb to index |
| ✌️ | **Click** | Index + middle up, bring tips together |
| 🤟 | **Volume Control** | Index + middle + ring up — spread for loud, pinch for quiet |
| 👍 | **Play / Pause** | Thumb only raised |
| ✊ | **Neutral / Release** | Fist — safely releases any drag |

</div>

<br>

---

## 🏗️ Architecture

```
GestureOS/
│
├── main.py              ← Entry point. Webcam loop, state machine, HUD rendering
├── hand_tracking.py     ← MediaPipe wrapper. Detects & draws 21-point hand landmarks
├── gesture_logic.py     ← Priority-ordered gesture recognizer (no conflicts possible)
└── volume_control.py    ← Smooth native volume via pycaw (no key-press spam)
```

### How the modules connect

```
Webcam Frame
     │
     ▼
┌─────────────────┐
│  hand_tracking  │  — Runs MediaPipe, returns 21 (x,y) landmarks
└────────┬────────┘
         │ lm[]
         ▼
┌─────────────────┐
│ gesture_logic   │  — Maps landmarks → gesture enum (priority-ordered)
└────────┬────────┘
         │ gesture
         ▼
┌─────────────────────────────────────────┐
│               main.py                   │
│  MOVE → pyautogui.moveTo()              │
│  DRAG → pyautogui.mouseDown/moveTo()    │
│  CLICK → pyautogui.click()              │
│  VOLUME → volume_control.update()       │
│  PLAY_PAUSE → pyautogui.press()         │
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────┐
│ volume_control  │  — pycaw SetMasterVolumeLevelScalar (smooth, native)
└─────────────────┘
```

---

## ⚡ Quick Start

### 1 — Clone the repository

```bash
git clone https://github.com/yourusername/GestureOS.git
cd GestureOS
```

### 2 — Create a virtual environment (recommended)

```bash
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS / Linux
```

### 3 — Install dependencies

```bash
pip install -r requirements.txt
```

### 4 — Run

```bash
python main.py
```

> Press **ESC** in the OpenCV window to quit cleanly.

---

## 📦 Requirements

```
opencv-python>=4.8
mediapipe>=0.10
pyautogui>=0.9
numpy>=1.24
pycaw>=20230407
comtypes>=1.2
```

Save as `requirements.txt` and install with `pip install -r requirements.txt`.

> **Note:** `pycaw` is Windows-only. On Linux/macOS the app runs with volume control disabled gracefully — all other gestures still work.

---

## 🔬 Technical Deep-Dive

### Gesture Recognition — Priority State Machine

The recogniser checks gestures in a strict priority order so two gestures can **never fire at the same time**:

```python
# gesture_logic.py — simplified
def get_gesture(self, lm):
    fingers = self.fingers_up(lm)          # [thumb, index, middle, ring, pinky]
    pinch   = self.distance(lm, 4, 8)     # thumb tip ↔ index tip

    if not any(fingers):      return FIST        # priority 1
    if fingers == [1,0,0,0,0]: return PLAY_PAUSE # priority 2
    if index and middle and ring: return VOLUME  # priority 3
    if index and middle and pinch < 40: return CLICK  # priority 4
    if index only and pinch < 45: return DRAG    # priority 5
    if index only: return MOVE                   # priority 6
    return NONE
```

### Mouse Smoothing — Exponential Filter

Raw landmark coordinates jitter at ≈ 1–3 px per frame. Exponential smoothing removes jitter while preserving intent:

```python
# Each frame
curr_x = prev_x + (target_x - prev_x) / SMOOTHENING   # SMOOTHENING = 7
curr_y = prev_y + (target_y - prev_y) / SMOOTHENING
pyautogui.moveTo(curr_x, curr_y)
prev_x, prev_y = curr_x, curr_y
```

Higher `SMOOTHENING` values = silkier movement, slightly more lag.

### Volume — Continuous Scalar, Not Key Presses

The original approach (`pyautogui.press("volumeup")`) fires 60 key presses per second. GestureOS uses pycaw to write the volume level directly:

```python
# volume_control.py
self._smoothed_scalar = (
    ALPHA * raw_scalar + (1 - ALPHA) * self._smoothed_scalar
)
self._volume_iface.SetMasterVolumeLevelScalar(self._smoothed_scalar, None)
```

This gives completely smooth, analog-feeling volume control.

### Safe Drag Release

A `is_dragging` flag is checked on **every** branch, including when no hand is detected. `mouseUp()` is guaranteed to fire when the gesture ends:

```python
# Hand disappears mid-drag? We still release cleanly.
else:
    if is_dragging:
        pyautogui.mouseUp()
        is_dragging = False
```

---

## 🎛️ Configuration

All tuning parameters are at the top of `main.py`:

| Parameter | Default | Effect |
|-----------|---------|--------|
| `SMOOTHENING` | `7` | Mouse smoothness. Higher = smoother but slower |
| `MARGIN` | `60 px` | Dead zone at webcam edges (reduces edge jitter) |
| `CLICK_DELAY` | `0.35 s` | Minimum time between clicks |
| `PLAY_PAUSE_DELAY` | `1.0 s` | Minimum time between play/pause triggers |

Volume range and smoothing are in `volume_control.py`:

| Parameter | Default | Effect |
|-----------|---------|--------|
| `DIST_MIN` | `30 px` | Pinch distance = 0% volume |
| `DIST_MAX` | `220 px` | Max spread distance = 100% volume |
| `SMOOTH_ALPHA` | `0.18` | Volume smoothing (lower = slower, smoother) |

---

## 🖥️ HUD — On-Screen Display

The overlay shows real-time feedback without cluttering the view:

```
┌─────────────────────────────────────────────────┐
│  [ MOVE ]                          [ FPS  58 ]  │
│                                                  │  ▕ VOL
│         (landmark skeleton overlay)              │  ▕ ████
│                                                  │  ▕ 72%
│  ☝ move   ✌ click   🤏 drag   🤟 vol   👍 ⏯   │
└─────────────────────────────────────────────────┘
```

- **Top-left** — Active gesture name (colour-coded per gesture)
- **Top-right** — Live FPS counter
- **Right edge** — Volume bar with percentage
- **Bottom strip** — Gesture reference cheat-sheet

---

## 🛠️ Troubleshooting

**Camera not opening**
```bash
# Try a different camera index
cap = cv2.VideoCapture(1)   # change 0 → 1 or 2
```

**Volume control not working**
- pycaw is Windows-only. On other platforms, volume gestures are silently ignored.
- Run as administrator if pycaw still fails to access the audio endpoint.

**Gestures feel too sensitive / not triggering**
- Ensure good, even lighting — mediapipe struggles in low light.
- Adjust `detection_conf` and `tracking_conf` in `HandTracker(...)` (default `0.85`).
- Widen `MARGIN` if the mouse is erratic at screen edges.

**High CPU usage**
```python
# In main.py, reduce resolution
cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
```

---

## 🗺️ Roadmap

- [ ] Left-hand support & handedness detection
- [ ] Two-hand gestures (e.g. pinch-zoom)
- [ ] Scroll gesture (two-finger swipe)
- [ ] Configurable gesture→action mapping via `config.yaml`
- [ ] System tray icon & background mode
- [ ] Linux volume support (PulseAudio / PipeWire)
- [ ] macOS support (CoreAudio)

---

## 🤝 Contributing

Pull requests are welcome! For major changes please open an issue first.

```bash
# Fork → clone → branch
git checkout -b feature/your-feature-name

# Make changes, then
git commit -m "feat: describe your change"
git push origin feature/your-feature-name
# Open a Pull Request on GitHub
```

Please keep the four-module structure intact — `hand_tracking`, `gesture_logic`, `volume_control`, `main` have clearly separated responsibilities.

---

## 📄 License

Distributed under the **MIT License**. See [`LICENSE`](LICENSE) for full text.

---

<div align="center">

Built with ❤️ using [MediaPipe](https://mediapipe.dev) · [OpenCV](https://opencv.org) · [pycaw](https://github.com/AndreMiras/pycaw)

*Star ⭐ the repo if this saved you a mouse click — ironically.*

</div>
