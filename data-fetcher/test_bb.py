import requests
import re
res = requests.get('https://www.billboard-live.com/tokyo/schedules?year=2026&month=3')
m = re.search(r'"initialScheduleData":(\[.*?\]),"initialError"', res.text)
if m:
    print("Found")
else:
    print("Not found")
