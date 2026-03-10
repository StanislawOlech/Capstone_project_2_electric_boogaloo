from djitellopy import Tello
import numpy as np
from safe_landing import search4landing_place, Landing_Search_Params


def main():
    landing_search_params = Landing_Search_Params(step_size=20,
                                                  max_search_size=100,
                                                  clockwise=True)

    tello = Tello()
    tello.connect()
    print(tello.get_battery())

    tello.streamon()
    tello.set_video_direction(1)


    tello.takeoff()

    try:
        search4landing_place(tello=tello,
                            lsp=landing_search_params)
    except Exception as e:
        print(f"Error occurred: {e}")
        tello.land()
        print("Emergency landing occurred")

    tello.streamoff()

if __name__ == "__main__":
    main()