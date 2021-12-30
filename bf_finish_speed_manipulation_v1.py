
from tminterface.interface import TMInterface
from tminterface.client import Client, run_client

import math
import numpy
import sys
import time

# MUST GIVE INPUTS TIME FOR ON_RUN_STEP
INPUTS_TIME = 51430

# state = iface.get_simulation_state()
# state.velocity = [100, 0, 0]
# iface.rewind_to_state(state)

class MainClient(Client):
    def __init__(self) -> None:
        self.cp_count = -1
        self.lowest_time = INPUTS_TIME
        self.base_velocity = None
        self.finish_crossed = False
        # self.nb_rewinds = 0
        self.min_coeff = 0
        self.max_coeff = 1

    def on_registered(self, iface: TMInterface) -> None:
        print(f'Registered to {iface.server_name}')

    def on_simulation_begin(self, iface):
        self.lowest_time = iface.get_event_buffer().events_duration

    def on_run_step(self, iface, _time):
        self.on_step(iface, _time)

    def on_simulation_step(self, iface, _time):
        self.on_step(iface, _time)

    def on_step(self, iface, _time):
        if _time == 0:
            self.min_coeff = 0
            self.max_coeff = 1

        if _time == self.lowest_time - 10:
            # Save base state to rewind before any change
            self.base_state = iface.get_simulation_state()
            
            # print()

        if _time == self.lowest_time:
            self.coeff = (self.min_coeff + self.max_coeff) / 2

            self.state = iface.get_simulation_state()

            # Save base run velocity
            if not self.base_velocity:
                self.base_velocity = self.state.velocity

            # Apply a coefficient to the speed on the last tick
            self.state.velocity = [v * self.coeff for v in self.base_velocity]
            iface.rewind_to_state(self.state)

            # print(f"pos_z={self.state.position[2]}")
            # print(f"vel_z={self.state.velocity[2]}")

        if _time == self.lowest_time + 10:
            # print(f"pos_z={iface.get_simulation_state().position[2]} (tick+1)")

            time_with_speed_coeff = (_time-10 + self.coeff*10) / 1000

            if self.finish_crossed:
                # print(f"finish with {self.coeff}")
                print(f"{time_with_speed_coeff}: finish")
                self.max_coeff = self.coeff
            else:
                # print(f"no finish with {self.coeff}")
                print(f"{time_with_speed_coeff}: no finish")
                self.min_coeff = self.coeff

            # time.sleep(0.1)
            if self.max_coeff - self.min_coeff > 0.001:
                iface.rewind_to_state(self.base_state)
            self.finish_crossed = False
            # self.nb_rewinds += 1
            # self.rewinded = True

        # if _time == self.lowest_time + 20:

    def on_checkpoint_count_changed(self, iface, current: int, target: int):
        self.cp_count = current
        if current == target:
            self.finish_crossed = True

def main():
    server_name = f'TMInterface{sys.argv[1]}' if len(sys.argv) > 1 else 'TMInterface0'
    print(f'Connecting to {server_name}...')
    run_client(MainClient(), server_name)

if __name__ == '__main__':
    main()
