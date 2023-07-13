from tminterface.interface import TMInterface
from tminterface.client import Client, run_client

import numpy
import sys

class MainClient(Client):
    def on_registered(self, iface: TMInterface) -> None:
        print(f'Registered to {iface.server_name}')        

    def on_run_step(self, iface, _time):
        state = iface.get_simulation_state()
        speed_kmh = round(min(numpy.linalg.norm(state.velocity) * 3.6, 1000))

        if _time == 0:
            self.nb_boosts = 0

        if _time > 0:
            if speed_kmh > self.last_speed_kmh + 10:
                print(f"{_time/1000:.2f}: speed boost from {self.last_speed_kmh} to {speed_kmh} km/h")
                self.nb_boosts += 1

        self.last_speed_kmh = speed_kmh

    def on_checkpoint_count_changed(self, iface: TMInterface, current: int, target: int):
        if current == target:
            print(f"Race finished with {self.nb_boosts} speed boosts")
             
def main():
    server_name = f'TMInterface{sys.argv[1]}' if len(sys.argv) > 1 else 'TMInterface0'
    print(f'Connecting to {server_name}...')
    run_client(MainClient(), server_name)

if __name__ == '__main__':
    main()
