import numpy as np
import time
import cv2
import cv2.aruco as aruco

class _SimulatedFrameRead:

    """Frame with a centred ArUco marker (ID 13, DICT_4X4_50) for simulation."""

    # pixels per cm — governs how far the marker shifts as the drone translates
    PX_PER_CM = 3
    BASE_MARKER_SIZE = 120
    REF_HEIGHT_CM = 100
    MIN_MARKER_SIZE = 24
    MAX_MARKER_SIZE = 320

    def __init__(self, position, rotation, height):
        frame = np.full((480, 640, 3), 180, dtype=np.uint8)  # light-grey background
        aruco_dict = aruco.getPredefinedDictionary(aruco.DICT_4X4_50)

        # Higher altitude -> smaller symbol in the frame.
        h_safe = max(1, int(height))
        marker_size = int(
            np.clip(
                self.BASE_MARKER_SIZE * self.REF_HEIGHT_CM / h_safe,
                self.MIN_MARKER_SIZE,
                self.MAX_MARKER_SIZE,
            )
        )
        marker_img = np.zeros((marker_size, marker_size), dtype=np.uint8)
        aruco.generateImageMarker(aruco_dict, 13, marker_size, marker_img)

        # Rotate marker opposite to drone yaw so it appears fixed on the ground
        if rotation % 360 != 0:
            mh, mw = marker_img.shape
            M = cv2.getRotationMatrix2D((mw / 2.0, mh / 2.0), rotation, 1.0)
            marker_img = cv2.warpAffine(marker_img, M, (mw, mh))

        h, w = frame.shape[:2]
        cx, cy = w // 2, h // 2
        mh, mw = marker_img.shape

        # Drone offset from marker centre → marker shifts the opposite way in the image
        px = int(-position[0] * self.PX_PER_CM * height / 100)
        py = int(-position[1] * self.PX_PER_CM * height / 100)

        # Desired top-left corner of the marker in the frame
        x1 = cx - mw // 2 + px
        y1 = cy - mh // 2 + py
        x2, y2 = x1 + mw, y1 + mh

        # Clip to frame boundaries and copy only the visible portion
        fx1, fy1 = max(0, x1), max(0, y1)
        fx2, fy2 = min(w, x2), min(h, y2)
        if fx1 < fx2 and fy1 < fy2:
            mx1, my1 = fx1 - x1, fy1 - y1
            mx2, my2 = mx1 + (fx2 - fx1), my1 + (fy2 - fy1)
            frame[fy1:fy2, fx1:fx2] = cv2.cvtColor(
                marker_img[my1:my2, mx1:mx2], cv2.COLOR_GRAY2BGR
            )

        self.frame = frame


class SimulatorAdapter:
    """Wraps SimulatedDrone to expose a djitellopy-compatible interface."""

    def __init__(self, initial_position=(20, -14), initial_rotation=0):
        self.height = 0
        self.position = initial_position  # pixels from centre — PID must correct this
        self.rotation = initial_rotation

    # --- camera stubs (simulator has no camera) ---
    def streamon(self):
        pass

    def streamoff(self):
        pass

    def get_frame_read(self):
        time.sleep(0.5)
        try:
            return _SimulatedFrameRead(self.position, self.rotation, self.height)
        except Exception as e:
            print(f"failed to obtain frame {e}")
            return None

    def get_height(self):
        return self.height

    # --- flight commands (mapped to simulator equivalents) ---
    def takeoff(self):
        self.height = 100;

    def land(self):
        self.height = 0;

    def move_forward(self, cm):
        # change position by cm in the direction of current rotation
        self.position = (self.position[0] + cm * np.cos(np.radians(self.rotation)),
                         self.position[1] + cm * np.sin(np.radians(self.rotation)))

    def rotate_clockwise(self, degrees):
        self.rotation = (self.rotation + degrees) % 360

    def rotate_counter_clockwise(self, degrees):
        self.rotation = (self.rotation - degrees) % 360

    def send_rc_control(self, lr, fb, ud, yaw):
        """Map RC velocity commands to discrete simulator movements."""

        print(f"Control commands: vx={lr}, vy={fb}, vz={ud}, yaw={yaw}")
        deadband = 5

        def _step(v):
            return max(20, int(abs(v) * 0.2))

        if abs(lr) > deadband:
            if lr > 0:
                self.position = (self.position[0] + _step(lr) * np.sin(np.radians(self.rotation)),
                                 self.position[1] - _step(lr) * np.cos(np.radians(self.rotation)))
            else:
                self.position = (self.position[0] - _step(lr) * np.sin(np.radians(self.rotation)),
                                 self.position[1] + _step(lr) * np.cos(np.radians(self.rotation)))

        if abs(fb) > deadband:
            if fb > 0:
                self.position = (self.position[0] + _step(fb) * np.cos(np.radians(self.rotation)),
                                 self.position[1] + _step(fb) * np.sin(np.radians(self.rotation)))
            else:
                self.position = (self.position[0] - _step(fb) * np.cos(np.radians(self.rotation)),
                                 self.position[1] - _step(fb) * np.sin(np.radians(self.rotation)))

        if abs(ud) > deadband:
            dist = _step(ud)
            if ud > 0:
                self.height += dist
            else:
                self.height = max(0, self.height - dist)

        if abs(yaw) > deadband:
            if yaw > 0:
                self.rotation = (self.rotation + _step(yaw)) % 360
            else:
                self.rotation = (self.rotation - _step(yaw)) % 360