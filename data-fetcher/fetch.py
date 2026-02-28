import json
import os
import re
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup

def get_url_map(is_bn):
    url_map = {}
    h = {'User-Agent': 'Mozilla/5.0'}
    base_url = 'https://www.bluenote.co.jp/jp/' if is_bn else 'https://www.cottonclubjapan.co.jp/jp/'
    paths = ['']
    if is_bn:
        paths.append('artists/')
    else:
        paths.append('schedule/')
        
    try:
        for p in paths:
            u = base_url + p
            res = requests.get(u, headers=h, timeout=10)
            res.encoding = 'utf-8'
            soup = BeautifulSoup(res.text, 'html.parser')
            target_paths = ['/artists/', '/event/', '/sp/artists/']
            for a in soup.find_all('a', href=True):
                href = a['href']
                if any(tp in href for tp in target_paths):
                    parts = [x for x in href.split('/') if x]
                    if not parts: continue
                    slug = parts[-1]
                    slug_no_date = re.sub(r'-\d+$', '', slug)
                    norm = re.sub(r'[\s\W_]+', '', slug_no_date.lower())
                    
                    full_url = href
                    if full_url.startswith('/'):
                        # Cotton Club uses http/https mixed, be safe
                        domain = 'https://www.bluenote.co.jp' if is_bn else 'https://www.cottonclubjapan.co.jp'
                        full_url = domain + full_url
                        
                    if norm and len(norm) > 3:
                        url_map[norm] = full_url
    except Exception as e:
        print(f"Error getting url map for {'BN' if is_bn else 'CC'}: {e}")
        
    # Sort keys by length descending to match the longest (most specific) slug first
    sorted_map = {k: url_map[k] for k in sorted(url_map.keys(), key=len, reverse=True)}
    return sorted_map

# 各サイト用のスクレイピング関数（仮実装、後ほど詳細化）
def fetch_bluenote():
    print("Fetching Blue Note Tokyo...")
    schedule_dict = {}
    current_time = "1st: 17:00 / 2nd: 20:00"
    target_year = datetime.now().year
    url_map = get_url_map(True)
    
    # 1. Fetch base URL to get actual current month
    url_base = "https://reserve.bluenote.co.jp/reserve/schedule/"
    res = requests.get(url_base)
    soup = BeautifulSoup(res.content, "html.parser")
    
    year_month_elem = soup.select_one(".thisMonth")
    if not year_month_elem:
        return schedule_dict
        
    real_y = int(year_month_elem.select_one(".year").text.strip())
    real_m = int(year_month_elem.select_one(".month").text.strip())
    
    # 2. Compute next 2 months based on real month
    next_m = real_m + 1 if real_m < 12 else 1
    next_y = real_y if real_m < 12 else real_y + 1
    
    m3 = next_m + 1 if next_m < 12 else 1
    y3 = next_y if next_m < 12 else next_y + 1
    
    urls_to_fetch = [
        url_base,
        f"https://reserve.bluenote.co.jp/reserve/schedule/move/{next_y}{next_m:02d}/",
        f"https://reserve.bluenote.co.jp/reserve/schedule/move/{y3}{m3:02d}/"
    ]
    
    for url in urls_to_fetch:
        if url != url_base:
            res = requests.get(url)
            soup = BeautifulSoup(res.content, "html.parser")
            year_month_elem = soup.select_one(".thisMonth")
            if not year_month_elem:
                continue
                
        month = year_month_elem.select_one(".month").text.strip()
        year = target_year
        
        for table in soup.select("table"):
            current_event = None
            for tr in table.select("tr"):
                schedule_box = tr.select_one(".scheduleBox")
                if schedule_box:
                    title_elem = schedule_box.select_one(".title")
                    img_elem = schedule_box.select_one("img")
                    
                    if title_elem:
                        current_artist = title_elem.text.strip()
                        img_src = img_elem["src"] if img_elem else ""
                        if img_src.startswith("/"):
                            img_src = "https://www.bluenote.co.jp" + img_src
                        
                        
                        current_url = f"https://reserve.bluenote.co.jp/reserve/schedule/move/{target_year}{int(month):02d}"
                        
                        # 名寄せ処理：抽出したスラッグのキーが公演名に含まれているか長い順に部分一致チェック
                        norm_artist = re.sub(r'[\s\W_]+', '', current_artist.lower())
                        matched = next((v for k, v in url_map.items() if k in norm_artist), None)
                        if matched:
                            current_url = matched

                        current_event = {
                            "artist": current_artist,
                            "time": current_time,
                            "img": img_src,
                            "url": current_url
                        }
                
                day_box = tr.select_one(".dayBox .day")
                if not day_box:
                    continue
                day = day_box.text.strip()
                date_str = f"{year}-{int(month):02d}-{int(day):02d}"
                
                if current_event:
                    schedule_dict[date_str] = current_event
    
    return schedule_dict

