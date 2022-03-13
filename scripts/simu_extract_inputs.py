import os
import sys
import time

from tminterface.interface import TMInterface
from tminterface.client import Client, run_client

DECIMAL_SYNTAX = True
OUTPUT_FILE = "extracted_inputs.txt"

class MainClient(Client):
    def on_registered(self, iface: TMInterface) -> None:
        print(f'Registered to {iface.server_name}')

    def on_deregistered(self, iface: TMInterface) -> None:
        print(f'Deregistered from {iface.server_name}')

    def on_simulation_begin(self, iface):
        begin = time.time()
        
        iface.remove_state_validation()

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


def to_sec(inputs_str: str) -> str:
    """Transform a string containing lines of inputs to min:sec.ms format"""

    def ms_to_sec_line(line: str) -> str:
        """Converter ms->sec for entire line"""
        if "." in line or line == "":
            return line
        splits = line.split(" ")
        if "-" in splits[0]:            
            press_time, rel_time = splits[0].split("-")
            splits[0] = ms_to_sec(press_time) + "-" + ms_to_sec(rel_time)
        else:
            splits[0] = ms_to_sec(splits[0])
        return " ".join(splits)

    def ms_to_sec(line_time: str) -> str:
        """Converter ms->sec for time value
        Example: '763900' -> '12:43.90'
        """
        if type(line_time) == int:
            line_time = str(line_time)

        if "." in line_time or line_time == "0":
            return line_time

        minutes, milliseconds = divmod(int(line_time), 60 * 1000)
        hours, minutes = divmod(minutes, 60)
        seconds = milliseconds / 1000

        value = ""    
        if hours > 0:
            value += str(hours) + ":"
        if minutes > 0 or hours > 0:
            value += str(minutes) + ":"
        value += f"{seconds:.2f}"

        return value

    result_string = ""
    for line in inputs_str.split("\n"):
        if line != "":
            result_string += ms_to_sec_line(line) + "\n"
    
    return result_string

def main():
    server_name = f'TMInterface{sys.argv[1]}' if len(sys.argv) > 1 else 'TMInterface0'
    print(f'Connecting to {server_name}...')
    run_client(MainClient(), server_name)

if __name__ == '__main__':
    main()
