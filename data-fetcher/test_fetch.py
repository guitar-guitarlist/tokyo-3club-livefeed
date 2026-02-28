import requests
import json
import re

print("Testing Billboard data...")
url = "https://www.billboard-live.com/tokyo/schedules"
res = requests.get(url)

m = re.search(r'\"initialScheduleData\":\s*(\[.*?\]),\s*\"initialError\"', res.text)
if m:
    json_str = m.group(1).replace('\\"', '"').replace('\\\\', '\\')
    data = json.loads(json_str)
    
    for d in data:
        if d['location'] == 'tokyo':
            print("Tokyo schedules count:", len(d.get('schedules', [])))
            for s in d.get('schedules', [])[:3]:
                print(s.get('dates', [''])[0])
else:
    print("Initial schedule pattern not found")

# Test Billboard schedule request for next month
try:
    print("\nTesting Billboard API endpoint if exists...")
    res2 = requests.post("https://www.billboard-live.com/api/schedules", json={
        "location": "tokyo",
        "ym": "202603"
    })
    print("API status:", res2.status_code)
    if res2.status_code == 200:
        print("API response length:", len(res2.text))
except Exception as e:
    print("API Error:", e)

# Test Cotton Club artist mapping issue
try:
    print("\nTesting CC artist map")
    from bs4 import BeautifulSoup
    base_url = "https://www.cottonclubjapan.co.jp/jp/schedule/"
    res3 = requests.get(base_url, headers={'User-Agent': 'Mozilla/5.0'})
    res3.encoding = 'utf-8'
    soup = BeautifulSoup(res3.text, 'html.parser')
    url_map = {}
    for a in soup.find_all('a', href=True):
        href = a['href']
        if '/sp/artists/' in href or '/artists/' in href:
            parts = [x for x in href.split('/') if x]
            if not parts: continue
            slug = parts[-1]
            slug_no_date = re.sub(r'-\d+$', '', slug)
            norm = re.sub(r'[\s\W_]+', '', slug_no_date.lower())
            
            full_url = href
            if full_url.startswith('/'):
                full_url = "https://www.cottonclubjapan.co.jp" + full_url
                
            if norm and len(norm) > 3:
                url_map[norm] = full_url
    
    sorted_map = {k: url_map[k] for k in sorted(url_map.keys(), key=len, reverse=True)}
    print("CC map size:", len(sorted_map))
    
    test_artists = [
        "ACTION TRIO : DAVID BINNEY, LOUIS COLE, PERA KRSTAJIC",
        "TANQUA WATER deux troisI",
        "TOMOHIRO MORI NY TRIO featuring ESTEBAN CASTRO & BAR FILIPOWICZ"
    ]
    for artist in test_artists:
        norm_artist = re.sub(r'[\s\W_]+', '', artist.lower())
        matched = next((v for k, v in sorted_map.items() if k in norm_artist), None)
        print(f"Match for {artist}: {matched}")
        
except Exception as e:
    print("CC error:", e)
