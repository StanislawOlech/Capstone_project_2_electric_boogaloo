import cv2
import cv2.aruco as aruco
import time
from pid import PID
import time


class Landing_Search_Params:
    def __init__(self,
                 max_search_size,
                 step_size,
                 clockwise=False):
        self.max_search_size = max_search_size
        self.step_size = step_size
        self.clockwise = clockwise


def find_aruco(tello, aruco_num=13):
    try:
        frame_read = tello.get_frame_read()
        frame = frame_read.frame
    except Exception as e:
        print("failed to obtain frame")
        return(None)

    h, w, _ = frame.shape
    frame_center = (w // 2, h // 2)


    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # --- ArUco Detection ---
    aruco_dict = aruco.getPredefinedDictionary(aruco.DICT_4X4_50)
    parameters = aruco.DetectorParameters()
    detector = aruco.ArucoDetector(aruco_dict, parameters)

    corners, ids, _ = detector.detectMarkers(gray)

    if ids is None:
        return None

    for i, marker_id in enumerate(ids.flatten()):
        if marker_id != aruco_num:
            continue
        marker_corners = corners[i][0]

        center_x = int(marker_corners[:, 0].mean())
        center_y = int(marker_corners[:, 1].mean())

        return (center_x - frame_center[0], center_y - frame_center[1]) # TODO make sure the coordinates are not mismatched

    return None


def pid_landing(tello,
                aruco_id=13,
                k_p=0.25,
                k_i=0.0,
                k_d=0.0): # TODO adjust params

    pid_x = PID(k_p, k_i, k_d, limit=20)
    pid_y = PID(k_p, k_i, k_d, limit=20)


    # TODO adjust params
    descent_speed = 20
    landing_threshold = 20  # in pixels

    prev_time = time.time()

    while True:

        aruco_pos_error = find_aruco(tello, aruco_id)

        if aruco_pos_error is None:
            print("Aruco symbol lost trying again in 0.5 s")
            time.sleep(0.5)
            aruco_pos_error = find_aruco(tello, aruco_id)
            raise("Aruco symbol lost")

        error_x, error_y = aruco_pos_error


        now = time.time()
        dt = now - prev_time
        prev_time = now


        vx = pid_y.update(error_y, dt) * -1
        vy = pid_x.update(error_x, dt)


        # descent only if roughly centered
        if abs(error_x) < landing_threshold and abs(error_y) < landing_threshold:
            vz = -descent_speed
            tello.move_down(vz)
        else:
            vz = 0

        vx = min(20, vx)
        vy = min(20, vy)


        tello.move_forward(vx)
        tello.move_left(vy)



        print(f"errorX:{error_x} errorY:{error_y}")


        # final landing
        if abs(error_x) < 10 and abs(error_y) < 10 and tello.get_height() < 20:
            print("Landing")
            tello.land()
            break


def search4landing_place(tello, lsp):
    aruco_pos_error = None
    change_move_size = False
    current_move = lsp.step_size

    while aruco_pos_error is None:
        try:
            frame_read = tello.get_frame_read()
            frame = frame_read.frame
        except:
            print("failed to obtain frame")
            time.sleep(0.5)
            continue

        if frame is None:
            continue


        time.sleep(0.25)
        aruco_pos_error = find_aruco(tello=tello)


        if aruco_pos_error is not None:
            print("Safe to land.")
            try:
                pid_landing(tello)
                return
            except:
                print("Aruco lost during landing return to the search")
                continue


        # move to the next position
        tello.move_forward(current_move)

        if lsp.clockwise:
            tello.rotate_clockwise(90)
        else:
            tello.rotate_counter_clockwise(90)


        # adjust moving distance every second iteration
        if change_move_size:
            current_move += lsp.step_size
            print(f"new search size:{current_move}")

        change_move_size = not change_move_size


        # check if inbounds
        if current_move > lsp.max_search_size:
            raise("Landing site not found in the desired size — initiate emergency landing")