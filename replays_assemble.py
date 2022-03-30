from dataclasses import dataclass, field
from fileinput import filename
import math
import operator
import os
import sys
import time

from tminterface.commandlist import CommandList, InputCommand, InputType, BOT_INPUT_TYPES
import pygbx
import generate_input_file

@dataclass
class Split:
    filename: str
    start_cp: int = None
    end_cp: int = None
    remove_fails: bool = False
    ignore_cp: list = field(default_factory=list)

"""
HOW TO USE
- pip install pygbx
- In the directory of the script, you need generate_input_file.py and the relevant replays
- Add ordered Splits to route: the route is the final replay desired route, every split is some continuous part of inputs
- Use "end_cp" to select the CP where to stop grabbing inputs from
- Use "start_cp" to select the CP where to start grabbing inputs from (leave empty to start on the last "press enter" before "end_cp")
- Use "remove_fails" to remove respawns that didn't reach a CP (forces respawn every CP that is not in ignore_cp)
- Use "ignore_cp" to NOT respawn on some CP (rings or CPs that the replay didn't respawn on)
"""

route = []
# route.append(Split(filename="Ţ.A.L.O.S_5days(07'34''85).Replay.Gbx"))
route.append(Split(filename="T.A.L.O.S_KMAIL COLINS(284'58''78).Replay.Gbx", remove_fails=True, ignore_cp=[12, 20]))
# route.append(Split(filename="ASUS2_T.A.L.O.S.Replay.gbx", start_cp=0, end_cp=0))

class RespawnState:
    """Stores the time and inputs pressed during a respawn"""
    def __init__(self):
        self.timestamp = 0
        self.inputs = {}
        # self.filename = filename
        for i in range(InputType.UNKNOWN):
            self.inputs[i] = 0

    def update(self, input_type: InputType, state: int) -> None:
        self.inputs[input_type.value] = state


class Replay:
    """Stores cp_times, inputs and commands of a replay"""
    def __init__(self, filename):
        self.cp_times = extract_cp_times(filename)
        self.inputs_str = extract_inputs(filename)
        self.commands = extract_sorted_commands(self.inputs_str)

def extract_cp_times(filename: str) -> list[int]:
    g = pygbx.Gbx(filename)
    ghost = g.get_class_by_id(pygbx.GbxType.CTN_GHOST)
    if not ghost:
        print(f"ERROR: no ghost in {filename=}")
        quit()

    # print(len(ghost.cp_times))
    # print(ghost.cp_times)

    # Check car position after every CP to guess where rings are and remove them
    # does not work for exported for validation replays
    # if not ghost.records:
    #     # exported for validation replay
    #     pass
    # else:
    #     cp_times_no_rings = []
    #     for cp_time in ghost.cp_times:
    #         index_after_cp = math.floor(cp_time / 100) + 1
    #         x, y, z = ghost.records[index_after_cp].position.as_array()
    #         print(x, y, z)
    #         # TODO

    return ghost.cp_times

def extract_inputs(filename: str) -> str:
    inputs_list = []
    generate_input_file.process_path(filename, inputs_list.append)

    inputs_str = ""
    for input in inputs_list:
        inputs_str += input + "\n"
    
    return inputs_str
    
def extract_sorted_commands(inputs_str: str) -> CommandList:
    # Transform inputs in sorted commands (free inputs clean up)
    cmdlist = CommandList(inputs_str)
    commands = [cmd for cmd in cmdlist.timed_commands if isinstance(cmd, InputCommand)]
    commands.sort(key=operator.attrgetter("timestamp"))

    return commands

def find_end_times_cp(filename: str) -> list[int]:
    end_times_cp = []

    with open(filename, "r") as f:
        lines = f.readlines()
    
    for line in lines:
        if "[Simulation] Checkpoint" in line:
            splits = line.split(" ")
            end_time = splits[-2][:-1].rstrip()
            end_times_cp.append(end_time)
            print(f"{end_time=}")
            # cp_number = splits[-1].split("/")[0]
            
        if "[Simulation] Race" in line:
            splits = line.split(" ")
            end_time = splits[-1].rstrip()
            end_times_cp.append(end_time)
            print(f"{end_time=}")

    return end_times_cp

