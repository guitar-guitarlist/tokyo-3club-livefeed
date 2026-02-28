import requests, json, re, codecs
url = 'https://www.billboard-live.com/tokyo/schedules'
res = requests.get(url)
m = re.search(r'\\?"initialScheduleData\\?":(\[.*?\]),\\?"initialError\\?"', res.text)
if m:
    json_str = m.group(1).replace('\\"', '"').replace('\\\\', '\\')
    data = json.loads(json_str)
    with codecs.open('bb.json', 'w', 'utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("Done writing bb.json")
else:
    print("No match")
