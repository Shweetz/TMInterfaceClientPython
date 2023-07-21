array<Rule@> rules;
SimulationState@ stateMinChange = null;
int iterationCount;
TM::InputEventBuffer@ unrandomizedInputBuffer;
TM::InputEventBuffer@ inputBuffer;
int lowestPossChange;
int highestPossChange;

void UIRules()
{
    if (UI::CollapsingHeader("General"))
    {
        /*timeFrom  = UI::InputTimeVar("Time to start at", TIME_FROM);
        timeTo    = UI::InputTimeVar("Time to stop at", TIME_TO);
        direction = UI::SliderIntVar("Direction", DIRECTION, Direction::left, Direction::right, "");
        direction = direction == Direction::left ? -1 : 1;*/
    }

    if (UI::CollapsingHeader("Modes"))
    {
        /*if (UI::BeginCombo("Mode", mode))
        {
            for (uint i = 0; i < modes.Length; i++)
            {
                string newMode = modes[i];
                if (UI::Selectable(newMode, mode == newMode))
                {
                    SetVariable(MODE, newMode);
                    mode = newMode;
                    @funcs = GetScriptFuncs(newMode);
                }
            }

            UI::EndCombo();
        }
        funcs.settings();*/
    }
}

void OnSimulationBeginRules(SimulationManager@ simManager)
{
    /*lowestPossChange = rules[0].start_time;
    highestPossChange = rules[0].end_time;
    for (uint i = 1; i < rules.Length; i++) {
        lowestPossChange = Math::Min(lowestPossChange, rules[i].start_time);
        highestPossChange = Math::Max(highestPossChange, rules[i].end_time);
    }*/

    @stateMinChange = null;
    iterationCount = 0;
    @unrandomizedInputBuffer = simManager.InputEvents;
    @inputBuffer = simManager.InputEvents;
    print("Replay time: " + inputBuffer.Length);

    /*print(inputBuffer.ToCommandsText());
    print("" + inputBuffer.opIndex(1).Time);
    inputBuffer.opIndex(1).Time = 100020;
    print(inputBuffer.ToCommandsText());
    print("aaaaaa time: " + inputBuffer.Length);
    if (GetB("shweetz_fill_inputs")) {
        FillInputs(inputBuffer);
    }*/
}

void OnSimulationStepRules(SimulationManager@ simManager, bool userCancelled)
{
    int raceTime = simManager.RaceTime;
    if (stateMinChange is null) {
        if (raceTime == 0) {
            string saveStateFile = GetS("shweetz_load_replay_from_file");
            saveStateFile = "state.bin";
            if (saveStateFile != "") {
                LoadSaveStateFromFile(simManager, saveStateFile);
            }
        }

        if (raceTime == lowestPossChange) { // -10 ?
            @stateMinChange = simManager.SaveState();
            print("Start state for attempts created at " + raceTime);
        }
    }

    auto curr = CarState();
    curr.time = raceTime;
    if (IsEvalTime(raceTime) && IsBetter(simManager, curr)) {

        if (!GetB("shweetz_lock_base_run")) {
            @unrandomizedInputBuffer = inputBuffer;
        }
        SaveResult();

    }
}

/*bool IsBetter(SimulationManager@ simManager, CarState& curr) {
    return false;
}*/

/*void OnRunStep(SimulationManager@ simManager)
{
}


void OnSimulationEnd(SimulationManager@ simManager, SimulationResult result)
{
}

void OnCheckpointCountChanged(SimulationManager@ simManager, int count, int target)
{
}

void OnLapsCountChanged(SimulationManager@ simManager, int count, int target)
{
}

void Render()
{
}

void OnDisabled()
{
}*/
