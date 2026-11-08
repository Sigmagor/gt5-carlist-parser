import re
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
from io import StringIO
from urllib.parse import unquote

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


def parse_car_title(title):
    if "Lv" in title:
        text = title[:title.find("Lv") - 1].strip()
    else:
        text = title

    if text.startswith("2010") or text.startswith("2011"):
        year = int(text[:4])
    elif text.rfind("'") != -1 and text[text.rfind("'") + 1:text.rfind("'") + 3].isdigit():
        apo_ind = text.rfind("'")
        year = parse_year(text[apo_ind + 1:apo_ind + 3])
        text = text[:apo_ind] + text[apo_ind + 3:]
        while "  " in text: text = text.replace("  ", " ")
        text = text.strip()
    else:
        year = None

    if text.startswith(brand):
        model = text[len(brand):].strip()
    else:
        model = text

    obt = True
    if "(DLC)" in title or "Car no longer obtainable" in title:
        obt = False
        model = model.replace("Car no longer obtainable.", "")

    return model, year, obt


def parse_cr(cr):
    cr = str(cr)
    if "Approx" in cr or "Appox" in cr:
        cr = cr.replace("Approx. ", "")
        cr = cr.replace("Appox. ", "")
    if "or less" in cr:
        cr = cr.replace("or less", "").strip()
    if "." in cr:
        cr = cr.replace(".", "") + "00"
    cr = cr.replace(",", "")
    return int(cr)


def parse_year(y):
    y = int(y)
    return 2000 + y if y <= 20 else 1900 + y


def parse_acq(row):
    dct = {"ds": None, "ucds": None, "om": None}
    if row["Other methods"] != "---":
        dct["om"] = row["Other methods"]
    if row["Purchase location"] != "---":
        pl = row["Purchase location"]
        cr = parse_cr(row["Credits"])
        if "Lv" in pl:
            pl = pl[:pl.index("Lv") - 1].strip()
        if pl == "Used Car Dealership":
            dct["ucds"] = cr
        else:
            dct["ds"] = cr
    return dct


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
        if {"game", "purchase location"} <= heads:
            df = pd.read_html(StringIO(str(t)))[0]
            game = df["Game"].astype(str).str.strip()
            mask = game.str.startswith("Gran Turismo 5") & ~game.str.contains("Prologue")
            row = df[mask].iloc[0]
    # print(row, "\n----------------------------------------")
    return row


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
            model, year, obt = parse_car_title(raw)

            a = td.find("a", href=True)
            title = unquote(a["href"][len("/wiki/"):]).replace("_", " ") if a else None
            acq = {"purchase_location": None, "credits": None, "other_methods": None}
            if title:
                acq = parse_acq(get_acquisition(title))
                time.sleep(0.3)
            else:
                print(title)
                break

            rows.append({
                "brand": brand,
                "model": model,
                "year": year,
                "obtainable": obt,
                "dealership": acq["ds"],
                "uc_dealership": acq["ucds"],
                "other_methods": acq["om"]
            })
            print(f"{len(rows)}/1104")
        except Exception as e:
            print(f"Ошибка {raw}: {e!r}")
            errors.append([raw, e])

    # if len(rows) >= 40:
    #     break

df = pd.DataFrame(rows)
df["year"] = df["year"].astype("Int64")
df["dealership"] = df["dealership"].astype("Int64")
df["uc_dealership"] = df["uc_dealership"].astype("Int64")
print(len(df))
print(errors.__len__())
print(*errors, sep="\n")
df.to_csv("gt5_cars.csv", index=False, encoding="utf-8-sig")