def fetch_billboard():
    print("Fetching Billboard Live Tokyo...")
    schedule_dict = {}
    import urllib.request
    
    target_year = datetime.now().year
    today = datetime.now().strftime('%Y-%m-%d')
    
    url = "https://www.billboard-live.com/api-front/v4/get_all_calendar_schedules"
    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhcGlrZXkiOiIzOTZlY2FjNGRkYTMyMmFmZWQ1Y2E4ZTUyMDU0MTQ3NyIsImNvbXBhbnlpZCI6MTA4MCwiZmFjaWxpdHlpZCI6MTA4MH0.h8o54w7xunscV2PX4gdGOzIM5gMisRiZwlpqchSqAMA'
    }
    data = {
        'start_date': today,
        'locations': ['tokyo'],
        'response_type': 1,
        'days': 90
    }
    
    try:
        res = requests.post(url, headers=headers, json=data, timeout=10)
        json_data = res.json()
        
        loc_schedules = json_data.get("location_schedules", [])
        for loc_data in loc_schedules:
            if loc_data.get("location") == "tokyo":
                for item in loc_data.get("schedules", []):
                    dates = item.get("dates", [])
                    events = item.get("schedules", [])
                    if dates and events and len(events) > 0 and len(events[0]) > 0:
                        first_session = events[0][0]
                        
                        artist = first_session.get("title_name")
                        if not artist:
                            artist = " / ".join([n for n in first_session.get("event_names", []) if n])
                            
                        times = []
                        for session in events[0]:
                            if session.get("play_start"):
                                times.append(session.get("play_start"))
                        time_str = " / ".join(times) if times else ""
                        
                        img = ""
                        images = first_session.get("images", [])
                        if images:
                            img_name = images[0].get("image_name", "")
                            for img_item in images:
                                if img_item.get("image_type") == 2:
                                    img_name = img_item.get("image_name")
                                    break
                            if img_name:
                                img = f"https://www.billboard-live.com/assets/images/shows/{img_name}"
                        
                        
                        bb_url_base = "https://www.billboard-live.com/tokyo/schedules"
                        event_id = first_session.get("event_id")
                                
                        for original_date in dates:
                            date_str = f"{target_year}-{original_date[5:]}"
                            
                            bb_url = bb_url_base
                            if event_id:
                                bb_url = f"https://www.billboard-live.com/tokyo/show?event_id={event_id}&date={date_str}"
                            schedule_dict[date_str] = {
                                "artist": artist,
                                "time": time_str,
                                "img": img,
                                "url": bb_url
                            }
    except Exception as e:
        print(f"Billboard parse error: {e}")
            
    return schedule_dict

