from dataclasses import dataclass, field
import math
import operator
import os

from tminterface.commandlist import CommandList, InputCommand, InputType, BOT_INPUT_TYPES
import pygbx
import generate_input_file

from SUtil import ms_to_sec, to_sec

@dataclass
class Split:
    filename: str
    start_cp: int = None
    end_cp: int = None
    remove_fails: bool = True
    ignore_cp: list = field(default_factory=list)
    
    # def update(self, replay: Replay) -> None:
    #     pass

"""
HOW TO USE
- pip install tminterface
- In the directory of the script, you need generate_input_file.py and the relevant replays
- Add ordered Splits to route: the route is the final replay desired route, every split is some continuous part of inputs
- Use "end_cp" to select the CP where to stop grabbing inputs from
- Use "start_cp" to select the CP where to start grabbing inputs from (leave empty to start on the last "press enter" before "end_cp")
- Use "remove_fails" to remove respawns that didn't reach a CP (forces respawn every CP that is not in ignore_cp)
- Use "ignore_cp" to NOT respawn on some CP (rings or CPs that the replay didn't respawn on)
"""

# Set to True to try and automatically find fastest splits
# Set to False if it causes problems (example: you try to combine replays with different routes)
TRY_FASTEST_SPLITS = True

# Extract the raw inputs from the replays into .txt files
WRITE_RAW_INPUTS = False

# If you want "realistic respawn", set a time value in ms to add wait between crossing CP and respawn
WAIT_AFTER_CP_CROSS = 0


route = []
# route.append(Split(filename="Snow_Powder_.c2oo..700306.Replay.Gbx", ignore_cp=[2]))


class RespawnState:
    """Stores the time and inputs pressed during a respawn"""
    def __init__(self):
        self.timestamp = 0
        self.inputs = {}
        for i in range(InputType.UNKNOWN):
            self.inputs[i] = 0

    def update(self, input_type: InputType, state: int) -> None:
        self.inputs[input_type.value] = state


class Replay:
    """Stores cp_times, inputs and commands of a replay"""
    def __init__(self, filename):
        self.cp_times = self.extract_cp_times(filename)
        self.inputs_str = self.extract_inputs(filename)
        self.commands = self.extract_sorted_commands(self.inputs_str)
        self.cp_not_respawned = self.extract_not_respawned(self.cp_times, self.commands)

    def extract_cp_times(self, filename: str) -> list[int]:
        """Extract CP times from a replay with pygbx"""
        g = pygbx.Gbx(filename)
        ghost = g.get_class_by_id(pygbx.GbxType.CTN_GHOST)
        if not ghost:
            print(f"ERROR: no ghost in {filename=}")
            quit()

        # print(len(ghost.cp_times))
        print(f"{len(ghost.cp_times)} CPs: {ghost.cp_times} for {filename}")

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

    def extract_inputs(self, filename: str) -> str:
        """Extract inputs from a replay with dona's script"""
        inputs_list = []
        generate_input_file.process_path(filename, inputs_list.append)

        inputs_str = ""
        for input in inputs_list:
            inputs_str += input
        
        if WRITE_RAW_INPUTS:
            # Write inputs to text file
            if filename.lower().endswith(".replay.gbx"):
                filename_inputs = filename[:-11] + ".txt"
            else:
                filename_inputs = filename + ".txt"

            with open(filename_inputs, "w") as f:
                f.write(inputs_str)

        return inputs_str
        
    def extract_sorted_commands(self, inputs_str: str) -> list[InputCommand]:
        """Transform inputs in sorted commands (free inputs clean up)"""
        cmdlist = CommandList(inputs_str)
        commands = [cmd for cmd in cmdlist.timed_commands if isinstance(cmd, InputCommand)]
        commands.sort(key=operator.attrgetter("timestamp"))

        return commands
        
    def extract_not_respawned(self, cp_times: list[int], commands: list[InputCommand]) -> list[int]:
        """Find which CP weren't respawned, using cp_times and commands"""
        # i+1 because i represents cp number (start is not a cp)
        not_respawned = [i+1 for i in range(len(cp_times) - 1)]

        # Check all respawn commands
        for command in commands:
            if command.input_type == InputType.RESPAWN and command.state:
                # print(command.timestamp)
                # Find out which which cp was crossed last before respawn
                # WARNING WITH NON-RESPAWNABLE CPS (RINGS)
                for cp in range(1, len(cp_times)):
                    # print(f"{cp=}")
                    if cp_times[cp-1] <= command.timestamp < cp_times[cp]:
                        if cp in not_respawned:
                            not_respawned.remove(cp)
                        break
        
        return not_respawned


