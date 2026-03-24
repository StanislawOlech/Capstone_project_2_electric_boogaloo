import tkinter as tk
from tkinter import ttk
import cv2
import pygame
import time
from PIL import Image, ImageTk
from djitellopy import Tello

class TelloControlGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Tello Capstone - PS3 Final Control")
        
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
        self.is_busy = False # Uniwersalna flaga blokująca RC dla KAŻDEJ komendy systemowej

        self.setup_ui()
        self.update_frame()
        self.poll_joystick() 

    def setup_ui(self):
        # --- Podgląd wideo ---
        self.video_label = tk.Label(self.root)
        self.video_label.grid(row=0, column=0, columnspan=3, padx=10, pady=10)

        # --- Panel Informacyjny ---
        self.info_label = tk.Label(self.root, text="Bateria: --% | Kamera: Przód", font=("Arial", 10))
        self.info_label.grid(row=2, column=0, columnspan=3)

        # --- Sidebar ---
        sidebar = tk.Frame(self.root)
        sidebar.grid(row=1, column=0, padx=20)

        # Wykorzystujemy safe_command dla startu i lądowania
        tk.Button(sidebar, text="START (TAKEOFF)", bg="green", fg="white", 
                  command=lambda: self.safe_command(self.tello.takeoff)).pack(fill='x')
        
        tk.Button(sidebar, text="LĄDUJ (LAND)", bg="red", fg="white", 
                  command=lambda: self.safe_command(self.tello.land)).pack(fill='x', pady=5)
        
        tk.Label(sidebar, text="Maks. Prędkość:").pack()
        self.speed_slider = tk.Scale(sidebar, from_=10, to=100, orient="horizontal", command=self.set_speed)
        self.speed_slider.set(50)
        self.speed_slider.pack()

        # Wykorzystujemy safe_command dla zmiany kamery
        tk.Button(sidebar, text="Zmień Kamerę", 
                  command=lambda: self.safe_command(self.switch_camera)).pack(fill='x', pady=10)

    def set_speed(self, val):
        self.speed = int(val)

    def safe_command(self, command_func, *args):
        """Wstrzymuje komendy RC z pada, wykonuje komendę i wznawia RC."""
        self.is_busy = True
        try:
            command_func(*args)
            time.sleep(0.3) # Dajemy dronowi ułamek sekundy na przetworzenie odpowiedzi OK
        except Exception as e:
            print(f"Błąd komendy: {e}")
        finally:
            self.is_busy = False

    def switch_camera(self):
        self.current_camera = 1 if self.current_camera == 0 else 0
        self.tello.set_video_direction(self.current_camera)
        cam_name = "Dół" if self.current_camera == 1 else "Przód"
        print(f"Zmiana kamery na: {cam_name}")

    def poll_joystick(self):
        if self.joystick:
            for event in pygame.event.get():
                if event.type == pygame.JOYBUTTONDOWN:
                    self.handle_button_press(event.button)

            # Wysyłaj RC tylko jeśli dron nie jest zajęty inną komendą i leci
            if not self.is_busy and self.tello.is_flying:
                lr = int(self.joystick.get_axis(0) * self.speed)
                fb = int(self.joystick.get_axis(1) * self.speed * -1) 
                
                if abs(lr) < 15: lr = 0
                if abs(fb) < 15: fb = 0

                self.tello.send_rc_control(lr, fb, 0, 0)

        # Aktualizacja statusu baterii
        if time.time() % 2 < 0.1: 
            try:
                cam_text = "Dół" if self.current_camera == 1 else "Przód"
                self.info_label.config(text=f"Bateria: {self.tello.get_battery()}% | Kamera: {cam_text}")
            except:
                pass

        self.root.after(50, self.poll_joystick)

    def handle_button_press(self, button_id):
        if not self.tello.is_flying or self.is_busy:
            return

        if self.tello.get_battery() < 30:
            print("Zbyt niska bateria na akrobacje!")
            return

        direction = None
        if button_id == 4: direction = 'l'
        elif button_id == 5: direction = 'r'
        elif button_id == 6: direction = 'f'
        elif button_id == 7: direction = 'b'

        if direction:
            print(f"Żądanie flipa: {direction}...")
            # Flipy również przepuszczamy przez safe_command!
            self.safe_command(self.tello.flip, direction)

    def update_frame(self):
        try:
            frame = self.tello.get_frame_read().frame
            if frame is not None:
                frame = cv2.resize(frame, (640, 480))
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(frame)
                imgtk = ImageTk.PhotoImage(image=img)
                self.video_label.imgtk = imgtk
                self.video_label.configure(image=imgtk)
        except:
            pass
        self.root.after(20, self.update_frame)


if __name__ == "__main__":
    root = tk.Tk()
    app = TelloControlGUI(root)
    root.mainloop()