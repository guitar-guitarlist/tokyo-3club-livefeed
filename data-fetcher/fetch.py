import json
import os
import re
import hashlib
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup

def download_image(url, images_dir, page_referer=""):
    """Download image and save locally. Returns relative path or empty string."""
    if not url:
        return ""
    try:
        ext = url.split('?')[0].rsplit('.', 1)[-1].lower()
        if ext not in ('jpg', 'jpeg', 'png', 'gif', 'webp'):
            ext = 'jpg'
        filename = hashlib.md5(url.encode()).hexdigest() + '.' + ext
        filepath = os.path.join(images_dir, filename)
        if not os.path.exists(filepath):
            # Use the page's domain as Referer, not the image URL
            from urllib.parse import urlparse
            parsed = urlparse(url)
            referer = page_referer or f"{parsed.scheme}://{parsed.netloc}/"
            h = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': referer,
                'Accept': 'image/avif,image/webp,image/apng,image/*,*/*;q=0.8',
            }
            res = requests.get(url, headers=h, timeout=10)
            content_type = res.headers.get('Content-Type', '')
            if res.status_code == 200 and 'image' in content_type and len(res.content) > 1000:
                with open(filepath, 'wb') as f:
                    f.write(res.content)
            else:
                print(f"  Skipped (status={res.status_code}, type={content_type}): {url}")
                return ""
        return f"images/{filename}"
    except Exception as e:
        print(f"Image download failed ({url}): {e}")
        return ""

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
def _clean_title(raw):
    """Strip HTML tags (e.g. <br/>) from an event title and collapse whitespace."""
    if not raw:
        return ""
    text = BeautifulSoup(raw, "html.parser").get_text(" ")
    return re.sub(r'\s+', ' ', text).strip()


def fetch_reserve_schedule(reserve_base, label):
    """Fetch schedule from the (redesigned) shared reserve system used by
    Blue Note Tokyo and Cotton Club.

    The schedule pages are server-rendered list views; each event card links
    to /reserve/schedule/exec/<event_id>, and full details (dates, stage
    times, images, artist page URL) are available as JSON from
    /reserve/schedule/read_event_info/<event_id>.
    """
    print(f"Fetching {label}...")
    schedule_dict = {}
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

    # 1. Determine the current month from the redirect target of the top page
    res = requests.get(f"{reserve_base}/reserve/schedule/", headers=headers, timeout=30)
    res.raise_for_status()
    m = re.search(r'/move/(\d{4})(\d{2})', res.url)
    if not m:
        raise RuntimeError(f"{label}: could not determine current month from {res.url}")
    cur_y, cur_m = int(m.group(1)), int(m.group(2))

    # 2. Collect unique event IDs from this month and the next 3 months
    event_ids = []
    seen = set()
    y, mo = cur_y, cur_m
    for _ in range(4):
        url = f"{reserve_base}/reserve/schedule/move/{y}{mo:02d}/"
        r = requests.get(url, headers=headers, timeout=30)
        r.raise_for_status()
        soup = BeautifulSoup(r.content, "html.parser")
        for card in soup.select(".c-schedule-list-card"):
            href = card.get("href", "")
            mm = re.search(r'/exec/(\d+)', href)
            if mm and mm.group(1) not in seen:
                seen.add(mm.group(1))
                event_ids.append(mm.group(1))
        mo += 1
        if mo > 12:
            mo = 1
            y += 1

    if not event_ids:
        raise RuntimeError(f"{label}: no events found on schedule pages (site structure may have changed)")

    # 3. Fetch each event's details as JSON
    for event_id in event_ids:
        info_url = f"{reserve_base}/reserve/schedule/read_event_info/{event_id}"
        r = requests.get(info_url, headers=headers, timeout=30)
        r.raise_for_status()
        info = json.loads(r.text)

        titles = info.get("basic_info", {}).get("titles", {})
        artist = _clean_title(titles.get("en_title") or titles.get("jp_title"))
        if not artist:
            continue

        img = info.get("basic_info", {}).get("thumbnail_url", "") or ""
        if img.startswith("/"):
            img = reserve_base + img

        links = info.get("links", {})
        event_url = links.get("detail_page_url") or links.get("reservation_action_url") or ""

        for day in info.get("schedule_list", []):
            date_str = day.get("date_iso")
            if not date_str:
                continue
            times = []
            for stage in day.get("stages", []):
                st = stage.get("start_time")
                if st:
                    label_txt = stage.get("label") or f"{stage.get('stage_no', '')}"
                    times.append(f"{label_txt}: {st}")
            schedule_dict[date_str] = {
                "artist": artist,
                "time": " / ".join(times),
                "img": img,
                "url": event_url
            }

    return schedule_dict


def fetch_bluenote():
    return fetch_reserve_schedule("https://reserve.bluenote.co.jp", "Blue Note Tokyo")


