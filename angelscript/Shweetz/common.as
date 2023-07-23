array<string> targets = { "Nosepos+" };
array<string> modes = { "Point", "Speed", "Time" };
array<string> inputModifiers = { "Built-in", "Rules" };
array<Rule@> rules;
//Rules@ rules;
array<string> inputTypes = { "Steer", "Accelerate", "Brake" };
array<string> changeTypes = { "Steering", "Timing", "Create" };
Point point;

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
    //Point point(GetS("shweetz_point"));
    return Math::Distance(pos, point.pvec);
}

/*double DistanceToPoint(array<double> pos) {
    Point point(GetS("shweetz_point"));
    vec3 pvec = point.pvec;
    //double a = 2.0;
    //return Math::Pow((pos[0]-POINT[0]), a) + Math::Pow((pos[1]-POINT[1]), a) + Math::Pow((pos[2]-POINT[2]), a);
    return (pos[0]-pvec[0]) * (pos[0]-pvec[0]) + (pos[1]-pvec[1]) * (pos[1]-pvec[1]) + (pos[2]-pvec[2]) * (pos[2]-pvec[2]);
}*/

int CountWheelsOnGround(SimulationManager@ simManager) {
    int count = 0;
    if (simManager.Wheels.FrontLeft.RTState.HasGroundContact) count++;
    if (simManager.Wheels.FrontRight.RTState.HasGroundContact) count++;
    if (simManager.Wheels.BackRight.RTState.HasGroundContact) count++;
    if (simManager.Wheels.BackLeft.RTState.HasGroundContact) count++;

    return count;
}

bool IsInTrigger(vec3& pos, array<double>& TRIGGER) {
    double x1 = Math::Min(TRIGGER[0], TRIGGER[3]), x2 = Math::Max(TRIGGER[0], TRIGGER[3]);
    double y1 = Math::Min(TRIGGER[1], TRIGGER[4]), y2 = Math::Max(TRIGGER[1], TRIGGER[4]);
    double z1 = Math::Min(TRIGGER[2], TRIGGER[5]), z2 = Math::Max(TRIGGER[2], TRIGGER[5]);
    if (x1 <= pos.x && pos.x <= x2 && y1 <= pos.y && pos.y <= y2 && z1 <= pos.z && pos.z <= z2) {
        return true;
    }
    return false;
}

bool IsInTrigger(vec3& pos, int triggerIndex) {
    Trigger3D trigger;
    GetTrigger(trigger, triggerIndex);
    return trigger.ContainsPoint(pos);
}

float Norm(vec3& vec) {
    return Math::Sqrt((vec.x * vec.x) + (vec.y * vec.y) + (vec.z * vec.z));
}

bool GetB(string& str) {
    return GetVariableBool(str);
}

double GetD(string& str) {
    return GetVariableDouble(str);
}

string GetS(string& str) {
    return GetVariableString(str);
}

class Point
{
    string pstr;
    vec3 pvec;

    Point()
    {
        str("0 0 0");
    }

    Point(string s)
    {
        str(s);
    }

    void str(string s)
    {
        pstr = s;
        array<string>@ splits = s.Split(" ");
        pvec = vec3(Text::ParseFloat(splits[0]), Text::ParseFloat(splits[1]), Text::ParseFloat(splits[2]));
        pvec.y = Text::ParseFloat(splits[1]);
        pvec.z = Text::ParseFloat(splits[2]);
    }

    void vec(vec3 v)
    {
        pvec = v;
    }

    string toStr() 
    {
        return "" + pvec.x + " " + pvec.y + " " + pvec.z;
    }

    vec3 toVec3() 
    {
        return pvec;
    }
}

/* RULES */

/*enum Change
{
    STEER_,
    TIMING,
    CREATE,
    AVG_REBRUTE
}

string EnumToString(Change enumVal)
{
    switch(enumVal)
    {
    case Change::STEER_:
        return "steer";
    case Change::TIMING:
        return "timing";
    case Change::CREATE:
        return "create";
    case Change::AVG_REBRUTE:
        return "avg_rebrute";
    default:
        return "ERROR";
    }
}*/

class Rule
{
    string input;
    string change;
    float proba;
    int start_time;
    int end_time;
    int diff;

    Rule()
    {
        Rule(inputTypes[0], changeTypes[0], 0.01, 0, 0, 50);
    }

    Rule(string i, string c, float p, int s, int e, int d)
    {
        input = i;
        change = c;
        proba = p;
        start_time = s;
        end_time = e;
        diff = d;
    }

    string serialize()
    {
        return input + "," + change + "," + proba + "," + start_time + "," + end_time + "," + diff;
    }

    void deserialize(string str)
    {
        print(str);
        array<string>@ splits = str.Split(",");
        input = splits[0];
        change = splits[1];
        proba = Text::ParseFloat(splits[2]);
        start_time = Text::ParseInt(splits[3]);
        end_time = Text::ParseInt(splits[4]);
        diff = Text::ParseInt(splits[5]);
    }

    string toString()
    {
        return "rule: From " + start_time + " to " + end_time + ", change " + input + " " + change + " with max diff of " + diff + " and modify_prob=" + proba;
    }
}

string Serialize(array<Rule@> rules)
{
    string str = "";
    for (uint i = 0; i < rules.Length; i++) {
        str += rules[i].serialize() + " ";
    }
    return str;
}

void Deserialize(string rules_str)
{
    rules.Resize(0);
    // Separate big string in rules
    array<string>@ splits = rules_str.Split(" ");
    print("<" + rules_str + ">");
    print("a " + splits.Length);
    for (uint i = 0; i < splits.Length; i++) {
        if (splits[i] == "") {
            continue;
        }
        rules.InsertLast(Rule());
        rules[i].deserialize(splits[i]);
    }
}

/*class Rules
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

    void deserialize(string rule_str)
    {
        // TODO
    }

    uint Length()
    {
        return rules.Length;
    }
}*/

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
