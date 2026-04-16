import numpy as np
from ctypes import cast, POINTER

from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume


class VolumeController:
    def __init__(self):
        devices = AudioUtilities.GetSpeakers()

        try:
            interface = devices.Activate(
                IAudioEndpointVolume._iid_, 23, None
            )
        except:
            try:
                interface = devices._ctl.QueryInterface(IAudioEndpointVolume)
            except:
                raise Exception("Could not access system volume interface (pycaw issue)")

        self.volume = cast(interface, POINTER(IAudioEndpointVolume))
        self.min_vol, self.max_vol, _ = self.volume.GetVolumeRange()

    def get_percent(self):
        current_vol = self.volume.GetMasterVolumeLevel()
        return int(np.interp(current_vol,
                             [self.min_vol, self.max_vol],
                             [0, 100]))

    def set_percent(self, percent):
        percent = max(0, min(100, percent))
        vol = np.interp(percent,
                        [0, 100],
                        [self.min_vol, self.max_vol])
        self.volume.SetMasterVolumeLevel(vol, None)

    def update_from_distance(self, distance, min_dist=20, max_dist=200):
        distance = max(min_dist, min(max_dist, distance))

        percent = int(np.interp(distance,
                                [min_dist, max_dist],
                                [0, 100]))

        self.set_percent(percent)
        return percent