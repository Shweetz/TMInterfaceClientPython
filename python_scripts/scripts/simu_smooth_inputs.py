import math
import os
import sys

from tminterface.interface import TMInterface
from tminterface.client import Client, run_client
from tminterface.constants import ANALOG_STEER_NAME, BINARY_ACCELERATE_NAME, BINARY_BRAKE_NAME, BINARY_LEFT_NAME, BINARY_RIGHT_NAME, BINARY_RESPAWN_NAME, BINARY_RACE_FINISH_NAME
from tminterface.commandlist import CommandList, InputCommand, InputType

INPUTS_NAME = "simplified_inputs.txt"
CLEAR_INPUTS = True

class InputState():
    """Holds currently pressed inputs"""
    def __init__(self):
        self.left  = False
        self.right = False
        self.down  = False
        self.up    = False
        self.steer = 0
        self.prev_steer = 0

class MainClient(Client):
    def on_registered(self, iface: TMInterface) -> None:
        print(f'Registered to {iface.server_name}')
        iface.execute_command('set controller none')

    def on_simulation_begin(self, iface):
        iface.remove_state_validation()
        if CLEAR_INPUTS:
            # Empty inputs file to not use previously found ones
            open(os.path.expanduser('~/Documents') + "/TMInterface/Scripts/" + INPUTS_NAME, "w").close()

        self.inputs_phase = "writing"
        self.state_start = None
        self.tick_info = {}
        self.turning_rate = 0
        self.prev_turn = 0
        self.prev_steer = 0
        self.inputs = ""
        self.begin_buffer = None
        self.pressed = InputState()
        self.wrong = False
        self.begin_buffer = iface.get_event_buffer()
        self.lowest_time = self.begin_buffer.events_duration

    def on_simulation_step(self, iface: TMInterface, _time: int):
        if self.inputs_phase == "writing":
            if _time == -10:
                self.state_start = iface.get_simulation_state()

            state = iface.get_simulation_state()

            if _time < self.lowest_time:
                self.tick_info[_time] = {}
                self.tick_info[_time]["position"] = state.position
                self.tick_info[_time]["velocity"] = state.velocity
                self.tick_info[_time]["yaw_pitch_roll"] = state.yaw_pitch_roll
                self.tick_info[_time]["wheels"] = nb_wheels_on_ground(state)

            if _time > 0 and _time < self.lowest_time:
                self.compute_inputs(state, _time)

            if _time == self.lowest_time - 10:
                self.save_inputs_to_file()
                self.load_inputs_from_file()
                iface.set_event_buffer(self.begin_buffer)
                iface.rewind_to_state(self.state_start)
                self.inputs_phase = "testing"

        elif self.inputs_phase == "testing":
            if _time > 0 and _time < self.lowest_time:
                if iface.get_simulation_state().position != self.tick_info[_time]["position"] or \
                   iface.get_simulation_state().velocity != self.tick_info[_time]["velocity"] or \
                   iface.get_simulation_state().yaw_pitch_roll != self.tick_info[_time]["yaw_pitch_roll"]:
                    if not self.wrong:
                        self.wrong = True
                        print(f"Position mismatch at {_time=}")
            
            if _time == self.lowest_time and not self.wrong:
                print(f"Positions match ({_time=})")


    def compute_inputs(self, state, _time):
        self.turning_rate = state.scene_mobil.turning_rate * 65536

        if self.tick_info[_time]["wheels"] >= 3:
            if self.turning_rate > self.prev_turn: self.turning_rate = math.ceil(self.turning_rate)
            if self.turning_rate < self.prev_turn: self.turning_rate = math.floor(self.turning_rate)
            
            if self.turning_rate != self.pressed.steer: 
                self.inputs += f"{(_time-20)/1000:.2f} steer {self.turning_rate} # ground={self.tick_info[_time]['wheels']}, t=\n"
            self.pressed.steer = self.turning_rate

        else:
            if self.prev_steer != self.pressed.steer: 
                self.inputs += f"{(_time-20)/1000:.2f} steer {self.prev_steer}\n"
            self.pressed.steer = self.prev_steer
                
        self.prev_steer = state.input_steer
        self.prev_turn = self.turning_rate

        if state.input_accelerate and not self.pressed.up: self.inputs += f"{(_time-10)/1000:.2f} press up\n"
        if not state.input_accelerate and self.pressed.up: self.inputs += f"{(_time-10)/1000:.2f} rel up\n"
        self.pressed.up    = state.input_accelerate

        if state.input_brake and not self.pressed.down:    self.inputs += f"{(_time-10)/1000:.2f} press down\n"
        if not state.input_brake and self.pressed.down:    self.inputs += f"{(_time-10)/1000:.2f} rel down\n"
        self.pressed.down  = state.input_brake

    def save_inputs_to_file(self):
        res_file = os.path.join(os.path.expanduser('~'), "Documents", "TMInterface", "Scripts", INPUTS_NAME)
        with open(res_file, "w") as f:
            f.write(self.inputs)

    def load_inputs_from_file(self):
        """Load a inputs to bruteforce from a file instead of a replay"""
        print(f"Loading inputs from {INPUTS_NAME}")
        
        self.begin_buffer.clear()

        inputs_file = os.path.join(os.path.expanduser('~'), "Documents", "TMInterface", "Scripts", INPUTS_NAME)
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

            self.begin_buffer.add(command.timestamp, command.input, command.state)

def nb_wheels_on_ground(state):
    number = 0
    for wheel in state.simulation_wheels:
        if wheel.real_time_state.has_ground_contact:
            number += 1

    return number


def main():
    server_name = f'TMInterface{sys.argv[1]}' if len(sys.argv) > 1 else 'TMInterface0'
    print(f'Connecting to {server_name}...')
    run_client(MainClient(), server_name)

if __name__ == '__main__':
    main()
