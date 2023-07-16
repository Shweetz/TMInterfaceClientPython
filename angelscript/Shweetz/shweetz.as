void Main()
{
    RegisterVariable("shweetz_eval_time_min", 0);
    RegisterVariable("shweetz_eval_time_max", 10000);
    RegisterVariable("shweetz_next_eval_check", false);
    RegisterVariable("shweetz_next_eval", "speed");
    //RegisterVariable("shweetz_point", {50, 50, 300});
    RegisterVariable("shweetz_angle_min_deg", 80);
    RegisterVariable("shweetz_angle_max_deg", 90);

    // use builtin bf_condition_speed
    RegisterVariable("shweetz_min_cp", 0);
    RegisterVariable("shweetz_min_wheels_on_ground", 0);
    RegisterVariable("shweetz_gear", -1);
    // RegisterVariable("shweetz_trigger", 0);

    RegisterBruteforceEvaluation("1nosepos_plus", "Nosepos+", OnEvaluateNosePos, UINosePos);
    RegisterBruteforceEvaluation("2other", "Other", OnEvaluateOther);
    RegisterValidationHandler("1rules", "Rules to change inputs");
    RegisterValidationHandler("2other", "Other script that changes inputs");
}

void OnSimulationBegin(SimulationManager@ simManager)
{
    int baseRunDuration = simManager.EventsDuration;
    print("Base run time: " + baseRunDuration);
    if (GetVariableDouble("shweetz_eval_time_min") > GetVariableDouble("shweetz_eval_time_max") || GetVariableDouble("shweetz_eval_time_max") > baseRunDuration) {
        print("ERROR: MUST HAVE 'EVAL_TIME_MIN <= EVAL_TIME_MAX <= REPLAY_TIME'");
    }
}

void OnSimulationStep(SimulationManager@ simManager, bool userCancelled)
{
    string controller;
    if (GetVariable("controller", controller)) {
        if (controller == "rules") {
            OnSimulationStepRules(simManager, userCancelled);
        } else if (controller == "other") {
            OnSimulationStepOther(simManager, userCancelled);
        }
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
