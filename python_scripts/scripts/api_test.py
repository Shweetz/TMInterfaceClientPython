from tminterface.interface import TMInterface
from tminterface.client import Client, run_client

import struct
import sys

class MainClient(Client):
    def on_registered(self, iface: TMInterface) -> None:
        print(f'Registered to {iface.server_name}')

    def on_run_step(self, iface, _time):
        state = iface.get_simulation_state()
        if _time % 500 != 0:
            return
        print(f"{state.velocity}")
        print(f"{state.angular_velocity}")
        print(f"{state.wheels_on_ground=}")
        print(f"{state.colliding=}")
        print(f"{state.free_wheeling=}")
        print(f"{state.sliding=}")
    
    def is_car_crashed(self, state):
        return struct.unpack('i', state.scene_mobil[1500:1504])[0]

def main():
    server_name = f'TMInterface{sys.argv[1]}' if len(sys.argv) > 1 else 'TMInterface0'
    print(f'Connecting to {server_name}...')
    run_client(MainClient(), server_name)

if __name__ == '__main__':
    main()
