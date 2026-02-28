import requests
import re
import json

res = requests.get('https://www.billboard-live.com/tokyo/schedules')
m = re.search(r'\\?"initialScheduleData\\?":(\[.*?\]),\\?"initialError\\?"', res.text)
if m:
    json_str = m.group(1).replace('\\"', '"').replace('\\\\', '\\')
    data = json.loads(json_str)
    for loc_data in data:
        if loc_data.get("location") == "tokyo":
            print(f"Found {len(loc_data.get('schedules', []))} dates")
            for item in loc_data.get("schedules", []):
                print(item.get("dates", [])[0])
else:
    print("Not found")
