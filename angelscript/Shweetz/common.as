bool IsEvalTime(int raceTime) {
    return GetVariableDouble("shweetz_eval_time_min") <= raceTime && raceTime <= GetVariableDouble("shweetz_eval_time_max");
}

bool IsPastEvalTime(int raceTime) {
    return GetVariableDouble("shweetz_eval_time_max") <= raceTime;
}

bool IsMaxTime(int raceTime) {
    return GetVariableDouble("shweetz_eval_time_max") == raceTime;
}

double DistanceToPoint(vec3 pos) {
    array<double> arr = { pos.x, pos.y, pos.z };
    return DistanceToPoint(arr);
}

double DistanceToPoint(array<double> pos) {
    array<double> POINT = {50, 50, 300};
    double a = 2.0;
    //return Math::Pow((pos[0]-POINT[0]), a) + Math::Pow((pos[1]-POINT[1]), a) + Math::Pow((pos[2]-POINT[2]), a);
    return (pos[0]-POINT[0]) * (pos[0]-POINT[0]) + (pos[1]-POINT[1]) * (pos[1]-POINT[1]) + (pos[2]-POINT[2]) * (pos[2]-POINT[2]);
}

int CountWheelsOnGround(SimulationManager@ simManager) {
    int count = 0;
    if (simManager.Wheels.FrontLeft.RTState.HasGroundContact) count++;
    if (simManager.Wheels.FrontRight.RTState.HasGroundContact) count++;
    if (simManager.Wheels.BackRight.RTState.HasGroundContact) count++;
    if (simManager.Wheels.BackLeft.RTState.HasGroundContact) count++;

    return count;
}

bool IsInTrigger(vec3 pos, array<double> TRIGGER) {
    double x1 = Math::Min(TRIGGER[0], TRIGGER[3]), x2 = Math::Max(TRIGGER[0], TRIGGER[3]);
    double y1 = Math::Min(TRIGGER[1], TRIGGER[4]), y2 = Math::Max(TRIGGER[1], TRIGGER[4]);
    double z1 = Math::Min(TRIGGER[2], TRIGGER[5]), z2 = Math::Max(TRIGGER[2], TRIGGER[5]);
    if (x1 <= pos.x && pos.x <= x2 && y1 <= pos.y && pos.y <= y2 && z1 <= pos.z && pos.z <= z2) {
        return true;
    }
    return false;
}

float Norm(vec3 vec) {
    return Math::Sqrt((vec.x * vec.x) + (vec.y * vec.y) + (vec.z * vec.z));
}

bool GetB(string str) {
    return GetVariableBool(str);
}

double GetD(string str) {
    return GetVariableDouble(str);
}

string GetS(string str) {
    return GetVariableString(str);
}