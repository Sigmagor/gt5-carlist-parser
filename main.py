import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
from io import StringIO

API = "https://gran-turismo.fandom.com/api.php"
HEADERS = {"User-Agent": "gt5-car-list/1.0 (your-email@example.com)"}

r = requests.get(API, headers=HEADERS, params={
    "action": "parse", "page": "Gran_Turismo_5/Car_List",
    "prop": "text", "format": "json", "formatversion": 2,
})
r.raise_for_status()
soup = BeautifulSoup(r.json()["parse"]["text"], "lxml")

for s in soup.select(".mw-editsection"):
    s.decompose()

session = requests.Session()
session.headers.update(HEADERS)


def get_acquisition(title):
    r = session.get(API, params={
        "action": "parse", "page": title, "prop": "text",
        "redirects": 1, "format": "json", "formatversion": 2,
    }, timeout=30)
    r.raise_for_status()
    page = BeautifulSoup(r.json()["parse"]["text"], "lxml")
    for t in page.find_all("table"):
        heads = {th.get_text(" ", strip=True).lower() for th in t.find_all("th")}
        if "purchase location" not in heads:
            continue
        df = pd.read_html(StringIO(str(t)))[0]
        game = df["Game"].astype(str).str.strip()
        mask = game.str.startswith("Gran Turismo 5") & ~game.str.contains("Prologue")
        df = df[mask]
        if len(df) == 0:
            continue
        row = df.iloc[0]
        break
    return row


def parse_year(y):
    return 2000 + y if y <= 20 else 1900 + y


def parse_title(title: str, raw: str, brand: str):
    model, year, obt = None, None, None

    if title.startswith(brand):
        model = title[len(brand):]
    else:
        model = title

    if title[:2] == "20":
        year = int(title[:4])
    elif title.rfind("'") != -1 and title[title.rfind("'") + 1:title.rfind("'") + 3].isdigit():
        apo_ind = title.rfind("'")
        year = parse_year(int(title[apo_ind + 1:apo_ind + 3]))
        model = model[:model.rfind("'")] + model[model.rfind("'") + 3:]
    model = model.strip()
    obt = True
    if "(DLC)" in raw:
        obt = False
        model += ' (DLC)'
    if "Car no longer obtainable" in raw:
        obt = False

    return model, year, obt


def parse_pl(pl):
    if "---" in pl: return None
    if "Used Car" in pl: return "UCD"
    return "D"


def parse_cr(cr, title):
    cr = str(cr)
    if "---" in cr: return None
    cr = cr.replace("Approx. ", "")
    cr = cr.replace("Appox. ", "")
    cr = cr.replace("or less", "")
    if "." in cr:
        cr = cr.replace(".", "") + "00"
    if "-" in cr:
        cr = cr[cr.index("-") + 1:]
    cr = cr.replace(",", "")
    cr = cr.strip()
    if " " in cr:
        if cr[:cr.index(" ")] == cr[cr.index(" ") + 1:]:
            cr = cr[:cr.index(" ")]
        else:
            cr = cr.replace("(Clio)", "").replace("(Lutecia)", "")
            while "  " in cr: cr = cr.replace("  ", " ").strip()
            if title[:4].lower() == "clio":
                cr = cr[:cr.index(" ")]
            else:
                cr = cr[cr.index(" ") + 1:]
    return int(cr)


def parse_om(om):
    if "---" in om: return None
    om = om.replace(".", " |")
    while "  " in om: om = om.replace("  ", " ")
    return om


def parse_acq(row, title):
    pl = parse_pl(row["Purchase location"])
    cr = parse_cr(row["Credits"], title)
    om = parse_om(row["Other methods"])
    return pl, cr, om


rows = []
errors = []
for table in soup.find_all("table"):
    headers = [th.get_text(strip=True) for th in table.find_all("th")]
    if "Car" not in headers:
        continue
    heading = table.find_previous(["h2", "h3"])
    brand = heading.get_text(strip=True)
    for tr in table.find_all("tr"):
        try:
            td = tr.find("td")
            if td is None:
                continue
            raw = td.get_text(" ", strip=True)
            a = td.find("a", href=True)
            title = a.get("title")

            model, year, obt = parse_title(title, raw, brand)
            pl, cr, om = parse_acq(get_acquisition(title), title)
            time.sleep(0.3)

            rows.append({
                "brand": brand,
                "model": model,
                "year": year,
                "obtainable": obt,
                "dealership": pl,
                "credits": cr,
                "other_methods": om
            })
            print(f"{len(rows)}/1104 {title}")
        except Exception as e:
            print(f"Ошибка {raw}: {e!r}")

print("Parsing complete")
df = pd.DataFrame(rows)
df = df.convert_dtypes()
df.to_csv("gt5_cars.csv", index=False, encoding="utf-8-sig")
df.to_excel("gt5_cars.xlsx", index=False)