def find_start_end_time(start_cp: int, end_cp: int, cp_times: list[int], commands: CommandList) -> list[int, int]:
    
    # CP0 is 0 but not in the list, so there's a - 1
    end_time = cp_times[end_cp - 1]

    # Find start_time
    if start_cp is None:
        # Find previous press enter before end_time
        end_index = find_command_index(commands, end_time, InputType.RESPAWN, 1)
        start_index = find_previous_index(commands, end_index, InputType.RESPAWN, 1)
        start_time = commands[start_index].timestamp

    elif start_cp == 0:
        start_time = 0
    
    else:
        start_time = cp_times[start_cp - 1]

    return start_time, end_time

def create_state(timestamp: int, commands: list[InputCommand]) -> RespawnState:
    state = RespawnState()
    state.timestamp = timestamp

    for command in commands:
        # For every command in the file, update the inputs pressed at the moment
        if (command.timestamp < timestamp):
            state.update(command.input_type, command.state)
            # print(f"{command.input_type=}, {command.state=}")
        else:
            # Save the state inputs when a respawn is performed
            # print(f"Adding new_respawn_state at {command.timestamp}, steer = {new_respawn_state.inputs[6]}")
            break
    
    return state

def compute_commands_transition(new_respawn_state, last_respawn_state):
    commands = []
    # new_respawn_state = get_respawn_state(commands, start_time, new_respawn_state)

    timestamp = new_respawn_state.timestamp

    # print(f"{last_respawn_state.inputs[0]=}")
    # print(f"{start_time} {last_respawn_state.inputs[0]} {new_respawn_state.inputs[0]}")
    for i in range(InputType.UNKNOWN):
        # print("")
        # print(f"{start_time} {i} {last_respawn_state.inputs[i]} {new_respawn_state.inputs[i]}")
        # print("")

        if new_respawn_state.inputs[i] != last_respawn_state.inputs[i]:
            inputs_type = InputType(i)
            state = new_respawn_state.inputs[i]
            # command = 
            commands.append(InputCommand(timestamp, inputs_type, state))
            # print("")
            # print(f"{start_time} {i} {last_respawn_state.inputs[i]} {new_respawn_state.inputs[i]}")
            # print("")

    return commands

def find_command_index(commands: CommandList, end_time: int, input_type: InputType, state: int) -> int:
    """
    In a CommandList, find the index of the command at end_time with the specified InputType.
    Example: find_command_index(commands, 1000, InputType.RESPAWN) -> 45
    """
    # Use dichotomy to find the command
    index_min = 0
    index_max = len(commands) - 1

    command = commands[0]
    
    # Find a command with the same time (can be another command)
    while command.timestamp != end_time:
        index = math.floor((index_min+index_max) / 2)
        command = commands[index]

        if command.timestamp < end_time:
            index_min = index + 1
        elif command.timestamp > end_time:
            index_max = index - 1

        if index_min > index_max:
            print(f"find_command_index: WARNING No command found at {end_time=} (can be because non-instant respawn)")
            return index_min
    
    # Find the enter/respawn command at this time
    if command.input_type != input_type or command.state != state:
        # Find the first command with end_time
        while commands[index-1].timestamp == end_time:
            index -= 1
        command = commands[index]

        # Go through commands until finding it or higher end_time
        while command.timestamp == end_time and command.input_type != input_type and index < len(commands) - 1:
            index += 1
            command = commands[index]
    
    # print(f"find_command_index: {index=}, {command.timestamp=}")
    # Index max means grab inputs until the start
    if index == len(commands) - 1:
        return index

    # Final check
    if command.timestamp != end_time or command.input_type != input_type:
        # print(index)
        # print(len(commands))
        print(f"find_command_index: ERROR {command.timestamp=} != {end_time=} or {command.input_type=} != {input_type=}")
        raise
    
    # print(f"find_command_index: {index=}, {command.timestamp=}")
    return index

def find_previous_index(commands: CommandList, end_index: int, input_type: InputType, state: int) -> int:
    """
    In a CommandList, find the index of the previous command with the specified InputType.
    Example: find_command_index(commands, 1000, InputType.RESPAWN) -> 45
    """
    index = end_index - 1
    command = commands[index]
    
    # Go back one command at a time until finding the previous
    while (command.input_type != input_type or command.state != state) and index > 0:
        index -= 1
        command = commands[index]

    # print(f"find_previous_index: {index=}, {command.timestamp=}")
    # Index 0 means grab inputs from the start
    if index == 0:
        return index

    # Final check (index != 0)
    if command.input_type != input_type:
        print(f"find_previous_index ERROR: {command.input_type=} != {input_type=}")
        raise
    
    return index

