import requests
from bs4 import BeautifulSoup

url = "http://www.cottonclubjapan.co.jp/jp/schedule/"
res = requests.get(url)
with open('cc_schedule_dump.html', 'w', encoding='utf-8') as f:
    f.write(res.text)

print("Downloaded Cotton Club schedule.")
