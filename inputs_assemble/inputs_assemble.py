from dataclasses import dataclass
import math
import operator
import os
import sys
import time

from tminterface.commandlist import CommandList, InputCommand, InputType, BOT_INPUT_TYPES

from SUtil import sec_to_ms

@dataclass
class Split:
    filename: str
    selected_time: str

"""
HOW TO USE
- Place the inputs as txt files in the same directory as this script
- Add Splits to route: the route is the final replay desired route, every split is some continuous part of inputs
- Use "selected_time" to select when to start and stop grabbing inputs from the text file
    * selected_time="cp_times"   will make 1 split/CP reached
        For this, add in the inputs file the TMI logs with CP timings of the selected CPs
        To get TMI logs with CP crossed, check Settings > Misc > Log Information About Simulation, then play or validate the run 
        Then use "copy_logs" to copy the info, paste it in the file and clean the logs by removing everything before CP1
    * selected_time="full"       will start at 0 and end at the end of the replay file
    * selected_time="2.20-15.15" will start at 2.20 and end at 15.15
    * selected_time="15.15"      will end at 15.15 and start at whichever is the previous respawn
    * selected_time="0"          will start at 0 and end at the next respawn (this only happens for value "0")
    * selected_time=""           will depend on how many "press enter" are in the inputs file
        + 1 "press enter" will grab from the "press enter" to the end
        + 2 "press enter" will grab what is between the 2
        + any other number will print an error
"""

"inputs_assemble_info.txt"
route = []
route.append(Split(filename="inputs.txt", selected_time="cp_times"))

class RespawnState:
    """Stores the time and inputs pressed during a respawn"""
    # filename = ""
    # input_accelerate = 0
    # input_brake = 0
    # input_left = 0
    # input_right = 0
    # input_steer = 0
    # input_gas_event = 0

    def __init__(self):
        self.timestamp = 0
        self.inputs = {}
        # self.filename = filename
        for i in range(InputType.UNKNOWN):
            self.inputs[i] = 0

    # def copy(self):
    #     respawn_state = RespawnState()
    #     respawn_state.timestamp = self.timestamp
    #     for i in range(InputType.UNKNOWN):
    #         respawn_state.inputs[i] = self.inputs[i]
    #     return respawn_state

    def update(self, input_type: InputType, state: int) -> None:
        # print(input_type.value)
        # print(state)
        # time.sleep(1)
        self.inputs[input_type.value] = state

def extract_sorted_timed_commands(filename: str) -> CommandList:
    with open(filename, "r") as f:
        inputs_str = f.read()

    # print(inputs_str)

    # Transform inputs in sorted commands (free inputs clean up)
    cmdlist = CommandList(inputs_str)
    commands = [cmd for cmd in cmdlist.timed_commands if isinstance(cmd, InputCommand)]
    commands.sort(key=operator.attrgetter("timestamp"))

    return commands

def find_end_times_cp(filename: str) -> list[int]: 
    """Find CP times from the inputs text file containing TMI's logs"""  
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

def find_start_end_time(selected_time: str, commands: CommandList) -> list[int, int]:
    
    if selected_time == "full":
        start_time = 0
        end_time   = commands[-1].timestamp

    elif "-" in selected_time:
        start_time = int(sec_to_ms(selected_time.split(".")[0]))
        end_time   = int(sec_to_ms(selected_time.split(".")[1]))

    elif selected_time == "0":
        start_time = 0
        end_time   = 0 # TODO first press enter

    elif selected_time:
        end_time   = int(sec_to_ms(selected_time))

        # find previous press enter before end_time
        end_index = find_command_index(commands, end_time, InputType.RESPAWN, 1)
        start_index = find_previous_index(commands, end_index, InputType.RESPAWN, 1)
        start_time = commands[start_index].timestamp

    else:
        # find end_time first
        nb_press_enter = 0
        for command in commands:
            # count nb press enter
            if command.input_type == InputType.RESPAWN and command.state == 1:
                nb_press_enter += 1
                # print(f"press enter found at {command.timestamp}")
        
        if nb_press_enter == 1:
            # last command
            end_time = commands[-1].timestamp
            print(f"WARNING only 1 press enter found, cutting on last InputCommand")

        elif nb_press_enter == 2:
            # last press enter
            end_index = find_previous_index(commands, len(commands), InputType.RESPAWN, 1)
            end_time = commands[end_index].timestamp

        else:
            print(f"ERROR {nb_press_enter=}")
            sys.exit()

        #find previous press enter before end_time
        end_index = find_command_index(commands, end_time, InputType.RESPAWN, 1)
        start_index = find_previous_index(commands, end_index, InputType.RESPAWN, 1)
        start_time = commands[start_index].timestamp

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
    # assembled_file = os.path.expanduser('~/Documents') + "/TMInterface/States/" + "work2.txt"
    assembled_inputs = ""
    # inputs_files_read = []
    last_end_time = 0
    last_respawn_state = RespawnState()
    # last_respawn_state.timestamp = 5
    # print(new_respawn_state.timestamp)

    # Remove fails (will force respawn every CP)
    if route[0].selected_time == "cp_times":
        # add remove_fails file content in the inputs file
        # read route[0].remove_fails to find all end_time (look for "Checkpoint" and "Race" lines)
        list_end_times = find_end_times_cp(route[0].filename)
        # add splits with filename=route[0].filename and selected_time=end_time
        for end_time in list_end_times:
            route.append(Split(filename=route[0].filename, selected_time=end_time))
        # remove this split
        route.pop(0)

    # Every line in lines_info shall be formatted like this:
    # filename.txt [start_time] end_time
    # Note: start_time is optional, if undefined it will be the previous press enter
    for split in route:
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
        if not split.selected_time:
            print(f"ERROR: no selected_time specified")
            continue
        if not os.path.isfile(split.filename):
            print(f"ERROR: {split.filename} does not exist")
            continue
        
        # Extract commands
        commands = extract_sorted_timed_commands(split.filename)

        # Find start_time and end_time
        start_time, end_time = find_start_end_time(split.selected_time, commands)
        print(f"{split.filename} between {start_time} and {end_time}")

        # Transition state: replace inputs during last respawn with inputs new respawn
        new_respawn_state = create_state(start_time, commands)
        commands_transition = compute_commands_transition(new_respawn_state, last_respawn_state)
        last_respawn_state = create_state(end_time, commands)
        
        # Get commands between start_time and end_time
        commands_split = [command for command in commands if start_time <= command.timestamp < end_time]

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


if __name__ == "__main__":
    main()
