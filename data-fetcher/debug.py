import urllib.request
import json

url = 'https://www.billboard-live.com/tokyo/schedules'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req) as r:
        html = r.read().decode('utf-8')
    
    parts = html.split('"initialScheduleData":')
    if len(parts) > 1:
        json_str = parts[1].split(',"initialError"')[0]
        data = json.loads(json_str)
        tokyo_data = next((d for d in data if d.get('location') == 'tokyo'), None)
        if tokyo_data:
            first_item = tokyo_data['schedules'][0]
            print("--- Top Level Object ---")
            for k, v in first_item.items():
                if 'url' in k or 'id' in k or 'link' in k:
                    print(f"{k}: {v}")
            
            print("\n--- Event Level Object ---")
            first_event = first_item['schedules'][0][0]
            for k, v in first_event.items():
                if 'url' in k or 'id' in k or 'link' in k:
                    print(f"{k}: {v}")
except Exception as e:
    print(e)
