void Main()
{
    RegisterVariable("shweetz_target", "Nosepos+");
    RegisterVariable("shweetz_eval_time_min", 0);
    RegisterVariable("shweetz_eval_time_max", 10000);
    RegisterVariable("shweetz_next_eval_check", false);
    RegisterVariable("shweetz_next_eval", "speed");
    RegisterVariable("shweetz_point", "0 0 0");
    RegisterVariable("shweetz_angle_min_deg", 80);
    RegisterVariable("shweetz_angle_max_deg", 90);

    // Conditions
    // use builtin bf_condition_speed
    RegisterVariable("shweetz_min_cp", 0);
    RegisterVariable("shweetz_min_wheels_on_ground", 0);
    RegisterVariable("shweetz_gear", -1);
    // RegisterVariable("shweetz_trigger", 0);

    // Input change
    RegisterVariable("shweetz_load_inputs_from_file", "");
    RegisterVariable("shweetz_load_replay_from_file", "");
    RegisterVariable("shweetz_lock_base_run", false);
    // lock: always/never/for X times/for X iterations/for X it since last improv
    RegisterVariable("shweetz_fill_inputs", false);
    RegisterVariable("shweetz_change_prob", 0);

    // Handlers
    RegisterBruteforceEvaluation("1nosepos_plus", "Nosepos+", OnEvaluateNosePos, UIBfNosePos);
    //RegisterBruteforceEvaluation("2other", "Other", OnEvaluateOther);
    RegisterValidationHandler("rules", "Shweetz's custom validation", UIValidation);
    //RegisterValidationHandler("other", "Other script that changes inputs");
}

void OnSimulationBegin(SimulationManager@ simManager)
{
    int baseRunDuration = simManager.EventsDuration;
    print("Base run time: " + baseRunDuration);
    if (GetD("shweetz_eval_time_min") > GetD("shweetz_eval_time_max") || GetD("shweetz_eval_time_max") > baseRunDuration) {
        print("ERROR: MUST HAVE 'EVAL_TIME_MIN <= EVAL_TIME_MAX <= REPLAY_TIME'");
    }
    string controller = GetS("controller");
    if (controller == "rules") {
        OnSimulationBeginRules(simManager);
    } else if (controller == "other") {
        //OnSimulationBeginOther(simManager);
    }
}

void OnSimulationStep(SimulationManager@ simManager, bool userCancelled)
{
    string controller = GetS("controller");
    if (controller == "rules") {
        OnSimulationStepRules(simManager, userCancelled);
    } else if (controller == "other") {
        OnSimulationStepOther(simManager, userCancelled);
    }
}

PluginInfo@ GetPluginInfo()
{
    auto info = PluginInfo();
    info.name = "Shweetz's plugin";
    info.author = "Shweetz";
    info.version = "v1.0.0";
    info.description = "Description";
    return info;
}
