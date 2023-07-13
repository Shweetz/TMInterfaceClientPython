from tminterface.interface import TMInterface
from tminterface.client import Client, run_client
from tminterface.util import mat3_to_quat
# from tminterface.util import mat3_to_quat, euler_to_quaternion, quaternion_to_rotation_matrix

import math
import numpy as np
import sys

# This script creates a bugged run that can only be validated
TIME_DIFF = 40
RUN_TIME = 26090

class MainClient(Client):
    def on_registered(self, iface: TMInterface) -> None:
        print(f'Registered to {iface.server_name}')
        self.recording = False
        self.states = []
        self.state_index = 0
        print(f"{self.recording=}")
        self.ax = 0
        self.bx = 0

    def on_run_step(self, iface, _time):
        state = iface.get_simulation_state()

        if _time == -2500:
            self.recording = not self.recording
            print(f"{self.recording=}")

            if self.recording:
                iface.execute_command('load tmp.txt')
                self.states = []
            else:
                iface.execute_command('unload')

        elif _time < 0:
            return
        
        if self.recording:
            self.states.append(state)

        else:
            if self.state_index < 4:
                ostate = self.states[0]
            elif self.state_index < len(self.states) - 4:
                ostate = self.states[self.state_index - 4]
            else:
                return
            
            state.position = ostate.position
            state.dyna.current_state.linear_speed = ostate.dyna.current_state.linear_speed
            state.dyna.current_state.angular_speed = ostate.dyna.current_state.angular_speed
                
            iface.rewind_to_state(state)

            self.state_index += 1

def main():
    server_name = f'TMInterface{sys.argv[1]}' if len(sys.argv) > 1 else 'TMInterface0'
    print(f'Connecting to {server_name}...')
    run_client(MainClient(), server_name)

if __name__ == '__main__':
    main()
