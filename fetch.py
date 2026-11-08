import requests
import time
from bs4 import BeautifulSoup
import pandas as pd
from io import StringIO
import threading

API = "https://gran-turismo.fandom.com/api.php"
HEADERS = {"User-Agent": "gt5-car-list/1.0 (your-email@example.com)"}
done = 0
done_lock = threading.Lock()

def fetch(params):
    for attempt in range(5):
        r = requests.get(API, headers=HEADERS, params=params, timeout=30)
        if r.status_code == 429:
            time.sleep(2 * (attempt + 1))
            continue
        r.raise_for_status()
        return r.json()
    raise RuntimeError("429")


def fetch_page(title):
    global done
    try:
        data = fetch({
            "action": "parse", "page": title, "prop": "text",
            "redirects": 1, "format": "json", "formatversion": 2,
        })
        time.sleep(0.5)
        res = data["parse"]["text"], None
    except Exception as e:
        res = None, e
    with done_lock:
        done += 1
        print(f"Скачано {done}", end="\r")
    return res

def get_acquisition(html):
    page = BeautifulSoup(html, "lxml")
    for s in page.select(".mw-editsection"):
        s.decompose()
    for t in page.find_all("table"):
        heads = {th.get_text(" ", strip=True).lower() for th in t.find_all("th")}
        if "purchase location" not in heads:
            continue
        df = pd.read_html(StringIO(str(t)))[0]
        game = df["Game"].astype(str).str.strip()
        mask = game.str.startswith("Gran Turismo 5") & ~game.str.contains("Prologue")
        df = df[mask]
        if len(df) > 0: return df.iloc[0]
    raise ValueError("таблица GT5 не найдена")
