// array<double> POINT = {50, 50, 300};
// array<double> TRIGGER = {523, 9, 458, 550, 20, 490};

void UIBfNosePos()
{
    UINosePos();
    UI::Separator();
    UIConditions();
}

void UINosePos()
{
    ///// Change a variable manually
    // double time;
    // GetVariable("plugin_time", time);
    // time = UI::InputTime("Some time", time);
    // SetVariable("plugin_time", time);
    //
    ///// Change a variable manually v2
    // string str = GetS("plugin_str");
    // combo shit => SetVariable("plugin_str", str);

    UI::InputTimeVar("Eval time min", "shweetz_eval_time_min");
    UI::InputTimeVar("Eval time max", "shweetz_eval_time_max");
        
    UI::Dummy( vec2(0, 25) );

    if (UI::CheckboxVar("Change eval after nosepos is good enough", "shweetz_next_eval_check"))
    {
        UI::TextDimmed("Good enough means angle can be some degrees off from ideal nosepos.");
        UI::InputIntVar("Max angle from ideal (°)", "shweetz_angle_min_deg", 1);

        string next_eval = GetS("shweetz_next_eval");
        if (UI::BeginCombo("Next eval", next_eval)) {
            for (uint i = 0; i < modes.Length; i++)
            {
                string currentMode = modes[i];
                if (UI::Selectable(currentMode, next_eval == currentMode))
                {
                    SetVariable("shweetz_next_eval", currentMode);
                }
            }
                
            UI::EndCombo();
        }

        if (next_eval == "Point") {
            /*Point point(GetS("shweetz_point"));
            if (UI::DragFloat3("Point", point.pvec)) {
                SetVariable("shweetz_point", point.toStr());
            }*/
            if (UI::DragFloat3Var("Point", "shweetz_point")) {
                point.str(GetS("shweetz_point"));
            }
        }
    }

    UI::Dummy( vec2(0, 25) );
}

void UIConditions()
{
    UI::SliderFloatVar("Min speed (km/h)", "bf_condition_speed", 0.0f, 1000.0f);
    UI::InputIntVar("Min CP collected", "shweetz_min_cp", 1);
    UI::SliderIntVar("Min wheels on ground", "shweetz_min_wheels_on_ground", 0, 4);
    UI::SliderIntVar("Gear (-1 to disable)", "shweetz_gear", -1, 6);
    UI::InputIntVar("Trigger index (-1 to disable)", "shweetz_trigger", 1);
    //int triggerIndex = int(GetD("shweetz_trigger"))-1;
    Trigger3D trigger = GetTriggerVar();
    if (trigger.Size.x != -1) {
        vec3 pos2 = trigger.Position + trigger.Size;
        UI::TextDimmed("The car must be in the trigger of coordinates: ");
        UI::TextDimmed("" + trigger.Position.ToString() + " " + pos2.ToString());
    }
    /*int triggerIndex = int(GetD("shweetz_trigger"))-1;
    if (triggerIndex > -1) {
        Trigger3D trigger;
        GetTrigger(trigger, GetTriggerIds()[triggerIndex]);
        print("" + triggerIndex);
        print("The car must be in the trigger of coordinates: " + trigger.Position.ToString());
        //UI::TextDimmed("The car must be in the trigger of coordinates: " + trigger.Position.ToString());
    }*/
    //print("" + IsInTrigger(vec3(100, 100, 100), int(GetD("shweetz_trigger_index"))));
    vec3 v = vec3(100 ,100, 100);
    //print("" + v.ToString());

    UI::Dummy( vec2(0, 25) );
}

class CarState
{
    double time = -1;
    double angle = -1;
    double distance = -1;
    double speed = -1;
}

auto best = CarState();