def fetch_cottonclub():
    print("Fetching Cotton Club...")
    schedule_dict = {}
    current_time = "1st: 18:00 / 2nd: 20:30"
    target_year = datetime.now().year
    
    url_base = "https://www.cottonclubjapan.co.jp/jp/schedule/"
    try:
        res = requests.get(url_base)
        soup = BeautifulSoup(res.content, "html.parser")
        
        month_elem = soup.select_one(".monthNavAreaInner .thisMonth")
        if not month_elem:
            return schedule_dict
            
        real_y = int(month_elem.select_one(".year").text.strip())
        real_m = int(month_elem.select_one(".month").text.strip())
        
        next_m = real_m + 1 if real_m < 12 else 1
        next_y = real_y if real_m < 12 else real_y + 1
        
        m3 = next_m + 1 if next_m < 12 else 1
        y3 = next_y if next_m < 12 else next_y + 1
        
        # 1. Build image to URL map from the main site schedules
        img_to_url = {}
        schedule_pages = [
            url_base,
            f"https://www.cottonclubjapan.co.jp/jp/schedule/{next_y}{next_m:02d}/",
            f"https://www.cottonclubjapan.co.jp/jp/schedule/{y3}{m3:02d}/"
        ]
        for url in schedule_pages:
            try:
                r = requests.get(url, timeout=10)
                r.encoding = 'utf-8'
                s = BeautifulSoup(r.text, 'html.parser')
                spans = s.select('span.twoColumnsType')
                for i in range(len(spans)):
                    img = spans[i].select_one('.columnImg img')
                    if img and img.has_attr('src'):
                        if i + 1 < len(spans):
                            a = spans[i+1].select_one('.btnBox a')
                            if a and a.has_attr('href'):
                                img_id = img['src'].split('/')[-1].split('.')[0]
                                img_to_url[img_id] = a['href']
            except Exception as e:
                print(f"Error fetching CC map from {url}: {e}")
        
        # 2. Extract Top Page links to match future Japanese artists by date ('-260302') or slug
        cc_url_map = {}
        top_url = "https://www.cottonclubjapan.co.jp/jp/"
        try:
            r = requests.get(top_url, timeout=10)
            r.encoding = 'utf-8'
            s = BeautifulSoup(r.text, 'html.parser')
            for a in s.find_all('a', href=True):
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
                        
                    # 2-A: Map by YMD suffix if present
                    m_date = re.search(r'-(\d{6})$', slug)
                    if m_date:
                        ymd = m_date.group(1) # '260302'
                        cc_url_map[f"date_{ymd}"] = full_url
                        
                    # 2-B: Map by norm artist name
                    if norm and len(norm) > 3:
                        cc_url_map[norm] = full_url
        except Exception as e:
            print("Error fetching CC top page map:", e)
        
        # Sort keys for name matching
        sorted_cc_map = {k: cc_url_map[k] for k in sorted(cc_url_map.keys(), key=len, reverse=True)}
        
        # 3. Fetch the calendar data from reserve site
        urls_to_fetch = [
            f"https://reserve.cottonclubjapan.co.jp/reserve/schedule/move/{real_y}{real_m:02d}/",
            f"https://reserve.cottonclubjapan.co.jp/reserve/schedule/move/{next_y}{next_m:02d}/",
            f"https://reserve.cottonclubjapan.co.jp/reserve/schedule/move/{y3}{m3:02d}/"
        ]
        
        for url in urls_to_fetch:
            if url != url_base:
                res = requests.get(url)
                soup = BeautifulSoup(res.content, "html.parser")
                month_elem = soup.select_one(".monthNavAreaInner .thisMonth")
                if not month_elem:
                    continue
            
            year = target_year
            month = month_elem.select_one(".month").text.strip()
            
            for table in soup.select("table"):
                trs = table.select("tr")
                if not trs:
                    continue
                    
                first_tr = trs[0]
                schedule_box = first_tr.select_one(".scheduleBox")
                
                artist = None
                img = None
                
                if schedule_box:
                    if "PRIVATE" in schedule_box.text:
                        artist = "PRIVATE"
                    else:
                        title_elem = schedule_box.select_one(".title")
                        if title_elem:
                            artist = title_elem.text.strip().replace('\n', ' ').replace('\r', '')
                        img_elem = schedule_box.select_one(".columnImg img")
                        if img_elem and img_elem.has_attr("src"):
                            img_src = img_elem["src"]
                            if img_src.startswith("/"):
                                img_src = "https://www.cottonclubjapan.co.jp" + img_src
                            img = img_src
                
                for tr in trs:
                    day_elem = tr.select_one(".dayBox .day")
                    if day_elem and artist:
                        day = day_elem.text.strip()
                        date_str = f"{year}-{int(month):02d}-{int(day):02d}"
                        slug_ymd = f"{str(year)[-2:]}{int(month):02d}{int(day):02d}"  # '260302'
                        
                        current_url = f"https://reserve.cottonclubjapan.co.jp/reserve/schedule/move/{year}{int(month):02d}"
                        
                        # A) Match by Img ID (Best for current month, handles Japanese)
                        if img:
                            img_id = img.split('/')[-1].split('.')[0]
                            if img_id in img_to_url:
                                current_url = img_to_url[img_id]
                                
                        # B) Match by URL date suffix (Best for future Japanese artists)
                        if "reserve.cottonclubjapan.co.jp" in current_url:
                            if f"date_{slug_ymd}" in sorted_cc_map:
                                current_url = sorted_cc_map[f"date_{slug_ymd}"]
                                
                        # C) Match by norm string (Fallback for English future artists)
                        if "reserve.cottonclubjapan.co.jp" in current_url:
                            norm_artist = re.sub(r'[\s\W_]+', '', artist.lower())
                            matched = next((v for k, v in sorted_cc_map.items() if not k.startswith("date_") and k in norm_artist), None)
                            if matched:
                                current_url = matched
                                
                        schedule_dict[date_str] = {
                            "artist": artist,
                            "time": current_time,
                            "img": img or "",
                            "url": current_url
                        }
    except Exception as e:
        print(f"Cotton Club parse error: {e}")
            
    return schedule_dict

