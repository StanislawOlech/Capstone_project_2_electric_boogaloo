import cv2
import numpy as np
from djitellopy import Tello
import time

# --- KONFIGURACJA ARUCO (Nowy standard OpenCV) ---
aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
aruco_params = cv2.aruco.DetectorParameters()
detector = cv2.aruco.ArucoDetector(aruco_dict, aruco_params)

# --- PARAMETRY BEZPIECZEŃSTWA I LOTU ---
MAX_ALTITUDE = 120         # Maksymalna wysokość (cm) - ląduj jeśli wyżej
WIDTH, HEIGHT = 320, 240
CENTER_X, CENTER_Y = WIDTH // 2, HEIGHT // 2
DEADZONE = 25
SPEED = 3

tello = Tello()
tello.connect()
print(f"Poziom baterii: {tello.get_battery()}%")

tello.set_video_direction(1) # Kamera dolna
tello.streamon()
tello.set_video_direction(1) # Kamera dolna
frame_read = tello.get_frame_read()

tello.takeoff()

time.sleep(1)
tello.move_down(50)

try:
    while True:
        img = frame_read.frame
        if img is None: continue
        
        # 1. Sprawdzenie wysokości (Failsafe)
        current_alt = tello.get_distance_tof()
        if current_alt > MAX_ALTITUDE:
            print(f"ALARM: Dron za wysoko ({current_alt}cm)! Wymuszam lądowanie.")
            break

        # 2. Przetwarzanie obrazu do debugowania
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Maska binarna - pomaga zobaczyć czy ArUco nie jest "zalane" światłem
        _, debug_thresh = cv2.threshold(gray, 100, 255, cv2.THRESH_BINARY)
        
        # 3. Detekcja ArUco
        corners, ids, rejected = detector.detectMarkers(gray)

        lr, fb = 0, 0
        target_found = False

        if ids is not None and 13 in ids:
            target_found = True
            idx = np.where(ids == 13)[0][0]
            c = corners[idx][0]
            
            # Środek znacznika
            target_x = int((c[0][0] + c[1][0] + c[2][0] + c[3][0]) / 4)
            target_y = int((c[0][1] + c[1][1] + c[2][1] + c[3][1]) / 4)

            # Wizualizacja na głównym oknie
            cv2.aruco.drawDetectedMarkers(img, corners, ids)
            cv2.circle(img, (target_x, target_y), 5, (0, 0, 255), -1)

            # Logika sterowania
            if target_x < CENTER_X - DEADZONE: lr = -SPEED
            elif target_x > CENTER_X + DEADZONE: lr = SPEED
            
            if target_y < CENTER_Y - DEADZONE: fb = SPEED
            elif target_y > CENTER_Y + DEADZONE: fb = -SPEED

            print(f"NAMIERZONO ID 13: Alt={current_alt}cm, X={target_x}, Y={target_y}")

            # Lądowanie
            if abs(target_x - CENTER_X) < DEADZONE and abs(target_y - CENTER_Y) < DEADZONE:
                print("IDEALNA POZYCJA. Lądowanie finalne...")
                tello.send_rc_control(0, 0, 0, 0)
                time.sleep(0.5)
                tello.land()
                break
        else:
            # Szukanie (tylko jeśli pod spodem jest biały stół)
            white_ratio = np.sum(debug_thresh == 255) / (WIDTH * HEIGHT)
            if white_ratio > 0.2:
                fb = 5
                print(f"Szukam ID 13 na stole (widoczność stołu: {int(white_ratio*100)}%)...")
            else:
                fb = -SPEED
                print("BRAK STOŁU! Cofam do bezpiecznej strefy.")

        # Wyślij komendy
        tello.send_rc_control(lr, fb, 0, 0)

        # OKNA DEBUGOWANIA
        # Wyświetlamy status na obrazie
        cv2.putText(img, f"Alt: {current_alt}cm", (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        cv2.imshow("Kamera Dolna (Live)", img)
        cv2.imshow("Debug: Maska Binarna", debug_thresh)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

except Exception as e:
    print(f"Błąd krytyczny: {e}")

finally:
    print("Zamykanie systemów...")
    try:
        tello.send_rc_control(0, 0, 0, 0)
        tello.land()
    except:
        pass
    tello.streamoff()
    cv2.destroyAllWindows()