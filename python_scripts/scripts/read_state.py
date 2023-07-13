from bytefield import *
from tminterface.structs import CachedInput, HmsDynaStruct, SceneVehicleCar, SimulationWheel, PlayerInfoStruct, SimStateData


class InputEvent(ByteStruct):
    time        = IntegerField()
    input_data  = IntegerField()


class CheckpointTime(ByteStruct):
    time            = IntegerField()
    stunts_score    = IntegerField()


class CheckpointData(ByteStruct):
    cp_states_length    = IntegerField()
    cp_states           = ArrayField(shape=None, elem_field_type=BooleanField)
    cp_times_length     = IntegerField()
    cp_times            = ArrayField(shape=None, elem_field_type=CheckpointTime)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.resize(CheckpointData.cp_states_field, self.cp_states_length)
        self.resize(CheckpointData.cp_times_field, self.cp_times_length)


class PhysicalObject(ByteStruct):
    mass                                    = FloatField()
    inverse_principial_moments_of_inertia   = ArrayField((3, 3), FloatField)
    center_of_mass                          = ArrayField(3, FloatField, offset=56)


class ActionIndices(ByteStruct):
    race_is_running_id  = IntegerField()
    finish_line_id      = IntegerField()
    accelerate_id       = IntegerField()
    brake_id            = IntegerField()
    steer_left_id       = IntegerField()
    steer_right_id      = IntegerField()
    steer_id            = IntegerField()
    gas_id              = IntegerField()
    respawn_id          = IntegerField()
    horn_id             = IntegerField()


class ChunkSaveStateInputEvents(ByteStruct):
    input_running_state     = StructField(InputEvent, instance_with_parent=False)
    input_finish_state      = StructField(InputEvent, instance_with_parent=False)
    input_accelerate_state  = StructField(InputEvent, instance_with_parent=False)
    input_brake_state       = StructField(InputEvent, instance_with_parent=False)
    input_left_state        = StructField(InputEvent, instance_with_parent=False)
    input_right_state       = StructField(InputEvent, instance_with_parent=False)
    input_steer_state       = StructField(InputEvent, instance_with_parent=False)
    input_gas_state         = StructField(InputEvent, instance_with_parent=False)
    action_indices          = StructField(ActionIndices, instance_with_parent=False)
    input_events_count      = IntegerField()
    input_events            = ArrayField(None, InputEvent)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.resize(ChunkSaveStateInputEvents.input_events_field, self.input_events_count)


class ChunkSaveStateRegion(ByteStruct):
    offset      = IntegerField()
    region_size = IntegerField()
    region      = VariableField()


class ChunkSaveStateHeader(ByteStruct):
    context_mode = IntegerField()


class ClassicString(ByteStruct):
    length = IntegerField()
    string = StringField(None)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.resize(ClassicString.string_field, self.length)


class ClassicWideString(ByteStruct):
    length = IntegerField()
    string = StringField(None, encoding='utf-16')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.resize(ClassicWideString.string_field, self.length * 2)


class ChunkSaveStateChallenge(ByteStruct):
    name        = StructField(ClassicWideString)
    uid         = StructField(ClassicString)
    collection  = StructField(ClassicString)


class DataChunk(ByteStruct):
    identifier      = IntegerField()
    content_size    = IntegerField()
    content         = VariableField()


