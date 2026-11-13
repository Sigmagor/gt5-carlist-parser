import requests
import time
from bs4 import BeautifulSoup
import pandas as pd
from io import StringIO
import threading
from utility import beautiful_print

API = "https://gran-turismo.fandom.com/api.php"
HEADERS = {"User-Agent": "gt5-car-list/1.0 (your-email@example.com)"}
done = 0
total = 0
done_lock = threading.Lock()
local = threading.local()
pr = []

def get_session():
    if not hasattr(local, "s"):
        local.s = requests.Session()
        local.s.headers.update(HEADERS)
    return local.s


def fetch(params):
    for attempt in range(5):
        try:
            r = get_session().get(API, params=params, timeout=30)
        except requests.RequestException:
            time.sleep(2 * (attempt + 1))
            continue
        if r.status_code == 429 or r.status_code >= 500:
            time.sleep(2 * (attempt + 1))
            continue
        r.raise_for_status()
        return r.json()
    raise RuntimeError(f"429/5xx/сеть: не удалось после 5 попыток")


def fetch_page(title):
    global done
    try:
        data = fetch({
            "action": "parse", "page": title, "prop": "text",
            "redirects": 1, "format": "json", "formatversion": 2,
        })
        res = data["parse"]["text"], None
        time.sleep(0.05)
    except Exception as e:
        res = None, repr(e)
    with done_lock:
        done += 1
        beautiful_print(f"{done}/{total} {title}", pr, 8)
    return res


def get_acquisition(page):
    for t in page.find_all("table"):
        heads = {th.get_text(" ", strip=True).lower() for th in t.find_all("th")}
        if "purchase location" not in heads:
            continue
        df = pd.read_html(StringIO(str(t)))[0]
        game = df["Game"].astype(str).str.strip()
        mask = game.str.startswith("Gran Turismo 5") & ~game.str.contains("Prologue")
        df = df[mask]
        if len(df) > 0: break
    return df.iloc[0]