class Subroute:
    # todo
    pass


def find_start_end_time(start_cp: int, end_cp: int, cp_times: list[int], commands: CommandList) -> list[int, int]:
    """Find start and end times from which to copy inputs from the replay (before delaying them)"""
    # Find end_time
    # end_cp None means until the end (finish cp)
    if end_cp is None:
        end_cp = len(cp_times)

    # CP0 is 0 but not in the list, so there's a - 1
    end_time = cp_times[end_cp - 1]

    # Find start_time but if start_cp, use time since start_cp and not last respawn
    # if start_cp is None:
    #     # Find previous press enter before end_time
    #     end_index = find_command_index(commands, end_time, InputType.RESPAWN, 1)
    #     start_index = find_previous_index(commands, end_index, InputType.RESPAWN, 1)
    #     if start_index is None:
    #         start_time = 0
    #     else:
    #         start_time = commands[start_index].timestamp

    # elif start_cp == 0:
    #     start_time = 0
    
    # else:
    #     start_time = cp_times[start_cp - 1]
    
    # Find start_time
    if start_cp is not None and start_cp == 0:
        start_time = 0
    else:
        # Find previous press enter before end_time
        end_index = find_command_index(commands, end_time, InputType.RESPAWN, 1)
        start_index = find_previous_index(commands, end_index, InputType.RESPAWN, 1)
        if start_index is None:
            start_time = 0
        else:
            start_time = commands[start_index].timestamp

    return start_time, end_time

def create_state(timestamp: int, commands: list[InputCommand]) -> RespawnState:
    """Save the inputs at a precise tick in a replay"""
    state = RespawnState()
    state.timestamp = timestamp

    for command in commands:
        # For every command in the file, update the inputs pressed at the moment
        if (command.timestamp < timestamp):
            state.update(command.input_type, command.state)
        else:
            # Save the state inputs when a respawn is performed
            break
    
    return state

def compute_commands_transition(new_respawn_state, last_respawn_state) -> list[InputCommand]:
    """Find input differences between end of last split to start of new split and return commands to fix transition"""
    commands = []

    timestamp = new_respawn_state.timestamp

    for i in range(InputType.UNKNOWN):
        if new_respawn_state.inputs[i] != last_respawn_state.inputs[i]:
            input_type = InputType(i)
            state = new_respawn_state.inputs[i]

            commands.append(InputCommand(timestamp, input_type, state))

    return commands

def compute_commands_split(commands: list[InputCommand], start_time: int, end_time: int) -> list[InputCommand]:
    """Get commands between start_time and end_time (respawn is at start_time, if any), with deepcopy"""
    commands_split = []

    deep_copy = True

    if deep_copy:
        for command in commands:
            if start_time <= command.timestamp < end_time:
                commands_split.append(InputCommand(command.timestamp, command.input_type, command.state))
    else:
        commands_split = [command for command in commands if start_time <= command.timestamp < end_time]

    return commands_split

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
            # print(f"find_command_index: No command found at {end_time=} (can be because non-instant respawn)")
            return index_min
    
    # Find the enter/respawn command at this time
    if command.input_type != input_type or command.state != state:
        # Find the first command with end_time
        while commands[index-1].timestamp == end_time:
            index -= 1
        command = commands[index]

        # Go through commands until finding it or higher end_time
        while command.timestamp == end_time and command.input_type != input_type:
            index += 1
            if index >= len(commands):
                return None
            command = commands[index]

        if command.timestamp > end_time:
            # print(f"find_command_index: No command found at {end_time=} (can be because non-instant respawn)")
            return index
    
    # Index max means grab inputs until the end
    # if index == len(commands) - 1:
    #     return index

    # Final check
    if command.timestamp != end_time or command.input_type != input_type:
        print(f"ERROR in find_command_index: {command.timestamp=} != {end_time=} or {command.input_type=} != {input_type=}")
    
    return index

