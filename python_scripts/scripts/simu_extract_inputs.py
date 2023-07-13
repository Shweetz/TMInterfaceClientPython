import os
import sys
import time

from tminterface.interface import TMInterface
from tminterface.client import Client, run_client

from SUtil import to_sec

# For large replays, you need a big TMI buffer size (default is 65536)
# 1 input = 8 bytes so buffer size will need to be at least 8x more than the number of inputs
# You also need to start TMI in cmd with a parameter: "TMInterface.exe /serversize=1000000"
BUFFER_SIZE = 1000000

DECIMAL_SYNTAX = True
OUTPUT_FILE = "extracted_inputs.txt"

class MainClient(Client):
    def on_registered(self, iface: TMInterface) -> None:
        print(f'Registered to {iface.server_name}')

    def on_deregistered(self, iface: TMInterface) -> None:
        print(f'Deregistered from {iface.server_name}')

    def on_simulation_begin(self, iface):        
        # Don't waste time validating the replay
        iface.set_simulation_time_limit(0)

        begin = time.time()

        # Grab inputs from the EventBufferData
        self.event_buffer = iface.get_event_buffer()        
        inputs_str = self.event_buffer.to_commands_str()

        # Convert inputs
        if DECIMAL_SYNTAX:
            inputs_str = to_sec(inputs_str)

        # Write inputs in file
        res_file = os.path.expanduser('~/Documents') + "/TMInterface/Scripts/" + OUTPUT_FILE
        with open(res_file, "w") as f:
            f.write(inputs_str)

        print(f"Done in {time.time() - begin} sec")

def main():
    server_name = f'TMInterface{sys.argv[1]}' if len(sys.argv) > 1 else 'TMInterface0'
    print(f'Connecting to {server_name}...')
    run_client(MainClient(), server_name, buffer_size=BUFFER_SIZE)

if __name__ == '__main__':
    main()