def generate_mock_data():
    """
    スクレイピングが失敗した場合のフォールバック用
    """
    data = []
    today = datetime.now()
    
    artists_bn = ["Marcus Miller", "Hiromi Uehara", "Snarky Puppy", "Kamasi Washington", None, "Robert Glasper", "Pat Metheny"]
    artists_bb = ["MISIA", None, "Chara", "Incognito", "Carly Rae Jepsen", "Mayer Hawthorne", None]
    artists_cc = [None, "Takuya Kuroda", "Christian McBride", "José James", "Kiefer", None, "Moonchild"]

    for i in range(7):
        d = today + timedelta(days=i)
        date_str = d.strftime("%Y-%m-%dT00:00:00.000Z") # format like JS Date JSON
        
        data.append({
            "date": date_str,
            "bluenote": {
                "artist": artists_bn[i],
                "time": "1st: 17:00 / 2nd: 20:00",
                "img": f"https://picsum.photos/seed/bn{i}/300/200"
            } if artists_bn[i] else None,
            "billboard": {
                "artist": artists_bb[i],
                "time": "1st: 16:30 / 2nd: 19:30",
                "img": f"https://picsum.photos/seed/bb{i}/300/200"
            } if artists_bb[i] else None,
            "cotton": {
                "artist": artists_cc[i],
                "time": "1st: 18:00 / 2nd: 20:30",
                "img": f"https://picsum.photos/seed/cc{i}/300/200"
            } if artists_cc[i] else None
        })
    return data

def main():
    print("Starting data fetch...")
    
    bn_data = fetch_bluenote()
    print(f"Fetched {len(bn_data)} days from Blue Note Tokyo.")
    
    bb_data = fetch_billboard()
    print(f"Fetched {len(bb_data)} days from Billboard Live Tokyo.")
    
    cc_data = fetch_cottonclub()
    print(f"Fetched {len(cc_data)} days from Cotton Club.")
    
    # マージするためにすべてのユニークな日付を取得
    all_dates = set(bn_data.keys()) | set(bb_data.keys()) | set(cc_data.keys())
    
    # 取得した日付をすべてソート（過去日も含める。月末でデータが空になるのを防ぐため）
    sorted_dates = sorted(list(all_dates))
    
    final_data = []
    
    # 全未来日分を出力
    for date_str in sorted_dates:
        js_date_str = f"{date_str}T00:00:00.000Z"
        
        final_data.append({
            "date": js_date_str,
            "bluenote": bn_data.get(date_str),
            "billboard": bb_data.get(date_str),
            "cotton": cc_data.get(date_str)
        })
    
    output_path = os.path.join(os.path.dirname(__file__), '..', 'schedule.json')
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)
        
    print(f"Data saved to {output_path}")

if __name__ == "__main__":
    main()
