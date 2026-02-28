import re
import json
import traceback

try:
    html = open('bb_schedules.html', encoding='utf-8').read()
    # It might be in escaping mode, e.g. \"initialScheduleData\":
    m = re.search(r'\\?\"initialScheduleData\\?\":(\[.*?\]),\\?\"initialError\\?\"', html)
    if not m:
        print("Regex not matched!")
    else:
        json_str = m.group(1)
        # Because we extracted a string from JSON, we may need to unescape it
        # Actually in HTML next.js payload, it might be a JSON that we can parse directly
        # Let's try to parse
        json_str = json_str.replace('\\"', '"').replace('\\\\', '\\')
        try:
            data = json.loads(json_str)
            print("Successfully parsed initialScheduleData!")
            for loc_data in data:
                if loc_data.get("location") == "tokyo":
                    schedules = loc_data.get("schedules", [])
                    print(f"Found {len(schedules)} dates for tokyo")
                    if schedules:
                        print(json.dumps(schedules[5], ensure_ascii=False, indent=2))
        except Exception as e:
            print(f"JSON Parse Error: {e}")
            print(json_str[:100] + "...")
except Exception as e:
    traceback.print_exc()
