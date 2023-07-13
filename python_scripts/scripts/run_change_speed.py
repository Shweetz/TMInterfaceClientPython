from tminterface.interface import TMInterface
from tminterface.client import Client, run_client

import struct
import sys

# CHANGE_TIME = 19500 
MIN_TIME = 23000 
MAX_TIME = 23000 
COEFF = 1.00001 # 1.01 = 101%

class MainClient(Client):
    def on_registered(self, iface: TMInterface) -> None:
        print(f'Registered to {iface.server_name}')

    def on_run_step(self, iface, _time):
        # if _time == MIN_TIME - 10:
        #     state = iface.get_simulation_state()
        #     print(state.input_steer_event.analog_value)

        print(f"{iface.get_simulation_state().cp_data.cp_times=}")
        print(f"{iface.get_simulation_state().cp_data.cp_states=}")

        # if MIN_TIME <= _time <= MAX_TIME:
        #     state = iface.get_simulation_state()
        #     # print(state.input_steer_event.analog_value)
        #     state.velocity = [v * COEFF for v in state.velocity]
        #     # state.velocity = [state.velocity[0] * (2-COEFF), state.velocity[1] * COEFF, state.velocity[2]]
        #     iface.rewind_to_state(state)
        
        #     print(len(iface.get_event_buffer().find(time=23000)))
            
        #     print(iface.get_simulation_state().input_accelerate)
        #     print(iface.get_simulation_state().input_steer)
        #     print(iface.get_simulation_state().input_steer_event.analog_value)

        # if _time == MAX_TIME + 10:
        
        #     print(len(iface.get_event_buffer().find(time=23000)))

        #     print(iface.get_simulation_state().input_accelerate)
        #     print(iface.get_simulation_state().input_steer)
        #     print(iface.get_simulation_state().input_steer_event.analog_value)
        #     print("")

def main():
    server_name = f'TMInterface{sys.argv[1]}' if len(sys.argv) > 1 else 'TMInterface0'
    print(f'Connecting to {server_name}...')
    run_client(MainClient(), server_name)

if __name__ == '__main__':
    main()