def fetch_billboard():
    print("Fetching Billboard Live Tokyo...")
    schedule_dict = {}

    target_year = datetime.now().year
    today = datetime.now().strftime('%Y-%m-%d')

    # The API token (JWT) is short-lived (~24h), so fetch a fresh one the
    # same way the official website does instead of hard-coding it.
    def get_fresh_token():
        r = requests.post(
            "https://www.billboard-live.com/api-proxy/auth/getencoded",
            json={'public': 1080},  # 1080 = Billboard Live TOKYO facility id
            timeout=30
        )
        r.raise_for_status()
        token = r.json().get('encode')
        if not token:
            raise RuntimeError("Billboard: token endpoint returned no token")
        return token

    url = "https://www.billboard-live.com/api-front/v4/get_all_calendar_schedules"
    data = {
        'start_date': today,
        'locations': ['tokyo'],
        'response_type': 1,
        'days': 90
    }

    json_data = None
    for attempt in range(2):
        token = get_fresh_token()
        res = requests.post(url, headers={'Content-Type': 'application/json', 'Authorization': token},
                            json=data, timeout=30)
        if res.status_code in (401, 403) and attempt == 0:
            print("Billboard: token rejected, retrying with a fresh token...")
            continue
        res.raise_for_status()
        json_data = res.json()
        break

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

                    event_id = first_session.get("event_id")

                    img = ""
                    images = first_session.get("images", [])
                    if images:
                        img_name = images[0].get("image_name", "")
                        for img_item in images:
                            if img_item.get("image_type") == 2:
                                img_name = img_item.get("image_name")
                                break
                        if img_name and event_id:
                            folder = img_name.split("_")[0]
                            img = f"https://www.billboard-live.com/public/event_img/{event_id}/{folder}/{img_name}"

                    bb_url_base = "https://www.billboard-live.com/tokyo/schedules"

                    for original_date in dates:
                        date_str = f"{target_year}-{original_date[5:]}"
                        if date_str < today:
                            # Dates past New Year belong to next year
                            date_str = f"{target_year + 1}-{original_date[5:]}"

                        bb_url = bb_url_base
                        if event_id:
                            bb_url = f"https://www.billboard-live.com/tokyo/show?event_id={event_id}&date={date_str}"
                        schedule_dict[date_str] = {
                            "artist": artist,
                            "time": time_str,
                            "img": img,
                            "url": bb_url
                        }

    if not schedule_dict:
        raise RuntimeError("Billboard: API returned no schedule (token or API may have changed)")
    return schedule_dict


def fetch_cottonclub():
    return fetch_reserve_schedule("https://reserve.cottonclubjapan.co.jp", "Cotton Club")


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

    total_days = len(bn_data) + len(bb_data) + len(cc_data)
    if total_days == 0:
        raise SystemExit("ERROR: all venues returned no data; refusing to overwrite schedule.json")

    for venue_name, venue_data in (("Blue Note", bn_data), ("Billboard", bb_data), ("Cotton Club", cc_data)):
        if not venue_data:
            print(f"WARNING: {venue_name} returned no data this run")

    # Download images
    images_dir = os.path.join(os.path.dirname(__file__), '..', 'images')
    os.makedirs(images_dir, exist_ok=True)
    print("Downloading images...")
    referer_map = [
        (bn_data, "https://www.bluenote.co.jp/jp/"),
        (bb_data, "https://www.billboard-live.com/tokyo/schedules"),
        (cc_data, "https://www.cottonclubjapan.co.jp/jp/schedule/"),
    ]
    url_cache = {}  # original URL -> local path (avoids re-downloading shared/multi-day events)
    for data_dict, referer in referer_map:
        for event in data_dict.values():
            if not (event and event.get('img')):
                continue
            src = event['img']
            # Skip values that are already local paths (multi-day events share one dict)
            if not src.startswith('http'):
                continue
            if src in url_cache:
                event['img'] = url_cache[src]
                continue
            local_path = download_image(src, images_dir, page_referer=referer)
            url_cache[src] = local_path
            event['img'] = local_path
    print("Images downloaded.")
    
    output_path = os.path.join(os.path.dirname(__file__), '..', 'schedule.json')
    history_map = {}
    if os.path.exists(output_path):
        try:
            with open(output_path, 'r', encoding='utf-8') as f:
                old_data = json.load(f)
                for day in old_data:
                    d_str = day['date'][:10]
                    for venue in ['bluenote', 'billboard', 'cotton']:
                        if day.get(venue) and day[venue].get('artist'):
                            key = f"{d_str}_{venue}_{day[venue]['artist']}"
                            history_map[key] = day[venue].get('first_seen')
        except Exception as e:
            print("Could not load history:", e)
            
    # マージするためにすべてのユニークな日付を取得
    all_dates = set(bn_data.keys()) | set(bb_data.keys()) | set(cc_data.keys())
    
    # 取得した日付をすべてソート（過去日も含める。月末でデータが空になるのを防ぐため）
    sorted_dates = sorted(list(all_dates))
    
    final_data = []
    today_str = datetime.now().strftime('%Y-%m-%d')
    
    # 全未来日分を出力
    for date_str in sorted_dates:
        js_date_str = f"{date_str}T00:00:00.000Z"
        day_output = {"date": js_date_str}
        
        for venue_code, venue_data_dict in [('bluenote', bn_data), ('billboard', bb_data), ('cotton', cc_data)]:
            event = venue_data_dict.get(date_str)
            if event and event.get('artist'):
                key = f"{date_str}_{venue_code}_{event['artist']}"
                first_seen = history_map.get(key)
                if not first_seen:
                    first_seen = today_str
                event['first_seen'] = first_seen
            day_output[venue_code] = event
            
        final_data.append(day_output)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)
        
    print(f"Data saved to {output_path}")

if __name__ == "__main__":
    main()
