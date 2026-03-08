from djitellopy import Tello
import numpy as np
from safe_landing import search4landing_place, Landing_Search_Params


def main():
    landing_search_params = Landing_Search_Params(step_size=20,
                                                  max_size=100)

    tello = Tello()
    tello.connect()

    tello.streamon()
    tello.set_video_direction(1)


    tello.takeoff()

    try:
        search4landing_place(tello=tello,
                             lsp=landing_search_params)
    except:
        tello.land()
        print("emergency landing occurred")

    tello.streamoff()

if __name__ == "__main__":
    main()