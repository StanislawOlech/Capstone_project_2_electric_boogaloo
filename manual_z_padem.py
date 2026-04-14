import tkinter as tk
from tkinter import ttk
import cv2
import cv2.aruco as aruco
import pygame
import time
import numpy as np
from PIL import Image, ImageTk
from djitellopy import Tello

class TelloControlGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Tello Capstone - ArUco Auto-Landing")
        
        # --- Konfiguracja ArUco ---
        self.aruco_dict = aruco.getPredefinedDictionary(aruco.DICT_4X4_50)
        self.aruco_params = aruco.DetectorParameters()
        self.detector = aruco.ArucoDetector(self.aruco_dict, self.aruco_params)
        self.target_id = 13

        # --- Stan Autopilota i ArUco ---
        self.auto_pilot = False
        self.marker_vector = [0, 0, 0] # [lr, fb, up_down]
        self.landing_in_progress = False

        # --- Inicjalizacja Pada ---
        pygame.init()
        pygame.joystick.init()
        self.joystick = None
        if pygame.joystick.get_count() > 0:
            self.joystick = pygame.joystick.Joystick(0)
            self.joystick.init()
            print(f"Połączono z padem: {self.joystick.get_name()}")

        # --- Inicjalizacja drona ---
        self.tello = Tello()
        self.tello.connect()
        self.tello.streamon()
        
        self.speed = 50
        self.current_camera = 0 
        self.is_busy = False 

        self.setup_ui()
        self.update_frame()
        self.poll_joystick() 

    def setup_ui(self):
        self.video_label = tk.Label(self.root)
        self.video_label.grid(row=0, column=0, columnspan=3, padx=10, pady=10)

        self.info_label = tk.Label(self.root, text="Bateria: --% | Kamera: Przód", font=("Arial", 10))
        self.info_label.grid(row=2, column=0, columnspan=3)

        sidebar = tk.Frame(self.root)
        sidebar.grid(row=1, column=0, padx=20)

        tk.Button(sidebar, text="START (TAKEOFF)", bg="green", fg="white", 
                  command=lambda: self.safe_command(self.tello.takeoff)).pack(fill='x')
        
        tk.Button(sidebar, text="LĄDUJ (LAND)", bg="red", fg="white", 
                  command=lambda: self.safe_command(self.tello.land)).pack(fill='x', pady=5)
        
        tk.Label(sidebar, text="Maks. Prędkość:").pack()
        self.speed_slider = tk.Scale(sidebar, from_=10, to=100, orient="horizontal", command=self.set_speed)
        self.speed_slider.set(50)
        self.speed_slider.pack()

        tk.Button(sidebar, text="Zmień Kamerę", 
                  command=lambda: self.safe_command(self.switch_camera)).pack(fill='x', pady=10)

    def set_speed(self, val):
        self.speed = int(val)

    def safe_command(self, command_func, *args):
        self.is_busy = True
        try:
            command_func(*args)
            time.sleep(0.3)
        except Exception as e:
            print(f"Błąd komendy: {e}")
        finally:
            self.is_busy = False
    
    def takeoff_sequence(self):
        """Wymusza czysty start i resetuje stany autopilota"""
        print("Inicjalizacja startu...")
        self.auto_pilot = False
        self.landing_in_progress = False
        self.marker_vector = [0, 0, 0]
        # Wysłanie komendy startu tylko jeśli dron zgłasza, że nie leci
        if not self.tello.is_flying:
            self.safe_command(self.tello.takeoff)

    def switch_camera(self):
        self.current_camera = 1 if self.current_camera == 0 else 0
        self.tello.set_video_direction(self.current_camera)
        cam_name = "Dół" if self.current_camera == 1 else "Przód"
        print(f"Zmiana kamery na: {cam_name}")

    def handle_button_press(self, button_id):
        if button_id == 1: # B
            print("AWARYJNE LĄDOWANIE / STOP AUTOPILOT")
            self.auto_pilot = False
            self.safe_command(self.tello.land)
            return

        if button_id == 2 and not self.tello.is_flying: # A
            self.takeoff_sequence()

        elif button_id == 3: # X
            self.safe_command(self.switch_camera)

        elif button_id == 0: # Y
            if self.current_camera == 1:
                self.auto_pilot = not self.auto_pilot
                print(f"Autopilot: {'WŁĄCZONY' if self.auto_pilot else 'WYŁĄCZONY'}")
            else:
                print("Przełącz na dolną kamerę przed włączeniem autopilota!")

    def poll_joystick(self):
        if self.joystick:
            for event in pygame.event.get():
                if event.type == pygame.JOYBUTTONDOWN:
                    self.handle_button_press(event.button)

            if not self.is_busy and self.tello.is_flying:
                if self.auto_pilot:
                    lr, fb, down = self.marker_vector
                    self.tello.send_rc_control(lr, fb, down, 0)
                else:
                    lr = int(self.joystick.get_axis(0) * self.speed)
                    fb = int(self.joystick.get_axis(1) * self.speed * -1)
                    self.tello.send_rc_control(lr, fb, 0, 0)

        if time.time() % 2 < 0.1:
            try:
                mode = "AUTO" if self.auto_pilot else "MANUAL"
                cam_text = "Dół" if self.current_camera == 1 else "Przód"
                self.info_label.config(text=f"Bateria: {self.tello.get_battery()}% | Tryb: {mode} | Kamera: {cam_text}")
            except: pass

        self.root.after(50, self.poll_joystick)

    def update_frame(self):
        try:
            frame = self.tello.get_frame_read().frame
            if frame is not None:
                frame = cv2.resize(frame, (640, 480))
                new_vector = [0, 0, 0]

                if self.current_camera == 1:
                    frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
                    frame = cv2.resize(frame, (640, 480))
                    
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    corners, ids, rejected = self.detector.detectMarkers(gray)
                    
                    if ids is not None and self.target_id in ids.flatten():
                        idx = np.where(ids.flatten() == self.target_id)[0][0]
                        marker_corners = corners[idx][0]
                        aruco.drawDetectedMarkers(frame, corners, ids)
                        
                        m_center_x = int(np.mean(marker_corners[:, 0]))
                        m_center_y = int(np.mean(marker_corners[:, 1]))
                        img_center_x, img_center_y = 320, 240
                        
                        # --- NOWA LOGIKA P (PROPORCJONALNA) ---
                        # Obliczamy błąd (odległość od środka w pikselach)
                        error_x = m_center_x - img_center_x
                        error_y = m_center_y - img_center_y

                        # Współczynnik Kp (zacznij od 0.15, jeśli będzie za wolny - zwiększ do 0.2)
                        kp = 0.15 
                        
                        # Prędkość jest proporcjonalna do błędu
                        lr = int(error_x * kp)
                        fb = int(error_y * kp * -1) # Mnożymy przez -1, bo osie Y w OpenCV są odwrócone

                        # Saturacja (ograniczenie), żeby dron nie "wariował" przy dużym błędzie
                        max_auto_speed = 30
                        lr = max(min(lr, max_auto_speed), -max_auto_speed)
                        fb = max(min(fb, max_auto_speed), -max_auto_speed)

                        # Martwa strefa (jeśli błąd jest malutki, ustaw 0, żeby nie drżał)
                        if abs(error_x) < 20: lr = 0
                        if abs(error_y) < 20: fb = 0

                        # --- SCHODZENIE ---
                        down = -15 if self.auto_pilot else 0
                        
                        new_vector = [lr, fb, down]
                        
                        # Wyświetlanie danych debugowania na ekranie
                        cv2.putText(frame, f"ErrX: {error_x} ErrY: {error_y}", (10, 90), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
                        
                        # Wizualizacja tylko gdy marker istnieje
                        cv2.putText(frame, "AUTOLAND ACTIVE", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                        cv2.circle(frame, (m_center_x, m_center_y), 5, (0, 0, 255), -1)
                    
                    elif self.auto_pilot and not self.landing_in_progress:
                        print("ArUco zgubione - LĄDOWANIE FINALNE")
                        self.auto_pilot = False
                        self.landing_in_progress = True
                        self.safe_command(self.tello.land)

                self.marker_vector = new_vector

                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(frame)
                imgtk = ImageTk.PhotoImage(image=img)
                self.video_label.imgtk = imgtk
                self.video_label.configure(image=imgtk)
        except Exception as e:
            print(f"Błąd wideo: {e}")
        
        self.root.after(20, self.update_frame)

if __name__ == "__main__":
    root = tk.Tk()
    app = TelloControlGUI(root)
    root.mainloop()