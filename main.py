from djitellopy import Tello
import cv2
import cv2.aruco as aruco
import numpy as np
import time

def is_safe_to_land(frame):
    """
    Landing is safe ONLY if ArUco ID 13 is detected.
    """

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # --- ArUco Detection ---
    aruco_dict = aruco.getPredefinedDictionary(aruco.DICT_4X4_50)
    parameters = aruco.DetectorParameters()
    detector = aruco.ArucoDetector(aruco_dict, parameters)

    corners, ids, rejected = detector.detectMarkers(gray)

    if ids is not None:
        ids = ids.flatten()
        if 13 in ids:
            return True

    return False

def tello_safe_landing(tello):
    frame_read = tello.get_frame_read()
    frame = frame_read.frame

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # --- ArUco Detection ---
    aruco_dict = aruco.getPredefinedDictionary(aruco.DICT_4X4_50)
    parameters = aruco.DetectorParameters()
    detector = aruco.ArucoDetector(aruco_dict, parameters)

    corners, ids, rejected = detector.detectMarkers(gray)

    if ids is not None:
        for i, marker_id in enumerate(ids.flatten()):
            if marker_id != 13:
                continue
            marker_corners = corners[i][0]

            # Optional: get center pixel
            center_x = int(marker_corners[:, 0].mean())
            center_y = int(marker_corners[:, 1].mean())
            print("Center:", (center_x, center_y))

    tello.land()


step_size = 20
max_size  = 100
move_size = step_size
has_move_size_changed = False

safe2land = False

tello = Tello()
tello.connect()

tello.streamon()
tello.set_video_direction(1)
frame_read = tello.get_frame_read()


tello.takeoff()

while not safe2land:
    frame_read = tello.get_frame_read()
    frame = frame_read.frame

    if frame is None:
        continue

    safe2land = is_safe_to_land(frame)


    if safe2land:
        print("Safe to land.")
        tello_safe_landing()

    tello.move_forward(move_size)

    tello.rotate_counter_clockwise(90)

    if has_move_size_changed:
        move_size += step_size
        print(f"new search size:{move_size}")

    has_move_size_changed = not has_move_size_changed

    if move_size > max_size:
        print("1 sq meter searched - emergency landing")
        tello.land()

tello.land() # redundant command
tello.streamoff()