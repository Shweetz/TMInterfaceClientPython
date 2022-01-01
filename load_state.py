from tminterface.structs import CheckpointData, Event, SimStateData
import struct


def load_state(path: str) -> SimStateData:
    data = SimStateData()
    with open(path, 'rb') as f:
        def read_int():
            return struct.unpack('i', f.read(4))[0]

        def read_event():
            return Event(read_int(), read_int())

        data.version = read_int()
        data.context_mode = read_int()
        data.flags = read_int()
        data.timers = bytearray(f.read(212))
        data.dyna = bytearray(f.read(1424))
        data.scene_mobil = bytearray(f.read(2168))
        data.simulation_wheels = bytearray(f.read(3056))
        data.plug_solid = bytearray(f.read(68))
        data.cmd_buffer_core = bytearray(f.read(264))
        data.player_info = bytearray(f.read(952))
        data.internal_input_state = bytearray(f.read(120))

        data.input_running_event = read_event()
        data.input_finish_event = read_event()
        data.input_accelerate_event = read_event()
        data.input_brake_event = read_event()
        data.input_left_event = read_event()
        data.input_right_event = read_event()
        data.input_steer_event = read_event()
        data.input_gas_event = read_event()

        data.num_respawns = read_int()

        cp_states = []
        num_cp_states = read_int()
        for _ in range(num_cp_states):
            cp_states.append(read_int())

        cp_times = []
        num_cp_times = read_int()
        for _ in range(num_cp_times):
            cp_times.append((read_int(), read_int()))

        data.cp_data = CheckpointData(cp_states, cp_times)

    return data