BFEvaluationResponse@ OnEvaluateNosePos(SimulationManager@ simManager, const BFEvaluationInfo&in info)
{
    int raceTime = simManager.RaceTime;
    //int time = simManager.PlayerInfo.RaceTime;
    //vec3 pos = simManager.Dyna.CurrentState.Location.Position;
    
    auto curr = CarState();
    curr.time = raceTime;

    auto resp = BFEvaluationResponse();

    if (info.Phase == BFPhase::Initial) {
        if (IsEvalTime(raceTime) && IsBetter(simManager, curr)) {
            best = curr;
        }

        if (IsMaxTime(raceTime)) {
            string greenText = "base at " + best.time + ": angle=" + best.angle;
            if (GetS("shweetz_next_eval") == "Point") greenText += ", distance=" + best.distance;
            if (GetS("shweetz_next_eval") == "Speed") greenText += ", speed=" + best.speed;          
            print(greenText);
        }
    }
    else {
        if (IsEvalTime(raceTime) && IsBetter(simManager, curr)) {
            resp.Decision = BFEvaluationDecision::Accept;
        }

        if (IsPastEvalTime(raceTime)) {
            if (resp.Decision != BFEvaluationDecision::Accept) {
                resp.Decision = BFEvaluationDecision::Reject;
                //print("worse at " + raceTime + ": distance=" + curr.distance);
            }
        }
    }

    return resp;
}

bool IsBetter(SimulationManager@ simManager, CarState& curr) {
    // Get values
    int raceTime = simManager.PlayerInfo.RaceTime;
    vec3 pos = simManager.Dyna.CurrentState.Location.Position;
    vec3 speedVec = simManager.Dyna.CurrentState.LinearSpeed;
    float speed = Norm(speedVec);
    float speedKmh = speed * 3.6;
    float carYaw, carPitch, carRoll;
    simManager.Dyna.CurrentState.Location.Rotation.GetYawPitchRoll(carYaw, carPitch, carRoll);

    // Conditions
    if (!AreConditionsMet(simManager)) {
        return false;
    }
    
    // Do calculations
    double targetYaw = Math::ToDeg(Math::Atan2(speedVec.x, speedVec.z));
    double targetPitch = 90;
    double targetRoll = 0;

    double diffYaw   = Math::Abs(Math::ToDeg(carYaw) - targetYaw);
    double diffPitch = Math::Abs(Math::ToDeg(carPitch) - targetPitch);
    double diffRoll  = Math::Abs(Math::ToDeg(carRoll) - targetRoll);
    diffYaw = Math::Max(diffYaw - 90, 0.0); // [-90; 90]° yaw is ok to nosebug, so 100° should only add 10°

    curr.angle = diffYaw + diffPitch + diffRoll;
    curr.distance = DistanceToPoint(pos);
    curr.speed = speedKmh;

    //print("distance=" + curr.distance);
    //print("" + raceTime + ": distance=" + DistanceToPoint(pos));

    if (best.distance == -1) {
        // Base run (past conditions)
        return true;
    } 
    
    if (best.angle < GetD("shweetz_angle_min_deg") && curr.angle < GetD("shweetz_angle_min_deg")) {
        // Best and current have a good angle, now check next eval
        if (GetS("shweetz_next_eval") == "Point") {
            return curr.distance < best.distance;
        }
        if (GetS("shweetz_next_eval") == "Speed") {
            return curr.speed > best.speed;
        }
        if (GetS("shweetz_next_eval") == "Time") {
            return curr.time < best.time;
        }
    }
    //print("" + curr.angle + " vs " + best.angle);
    return curr.angle < best.angle;
}

bool AreConditionsMet(SimulationManager@ simManager)
{
    float speedKmh = Norm(simManager.Dyna.CurrentState.LinearSpeed) * 3.6;
    vec3 pos = simManager.Dyna.CurrentState.Location.Position;

    if (GetD("bf_condition_speed") > speedKmh) {
        //print("Speed too low: " + speedKmh + " < " + GetD("bf_condition_speed"));
        return false;
    }
        //print("Speed is ok  : " + speedKmh);

    if (GetD("shweetz_min_cp") > int(simManager.PlayerInfo.CurCheckpointCount)) {
        return false;
    }

    if (GetD("shweetz_min_wheels_on_ground") > CountWheelsOnGround(simManager)) {
        return false;
    }

    if (GetD("shweetz_gear") != -1 && GetD("shweetz_gear") != simManager.SceneVehicleCar.CarEngine.Gear) {
        return false;
    }

    //print("" + IsInTrigger(pos, int(GetD("shweetz_trigger_index"))));
    if (!IsInTrigger(pos, int(GetD("shweetz_trigger_index")))) {
        return false;
    }

    // if (simManager.SceneVehicleCar.IsFreeWheeling) {
    //     return false;
    // }

    return true;
}
