import cv2
import mediapipe as mp


class HandTracker:
    def __init__(self, max_hands=1, detection_conf=0.5, tracking_conf=0.5):
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            max_num_hands=max_hands,
            min_detection_confidence=detection_conf,
            min_tracking_confidence=tracking_conf
        )
        self.mp_draw = mp.solutions.drawing_utils
        self.results = None

    def find_hands(self, frame, draw=True):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        self.results = self.hands.process(rgb)

        if self.results.multi_hand_landmarks:
            for handLms in self.results.multi_hand_landmarks:
                if draw:
                    self.mp_draw.draw_landmarks(
                        frame,
                        handLms,
                        self.mp_hands.HAND_CONNECTIONS
                    )
        return frame

    def get_landmarks(self, frame):
        if self.results and self.results.multi_hand_landmarks:
            h, w, _ = frame.shape
            lm_list = []

            for id, lm in enumerate(self.results.multi_hand_landmarks[0].landmark):
                cx, cy = int(lm.x * w), int(lm.y * h)
                lm_list.append((cx, cy))

            return lm_list

        return None