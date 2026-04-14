import pygame
import time

def monitor_controller():
    pygame.init()
    pygame.joystick.init()

    if pygame.joystick.get_count() == 0:
        print("Błąd: Nie znaleziono kontrolera! Podłącz pad i spróbuj ponownie.")
        return

    # Inicjalizacja pierwszego znalezionego pada
    joystick = pygame.joystick.Joystick(0)
    joystick.init()

    print(f"--- Monitorowanie: {joystick.get_name()} ---")
    print("Naciskaj przyciski lub ruszaj gałkami (Ctrl+C aby zakończyć)")

    try:
        while True:
            pygame.event.pump() # Odśwież stan zdarzeń

            # 1. Sprawdzanie przycisków (0 / 1)
            for i in range(joystick.get_numbuttons()):
                if joystick.get_button(i):
                    print(f"[BUTTON] Numer: {i}")

            # 2. Sprawdzanie osi (gałki i triggery)
            # Wypisujemy tylko jeśli wychylenie jest większe niż 0.1 (martwa strefa)
            for i in range(joystick.get_numaxes()):
                axis_val = joystick.get_axis(i)
                if abs(axis_val) > 0.1:
                    print(f"[AXIS] Numer: {i} | Wartość: {axis_val:.2f}")

            # 3. Sprawdzanie strzałek (D-pad)
            for i in range(joystick.get_numhats()):
                hat_val = joystick.get_hat(i)
                if hat_val != (0, 0):
                    print(f"[HAT] Numer: {i} | Stan: {hat_val}")

            time.sleep(0.1) # Małe opóźnienie dla czytelności konsoli

    except KeyboardInterrupt:
        print("\nZakończono monitorowanie.")
        pygame.quit()

if __name__ == "__main__":
    monitor_controller()