def find_previous_index(commands: CommandList, end_index: int, input_type: InputType, state: int) -> int:
    """
    In a CommandList, find the index of the previous command with the specified InputType.
    Example: find_command_index(commands, 1000, InputType.RESPAWN) -> 45
    """
    if end_index is None:
        index = len(commands) - 1
    else:
        index = end_index - 1
    command = commands[index]
    
    # Go back one command at a time until finding the previous
    while command.input_type != input_type or command.state != state:
        index -= 1
        if index < 0:
            return None
        command = commands[index]

    # Index 0 means grab inputs from the start
    # if index == 0:
    #     return index

    # Final check
    if command.input_type != input_type:
        print(f"ERROR in find_previous_index: {command.input_type=} != {input_type=}")
    
    return index

def to_script(commands: list) -> str:
    """Transform a list of commands to a string"""
    result_string = ""
    for command in commands:
        result_string += command.to_script() + "\n"
    
    result_string = to_sec(result_string)

    return result_string

def try_subroute(subroute: list[int], best_splits: dict[(int, int): Split]) -> int:
    subroute_time = 0

    for i in range(len(subroute)-1):
        key = (subroute[i],subroute[i+1])
        if key not in best_splits:
            # print(f"no {key=}")
            return -1
        
        subroute_time += best_splits[key].duration

    return subroute_time