def to_script(commands: list) -> str:
    """Transform a list of commands to a string"""
    result_string = ""
    for command in commands:
        result_string += command.to_script() + "\n"
    return result_string

def main():
    # with open("inputs_assemble_info.txt", "r") as f:
    #     lines_info = f.readlines()

    assembled_file = "inputs_assemble.txt"
    assembled_file = os.path.expanduser('~/Documents') + "/TMInterface/Scripts/" + "inputs_assemble.txt"
    assembled_inputs = ""
    # inputs_files_read = []
    last_end_time = 0
    last_respawn_state = RespawnState()
    replays = {}

    # Remove fails (will force respawn every CP)
    route_expanded = []
    for split in route:
        if split.filename not in replays:
            replays[split.filename] = Replay(split.filename)

        if split.remove_fails:
            # Every CP is a new split of 1 CP (can't handle rings here :/ )
            split_start_cp = split.start_cp if split.start_cp is not None else 0
            split_end_cp = split.end_cp if split.end_cp is not None else len(replays[split.filename].cp_times)

            # +1 because i represents end_cp and not start_cp
            for i in range(split_start_cp + 1, split_end_cp + 1):
                if i in split.ignore_cp:
                    continue

                route_expanded.append(Split(filename=split.filename, end_cp=i))

            # Remove this fake split
            # route.pop(0)

        else:
            route_expanded.append(split)

    # Every line in lines_info shall be formatted like this:
    # filename.txt [start_time] end_time
    # Note: start_time is optional, if undefined it will be the previous press enter
    for split in route_expanded:
        # print("")
        # line = line.replace("\n", "")
        # if not line or line.startswith("#"):
        #     continue
        
        # splits = line.split(" ")
        # filename = splits[0]
        # start_time = None
        # end_time = None

        # if len(splits) == 2:
        #     end_time = int(sec_to_ms(splits[1]))

        # elif len(splits) == 3:
        #     start_time = int(sec_to_ms(splits[1]))
        #     end_time = int(sec_to_ms(splits[2]))
        #     # print(f"{start_time=} {end_time=}")
        # elif len(splits) > 3:
        #     print(f"{len(splits)=}: {line}")
        #     continue

        if not split.filename:
            print(f"ERROR: no filename specified")
            continue
        # if not split.selected_time:
        #     print(f"ERROR: no selected_time specified")
        #     continue
        if not os.path.isfile(split.filename):
            print(f"ERROR: {split.filename} does not exist")
            continue
        
        print("")
        print(f"split: {split.filename} {split.start_cp}-{split.end_cp}")
        
        replay = replays[split.filename]

        # Find start_time and end_time
        if split.end_cp is None:
            # end_cp None means until the end (finish cp)
            split.end_cp = len(replay.cp_times)

        start_time, end_time = find_start_end_time(split.start_cp, split.end_cp, replay.cp_times, replay.commands)
        print(f"{split.filename} between {start_time} and {end_time}")

        # Transition state: replace inputs during last respawn with inputs new respawn
        new_respawn_state = create_state(start_time, replay.commands)
        commands_transition = compute_commands_transition(new_respawn_state, last_respawn_state)
        last_respawn_state = create_state(end_time, replay.commands)
        
        # Get commands between start_time and end_time
        commands_split = [command for command in replay.commands if start_time <= command.timestamp < end_time]

        # Combine transition state + new commands
        new_commands = commands_transition + commands_split

        # Delay commands
        delay = last_end_time - start_time
        # print(delay)
        # print(len(new_commands))
        # print(new_commands[0].timestamp)
        for i in range(len(new_commands)):
            new_commands[i].timestamp += delay

        # print(new_commands[0].timestamp)
        last_end_time = last_end_time - start_time + end_time

        # print inputs
        assembled_inputs += to_script(new_commands)


    with open(assembled_file, "w") as f:
        f.write(assembled_inputs)

    print(f"Wrote to {assembled_file}")

if __name__ == "__main__":
    main()
