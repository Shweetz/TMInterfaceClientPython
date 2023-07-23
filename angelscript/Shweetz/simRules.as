
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

        string inputModifier = GetS("shweetz_input_modifier");
        inputModifier = BuildCombo("Input Modifier", inputModifier, inputModifiers);
        SetVariable("shweetz_input_modifier", inputModifier);
        if (inputModifier == "Built-in")
        {
            UIInputBuiltin();
        }
        if (inputModifier == "Rules")
        {
            UIRules();
        }
        UI::Dummy( vec2(0, 25) );
    }
}

string BuildCombo(string& label, string& value, array<string> values)
{
    //print("BuildCombo");
    string ret = value;
    if (UI::BeginCombo(label, value)) {
        for (uint i = 0; i < values.Length; i++)
        {
            string currentValue = values[i];
            if (UI::Selectable(currentValue, value == currentValue))
            {
                ret = currentValue;
                print("aaaaaaret=" + ret);
            }
        }
            
        UI::EndCombo();
    }
    //print("ret=" + ret);
    return ret;
}

void UIInputBuiltin()
{
    UI::PushItemWidth(300);
    UI::InputIntVar("Input Modify Count", "bf_modify_count", 1);
    UI::TextDimmed("At most " + GetD("bf_modify_count") + " inputs will be changed each attempt.");
    UI::Dummy(vec2(0, 15));
    
    UI::PushItemWidth(230);
    UI::Text("Time frame in which inputs can be changed:");
    UI::Text("From       ");
    UI::SameLine();
    UI::InputTimeVar("##from", "bf_inputs_min_time");
    UI::Text("To            ");
    UI::SameLine();
    UI::InputTimeVar("##to", "bf_inputs_max_time");
    UI::TextDimmed("Limiting this time frame will make the bruteforcing process faster.");
    UI::Dummy(vec2(0, 15));
    
    UI::PushItemWidth(300);
    UI::SliderIntVar("Maximum Steering Difference", "bf_max_steer_diff", 0, 131072);
    UI::TextDimmed("Bruteforce will randomize a number between [-" + GetD("bf_max_steer_diff") + ", " + GetD("bf_max_steer_diff") + "]");
    UI::TextDimmed("and add it to the current steering value.");
    UI::Dummy(vec2(0, 15));
    
    UI::InputTimeVar("Maximum Time Difference", "bf_max_time_diff");
    UI::TextDimmed("Bruteforce will randomize a number between [-" + GetD("bf_max_time_diff") + "s, " + GetD("bf_max_time_diff") + "s]");
    UI::TextDimmed("and add it to the current time value.");
    
    UI::CheckboxVar("Fill Missing Steering Input", "bf_inputs_fill_steer");
    UI::TextDimmed("Timestamps with no steering input changes will be filled with");
    UI::TextDimmed("existing values resulting in more values that can be changed.");
    UI::TextDimmed("1.00 steer 3456 -> 1.00 steer 3456");
    UI::TextDimmed("1.30 steer 1921     1.10 steer 3456");
    UI::TextDimmed("                                1.20 steer 3456");
    UI::TextDimmed("                                1.30 steer 1921");
    UI::Dummy(vec2(0, 15));

    UI::PopItemWidth();
}

void UIRules()
{
    //print("" + rules.Length);
    Deserialize(GetS("shweetz_rules"));

    if (UI::Button("Add Rule")) {
        rules.InsertLast(Rule());
    }
    UI::SameLine();
    if (UI::Button("Clear Rules")) {
        rules.Resize(0);
    }
    UI::Dummy( vec2(0, 25) );
    
    int width = 110;
    UI::PushItemWidth(width);

    UI::Text("Start Time (ms)    ");
    UI::SameLine();
    UI::Text("End Time (ms)      ");
    UI::SameLine();
    UI::Text("Input type           ");
    UI::SameLine();
    UI::Text("Change type         ");
    UI::SameLine();
    UI::Text("Diff             ");
    UI::SameLine();
    UI::Text("Proba                  ");

    UI::Separator();

    for (uint i = 0; i < rules.Length; i++)
    {
        Rule@ currentRule = rules[i];

        currentRule.start_time = UI::InputInt("##start_time_" + i, currentRule.start_time, 100);
        UI::SameLine();
        
        currentRule.end_time = UI::InputInt("##end_time_" + i, currentRule.end_time, 100);
        UI::SameLine();
        
        string inputType = currentRule.input;
        if (UI::BeginCombo("##inputType_" + i, inputType)) {
            for (uint j = 0; j < inputTypes.Length; j++)
            {
                string currentInputType = inputTypes[j];
                if (UI::Selectable(currentInputType, inputType == currentInputType)) {
                    currentRule.input = currentInputType;
                }
            }
                
            UI::EndCombo();
        }
        UI::SameLine();

        string changeType = currentRule.change;
        if (UI::BeginCombo("##changeType_" + i, changeType)) {
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
        UI::SameLine();

        currentRule.diff = UI::InputInt("##diff_" + i, currentRule.diff, 10);
        UI::SameLine();

        currentRule.proba = UI::InputFloat("##proba_" + i, currentRule.proba, 0.01);
        
        // Validate/force values
        if (currentRule.start_time < 0) {
            currentRule.start_time = 0;
        }
        if (currentRule.start_time > currentRule.end_time) {
            currentRule.end_time = currentRule.start_time;
        }
        if (currentRule.input == "") {
            currentRule.input = inputTypes[0];
        }
        if (currentRule.change == "") {
            currentRule.change = changeTypes[0];
        }
        if (currentRule.input != "Steer" && currentRule.change == "Steering") {
            currentRule.change = "Timing";
        }
        //UI::Text(currentRule.toString());
        
        UI::Dummy( vec2(0, 10) );
    }
    
    UICopyButtons(width);
    
    UI::PopItemWidth();

    SetVariable("shweetz_rules", Serialize(rules));
}

void UICopyButtons(int width)
{
    if (UI::Button("Copy 1st for all##1", vec2(width, 25))) {
        for (uint i = 1; i < rules.Length; i++) {
            rules[i].start_time = rules[0].start_time;
        }
    }
    UI::SameLine();
    if (UI::Button("Copy 1st for all##2", vec2(width, 25))) {
        for (uint i = 1; i < rules.Length; i++) {
            rules[i].end_time = rules[0].end_time;
        }
    }
    UI::SameLine();
    if (UI::Button("Copy 1st for all##3", vec2(width, 25))) {
        for (uint i = 1; i < rules.Length; i++) {
            rules[i].input = rules[0].input;
        }
    }
    UI::SameLine();
    if (UI::Button("Copy 1st for all##4", vec2(width, 25))) {
        for (uint i = 1; i < rules.Length; i++) {
            rules[i].change = rules[0].change;
        }
    }
    UI::SameLine();
    if (UI::Button("Copy 1st for all##5", vec2(width, 25))) {
        for (uint i = 1; i < rules.Length; i++) {
            rules[i].diff = rules[0].diff;
        }
    }
    UI::SameLine();
    if (UI::Button("Copy 1st for all##6", vec2(width, 25))) {
        for (uint i = 1; i < rules.Length; i++) {
            rules[i].proba = rules[0].proba;
        }
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
