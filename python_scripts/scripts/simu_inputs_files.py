import os
import sys

from tminterface.interface import TMInterface
from tminterface.client import Client, run_client
from tminterface.constants import ANALOG_STEER_NAME, BINARY_ACCELERATE_NAME, BINARY_BRAKE_NAME, BINARY_LEFT_NAME, BINARY_RIGHT_NAME, BINARY_RESPAWN_NAME, BINARY_RACE_FINISH_NAME
from tminterface.commandlist import CommandList, InputCommand, InputType

# Usage:
# 0. Prepare some input files for load_inputs_from_file()
# 1. Start TMInterface
# 2. Start this script, on_registered() should be called (check console for its print)
# 3. Validate a replay that finishes the desired track (the replay will be played as the base run until TIME_TO_REWIND_TO)

TIME_TO_REWIND_TO = 0 # for example, if you are satisfied with the base run inputs before 1530ms, set this to 1530

class MainClient(Client):
    def __init__(self) -> None:
        self.state_min_change = None
        self.file_number = 0
        self.finished = False

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
        
    def on_simulation_step(self, iface: TMInterface, _time: int):
        self.race_time = _time

        if not self.state_min_change:
            # During base run, store the state that every iteration will rewind to
            if self.race_time == TIME_TO_REWIND_TO:
                self.state_min_change = iface.get_simulation_state()
                print(f"self.state_min_change created at {self.race_time}")

                self.load_inputs_from_file(self.get_filename())
                iface.set_event_buffer(self.buffer)

        else:
            # Check for run finish
            if self.finished:
                print(f"{self.get_filename()} finished with a time of {self.race_time - 10}")
                self.finished = False

            # Time to rewind and start a new iteration
            if self.finished or self.race_time == self.base_run_time:
                # Load new file in the buffer
                self.file_number += 1
                self.load_inputs_from_file(self.get_filename())
                iface.set_event_buffer(self.buffer)

                iface.rewind_to_state(self.state_min_change)

        # Printing
        state = iface.get_simulation_state()
        
        pos = state.position
        vel = state.velocity
        aim = state.yaw_pitch_roll
        print(f'Time: {self.race_time}, Position: {pos}, Velocity: {vel}, Aim Direction: {aim}')

    def on_checkpoint_count_changed(self, iface: TMInterface, current: int, target: int):
        print(f"{current=}, {target=}")
        if current == target:
            self.finished = True
            iface.prevent_simulation_finish()

    def load_inputs_from_file(self, filename):
        """Load a inputs to bruteforce from a file instead of a replay"""
        inputs_file = os.path.join(os.path.expanduser('~'), "Documents", "TMInterface", "Scripts", filename)
        
        if not os.path.exists(inputs_file):
            print(f"{inputs_file} doesn't exist.")
            sys.exit()
        
        print(f"Loading inputs from {inputs_file}")

        # Replace buffer contents with inputs from file
        self.buffer.clear()
        
        cmdlist = CommandList(open(inputs_file, 'r'))
        commands = [cmd for cmd in cmdlist.timed_commands if isinstance(cmd, InputCommand)]

        for command in commands:
            if   command.input_type == InputType.UP:      command.input = BINARY_ACCELERATE_NAME
            elif command.input_type == InputType.DOWN:    command.input = BINARY_BRAKE_NAME
            elif command.input_type == InputType.LEFT:    command.input = BINARY_LEFT_NAME
            elif command.input_type == InputType.RIGHT:   command.input = BINARY_RIGHT_NAME
            elif command.input_type == InputType.RESPAWN: command.input = BINARY_RESPAWN_NAME
            elif command.input_type == InputType.STEER:   command.input = ANALOG_STEER_NAME
            else: print(f"{command.input_type=}"); continue

            self.buffer.add(command.timestamp, command.input, command.state)

    def get_filename(self):
        return "inputs_" + str(self.file_number) + ".txt"

def main():
    server_name = f'TMInterface{sys.argv[1]}' if len(sys.argv) > 1 else 'TMInterface0'
    print(f'Connecting to {server_name}...')
    run_client(MainClient(), server_name)

if __name__ == '__main__':
    main()
