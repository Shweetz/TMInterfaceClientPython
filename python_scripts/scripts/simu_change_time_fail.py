from tminterface.interface import TMInterface
from tminterface.client import Client, run_client

import struct
import sys

TIME_DIFF = 40 

class MainClient(Client):
    def on_registered(self, iface: TMInterface) -> None:
        print(f'Registered to {iface.server_name}')
        iface.execute_command('set controller none') # TMI bruteforce off

    def on_deregistered(self, iface: TMInterface) -> None:
        print(f'Deregistered from {iface.server_name}')

    def on_simulation_begin(self, iface):
        iface.remove_state_validation() # keep simulation going even if inputs and replay stop matching

        self.buffer = iface.get_event_buffer()
        self.base_run_time = self.buffer.events_duration
        print(f"Base run time: {self.base_run_time}")

        self.states = {}
        for i in range(self.base_run_time // 10):
            self.states[i] = None
        
    def on_simulation_step(self, iface: TMInterface, _time: int):
        self.race_time = _time

        self.states[_time // 10] = iface.get_simulation_state()

        if _time - TIME_DIFF < 0:
            # wait at start
            return

        print(self.states[_time // 10].timers[1])
        self.states[_time // 10].timers[1] = _time - TIME_DIFF
        iface.rewind_to_state(self.states[(_time - TIME_DIFF) // 10])


def main():
    server_name = f'TMInterface{sys.argv[1]}' if len(sys.argv) > 1 else 'TMInterface0'
    print(f'Connecting to {server_name}...')
    run_client(MainClient(), server_name)

if __name__ == '__main__':
    main()