class DataFile(ByteStruct):
    magic           = StringField(length=4)
    file_version    = IntegerField(False)
    client_version  = IntegerField(False)
    file_type       = IntegerField(False)
    reserved        = IntegerField()
    num_chunks      = IntegerField()
    simStateData    = SimStateData()

    def __init__(self, data: Iterable, master_offset: int = 0, **kwargs):
        super().__init__(data, master_offset, **kwargs)

        self.chunks = []
        chunk_offset = DataFile.min_size
        for _ in range(self.num_chunks):
            chunk = DataChunk(data, master_offset=chunk_offset)
            self._parse_chunk(chunk)
            self.chunks.append(chunk)

            chunk_offset += chunk.size

    def _parse_chunk(self, chunk: DataChunk):
        if chunk.identifier == 0x1001:
            chunk.resize(DataChunk.content_field, StructField(ChunkSaveStateHeader))
            return
        elif chunk.identifier == 0x100b:
            chunk.resize(DataChunk.content_field, StructField(ChunkSaveStateChallenge))
            return
        elif chunk.identifier == 0x100c:
            chunk.resize(DataChunk.content_field, StructField(CheckpointData))
            self.simStateData.cp_data = chunk.content
            return
        elif chunk.identifier == 0x100a:
            chunk.resize(DataChunk.content_field, StructField(ChunkSaveStateInputEvents))
            return

        chunk.resize(DataChunk.content_field, StructField(ChunkSaveStateRegion))
        if chunk.identifier == 0x1002:
            chunk.content.resize(ChunkSaveStateRegion.region_field, ByteArrayField(212))
            #print(chunk)
            #self.simStateData.timers = [0]
        elif chunk.identifier == 0x1003:
            chunk.content.resize(ChunkSaveStateRegion.region_field, StructField(HmsDynaStruct))
            self.simStateData.dyna = chunk.content
        elif chunk.identifier == 0x1004:
            chunk.content.resize(ChunkSaveStateRegion.region_field, StructField(SceneVehicleCar))
            self.simStateData.scene_mobil = chunk.content
        elif chunk.identifier == 0x1005:
            chunk.content.resize(ChunkSaveStateRegion.region_field, ArrayField(4, SimulationWheel))
            #self.simStateData.simulation_wheels = chunk.content
            print(self.simStateData.simulation_wheels)
        elif chunk.identifier == 0x1006:
            chunk.content.resize(ChunkSaveStateRegion.region_field, StructField(PhysicalObject))
            #self.simStateData.plug_solid = chunk.content
        elif chunk.identifier == 0x1007:
            chunk.content.resize(ChunkSaveStateRegion.region_field, ByteArrayField(chunk.content.region_size))
            #print(chunk)
        elif chunk.identifier == 0x1008:
            chunk.content.resize(
                ChunkSaveStateRegion.region_field,
                ArrayField(chunk.content.region_size // CachedInput.min_size, CachedInput)
            )
        elif chunk.identifier == 0x1009:
            chunk.content.resize(ChunkSaveStateRegion.region_field, StructField(PlayerInfoStruct))
            self.simStateData.player_info = chunk.content

def load_state(path: str) -> SimStateData:
    data = open(path, 'rb').read()
    state = DataFile(data)
    return state.simStateData

if __name__ == '__main__':
    import os
    # Change current directory from executing directory to script directory
    if os.path.dirname(__file__) != os.getcwd():
        print(f"Changing current directory from executing directory to script directory")
        print(f"{os.getcwd()} => {os.path.dirname(__file__)}")
        os.chdir(os.path.dirname(__file__))
    data = open('state.bin', 'rb').read()
    state = DataFile(data)
    for chunk in state.chunks:
        print(chunk.identifier)
        print(chunk.content_size)

    simStateData = SimStateData()
    """version                 = IntegerField(offset=0, signed=False)
    context_mode            = IntegerField(signed=False)
    flags                   = IntegerField(signed=False)
    timers                  = ArrayField(shape=53, elem_field_type=IntegerField)
    dyna                    = StructField(HmsDynaStruct, instance_with_parent=False)
    scene_mobil             = StructField(SceneVehicleCar, instance_with_parent=False)
    simulation_wheels       = ArrayField(shape=4, elem_field_type=SimulationWheel)
    plug_solid              = ByteArrayField(68)
    cmd_buffer_core         = ByteArrayField(264)
    player_info             = StructField(PlayerInfoStruct, instance_with_parent=False)
    internal_input_state    = ArrayField(shape=10, elem_field_type=CachedInput)

    input_running_event     = StructField(Event, instance_with_parent=False)
    input_finish_event      = StructField(Event, instance_with_parent=False)
    input_accelerate_event  = StructField(Event, instance_with_parent=False)
    input_brake_event       = StructField(Event, instance_with_parent=False)
    input_left_event        = StructField(Event, instance_with_parent=False)
    input_right_event       = StructField(Event, instance_with_parent=False)
    input_steer_event       = StructField(Event, instance_with_parent=False)
    input_gas_event         = StructField(Event, instance_with_parent=False)

    num_respawns            = IntegerField(signed=False)

    cp_data                 = StructField(CheckpointData, instance_with_parent=False)"""