def main():
    assembled_file = os.path.expanduser('~/Documents') + "/TMInterface/Scripts/" + "inputs_assemble.txt"

    # If no route defined, add all replays in the directory with default parameters
    if not route:
        for file in os.listdir("."):
            if file.lower().endswith(".replay.gbx"):
                route.append(Split(filename=file))

    # Create Splits from Replays and expand route to remove fails if needed
    print("")
    print("Reading replay(s)...")
    replays = {}
    route_expanded = []
    global_cp_not_respawned = []
    for split in route:
        if not split.filename:
            print(f"ERROR: no filename specified")
            continue
        if not os.path.isfile(split.filename):
            print(f"ERROR: {split.filename} does not exist")
            continue

        # Read and store replay info
        if split.filename not in replays:
            replays[split.filename] = Replay(split.filename)
            print(f"CPs not respawned: {replays[split.filename].cp_not_respawned}")

        # Remove fails
        if split.remove_fails:
            split_start_cp = split.start_cp if split.start_cp is not None else 0
            split_end_cp = split.end_cp if split.end_cp is not None else len(replays[split.filename].cp_times)

            last_respawned_cp = 0

            # Create subsplits from replay
            for i in range(split_start_cp + 1, split_end_cp + 1):
                subsplit = Split(filename=split.filename, start_cp=last_respawned_cp, end_cp=i)
                # subsplit.update(replay)
                route_expanded.append(subsplit)

                if i in split.ignore_cp or i in replays[split.filename].cp_not_respawned:
                    # At least 1 replay didn't respawn
                    if i not in global_cp_not_respawned:
                        global_cp_not_respawned.append(i)
                else:
                    last_respawned_cp = i

        else:
            # split.update(replay)
            route_expanded.append(split)

    # Find out each split time
    print("")
    print("Checking split times...")
    for split in route_expanded:
        replay = replays[split.filename]

        # Find start_time and end_time
        split.start_time, split.end_time = find_start_end_time(split.start_cp, split.end_cp, replay.cp_times, replay.commands)
        split.duration = split.end_time - split.start_time

        # Print split info
        if split.start_cp is None:
            cp_str = split.end_cp
        else:
            cp_str = str(split.start_cp) + "-" + str(split.end_cp)

        print(f"{split.filename} with CP {cp_str}, time={ms_to_sec(split.duration)}")

    # Find out the fastest splits
    if TRY_FASTEST_SPLITS and len(route) > 1:
        global_cp_not_respawned.sort()
        print("")
        print(f"{global_cp_not_respawned=}")
        
        print("")
        print("Finding fastest splits...")
        nb_cp_total = route_expanded[-1].end_cp
        route_timed = []

        best_splits = {}
        for curr_cp in range(1, nb_cp_total + 1):
            for split in route_expanded:
                key = (split.start_cp, split.end_cp)
                if key not in best_splits or split.duration < best_splits[key].duration:
                    best_splits[key] = split
        
        last_respawned_cp = 0
        best_subroute = []
        best_subroute_time = -1
        for curr_cp in range(1, nb_cp_total + 1):

            if curr_cp not in global_cp_not_respawned:
                # All replays respawned this CP: join splits

                cp_skipped = curr_cp - last_respawned_cp - 1
                nb_subroutes_poss = pow(2, cp_skipped)

                # print(f"CP{last_respawned_cp}-CP{curr_cp}, {nb_subroutes_poss=}")

                # Find best subroute
                for subroute_int in range(nb_subroutes_poss):
                    subroute_bin = "{0:b}".format(subroute_int).zfill(cp_skipped)

                    subroute = [last_respawned_cp]
                    for i, char in enumerate(subroute_bin):
                        if char == "1":
                            subroute.append(last_respawned_cp + 1 + i)
                    subroute.append(curr_cp)

                    subroute_time = try_subroute(subroute, best_splits)

                    # Uncomment me for algo info
                    # print(f"try_subroute {subroute_bin} => {subroute}: {subroute_time}")

                    if subroute_time != -1:
                        if best_subroute_time == -1 or subroute_time < best_subroute_time:
                            best_subroute = subroute
                            best_subroute_time = subroute_time

                # Append best splits in route_timed
                for i in range(len(best_subroute)-1):
                    best_split = best_splits[(best_subroute[i],best_subroute[i+1])]                 
                    route_timed.append(best_split)

                    # Print best_split info
                    if best_split.start_cp is None:
                        cp_str = best_split.end_cp
                    else:
                        cp_str = str(best_split.start_cp) + "-" + str(best_split.end_cp)
                        
                    print(f"CP {cp_str}: time={ms_to_sec(best_split.duration)} for {best_split.filename}")

                last_respawned_cp = curr_cp
                best_subroute = []
                best_subroute_time = -1

    else:
        route_timed = route_expanded

    # Execute the splits
    print("")
    print("Assembling splits...")
    last_respawn_state = RespawnState()
    last_end_time = 0
    assembled_inputs = ""
    for split in route_timed:
        replay = replays[split.filename]

        # Transition state: replace inputs during last respawn with inputs new respawn
        new_respawn_state = create_state(split.start_time, replay.commands)
        commands_transition = compute_commands_transition(new_respawn_state, last_respawn_state)
        last_respawn_state = create_state(split.end_time, replay.commands)
        
        # Get commands between start_time and end_time
        commands_split = compute_commands_split(replay.commands, split.start_time, split.end_time)

        # Combine transition state + new commands
        new_commands = commands_transition + commands_split

        # Delay commands
        delay = last_end_time - split.start_time
        # print(f"{split.start_time=}")
        # print(f"{split.end_time=}")
        # print(f"{delay=}")
        for i in range(len(new_commands)):
            new_commands[i].timestamp += delay

        last_end_time = last_end_time - split.start_time + split.end_time

        # Add a wait after crossing CP
        wait = WAIT_AFTER_CP_CROSS
        if (wait > 0):
            # new_commands.append(InputCommand(last_end_time, InputType.RESPAWN, True)) # add respawn on CP collect
            last_end_time += wait

        # Print inputs
        assembled_inputs += to_script(new_commands)

    with open(assembled_file, "w") as f:
        f.write(assembled_inputs)

    print(f"Total time = {ms_to_sec(last_end_time)} for the assembled inputs written in {assembled_file}")

if __name__ == "__main__":
    # Change current directory from executing directory to script directory
    if os.path.dirname(__file__) != os.getcwd():
        print(f"Changing current directory from executing directory to script directory")
        print(f"{os.getcwd()} => {os.path.dirname(__file__)}")
        os.chdir(os.path.dirname(__file__))

    main()
