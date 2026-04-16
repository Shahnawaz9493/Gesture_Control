class GestureRecognizer:
    GESTURE_NONE        = "NONE"
    GESTURE_MOVE        = "MOVE"
    GESTURE_DRAG        = "DRAG"
    GESTURE_CLICK       = "CLICK"
    GESTURE_VOLUME      = "VOLUME"
    GESTURE_PLAY_PAUSE  = "PLAY_PAUSE"

    def get_gesture(self, lm):
        """
        lm: list of (x, y) landmarks
        returns: (gesture, fingers_up_list)
        """

        fingers = []

        fingers.append(1 if lm[4][0] > lm[3][0] else 0)

        tips = [8, 12, 16, 20]
        for tip in tips:
            fingers.append(1 if lm[tip][1] < lm[tip - 2][1] else 0)


        if fingers == [0, 1, 0, 0, 0]:
            return self.GESTURE_MOVE, fingers

        if fingers == [1, 1, 0, 0, 0]:
            return self.GESTURE_DRAG, fingers

        if fingers == [0, 1, 1, 0, 0]:
            return self.GESTURE_CLICK, fingers

        if fingers == [0, 1, 1, 1, 0]:
            return self.GESTURE_VOLUME, fingers

        if fingers == [1, 0, 0, 0, 0]:
            return self.GESTURE_PLAY_PAUSE, fingers

        return self.GESTURE_NONE, fingers