array<Rule@> rules;
SimulationState@ stateMinChange = null;
int iterationCount;
TM::InputEventBuffer@ unrandomizedInputBuffer;
TM::InputEventBuffer@ inputBuffer;
int lowestPossChange;
int highestPossChange;

void UIValidation()
{
    if (UI::CollapsingHeader("Optimization"))
    {
        string target = GetS("shweetz_target");
        if (UI::BeginCombo("Target", target)) {
            for (uint i = 0; i < targets.Length; i++)
            {
                string currentTarget = targets[i];
                if (UI::Selectable(currentTarget, target == currentTarget))
                {
                    SetVariable("shweetz_next_eval", currentTarget);
                }
            }
                
            UI::EndCombo();
        }
        
        UINosePos();
    }

    if (UI::CollapsingHeader("Conditions"))
    {
        UIConditions();
    }

    if (UI::CollapsingHeader("Input Modification"))
    {
        UIRules();
    }
}

void UIRules()
{
    if (UI::Button("Add Rule")) {
        rules.InsertLast(Rule());
    }
    
    UI::Text("Input type");
    UI::SameLine();
    UI::Text("Change type");

    for (uint i = 0; i < rules.Length; i++)
    {
        Rule@ currentRule = rules[i];
        string inputType = currentRule.input;
        if (UI::BeginCombo("##inputType", inputType)) {
            for (uint j = 0; j < inputTypes.Length; j++)
            {
                string currentInputType = inputTypes[j];
                if (UI::Selectable(currentInputType, inputType == currentInputType)) {
                    currentRule.input = currentInputType;
                }
            }
                
            UI::EndCombo();
        }
        string changeType = currentRule.change;
        if (UI::BeginCombo("##changeType", changeType)) {
            for (uint j = 0; j < changeTypes.Length; j++)
            {
                string currentChangeType = changeTypes[j];
                if (currentChangeType == "Steering" && currentRule.input != "Steer") {
                    continue;
                }
                if (UI::Selectable(currentChangeType, changeType == currentChangeType)) {
                    currentRule.change = currentChangeType;
                }
            }
                
            UI::EndCombo();
        }
        if (currentRule.input != "Steer" && currentRule.change == "Steering") {
            currentRule.change = "Timing";
        }
        UI::Text(currentRule.toString());
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
