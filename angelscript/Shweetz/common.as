array<string> modes = { "None", "Point", "Speed", "Time" };

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

class Point
{
    string point;
    vec3 vpoint;

    Point(string s)
    {
        point = s;
    }

    void str(string s)
    {
        point = s;
    }

    void vec(vec3 v)
    {
        vpoint = v;
    }

    string toStr() 
    {
        return point;
    }

    vec3 toVec3() 
    {
        return vec3(0, 0, 0);
    }
}

/* RULES */

enum Change
{
    STEER_,
    TIMING,
    CREATE,
    AVG_REBRUTE
}

class Rule
{
    string input;
    Change change_type;
    float proba;
    int start_time;
    int end_time;
    int diff;

    Rule(string i, Change c, float p, int s, int e, int d)
    {
        input = i;
        change_type = c;
        proba = p;
        start_time = s;
        end_time = e;
        diff = d;
    }

    string serialize()
    {
        return input + "," + change_type + "," + proba + "," + start_time + "," + end_time + "," + diff;
    }

    void deserialize()
    {
        // TODO string -> rule
    }

    string toString()
    {
        return "rule: From " + start_time + " to " + end_time + ", change " + change_type + " for " + input + " with max diff of " + diff + " and modify_prob=" + proba;
    }
}

class Rules
{
    array<Rule@> rules;
    string serialize()
    {
        string str = "";
        for (uint i = 0; i < rules.Length; i++) {
            str += rules[i].serialize();
        }
        return str;
    }

    string deserialize()
    {
        // TODO
        return "";
    }
}

void FillInputs(TM::InputEventBuffer@ inputBuffer) 
{
    int startFill = 0;
    int endFill = inputBuffer.Length;
    int currSteer = 0;
    int i = 0;
    TM::InputEvent event = inputBuffer.opIndex(i);

    for (int time = startFill; time <= endFill; time += 10) {
        // Look for steer event at time, or
        print("" + event.Time + "," + event.Value.EventIndex);
        // if (event.Time = inputBuffer.opIndex(i);
    }
}

void SaveResult()
{
    CommandList list;
    list.Content = "0.00 press...";
    list.Save("result.txt");
    /*file f;
    // Open the file in 'read' mode
    if( f.open("file.txt", "w") >= 0 ) 
    {
        f.writeString("hello");
        f.close();
    }*/
}

void LoadSaveStateFromFile(SimulationManager@ simManager, string&in filename) {
    print("Loading save state " + filename);
    string error;
    SimulationStateFile f;
    f.Load(filename, error);
    print(error);
    simManager.RewindToState(f);
    print("Loaded save state at " + simManager.RaceTime);
}
