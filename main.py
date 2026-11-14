import os
import pickle
import time
import pandas as pd
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
import fetch as fetch_module
from fetch import fetch, fetch_page, get_acq
from parse import parse_title, parse_acq, parse_infobox
from utility import beautiful_print, enable_ansi_support, is_win10
import json

if is_win10():
    enable_ansi_support()

THREADS = 32

# Парсинг Gran_Turismo_5/Car_List
data = fetch({
    "action": "parse", "page": "Gran_Turismo_5/Car_List",
    "prop": "text", "format": "json", "formatversion": 2,
})
soup = BeautifulSoup(data["parse"]["text"], "lxml")
for s in soup.select(".mw-editsection"):
    s.decompose()

# Список страниц для запросов
print("Creating tasks")
print("\033[32m", end="")
bp = []
cnt = 0
tasks = []
for table in soup.find_all("table"):
    headers = [th.get_text(strip=True) for th in table.find_all("th")]
    if "Car" not in headers:
        continue
    brand = table.find_previous(["h2", "h3"]).get_text(strip=True)
    for tr in table.find_all("tr"):
        td = tr.find("td")
        if td is None:
            continue
        raw = td.get_text(" ", strip=True)
        a = td.find("a", href=True)
        cnt += 1
        beautiful_print(f"{cnt}: {a.get("title")}", bp, 4)
        tasks.append((brand, a.get("title"), raw))

print("\033[0m", end="")
# Многопоточные запросы с кэшированием
titles = [t[1] for t in tasks]
CACHE = "pages.pkl"

if os.path.exists(CACHE):
    with open(CACHE, "rb") as f:
        pages = pickle.load(f)
else:
    pages = [None] * len(tasks)

todo = [i for i, p in enumerate(pages) if p is None or p[1]]
print(f"{len(tasks)} tasks found, {len(todo)} to download")
if len(todo):
    print(f"Downloading pages in {THREADS} threads...")
    print("\033[32m", end="")

fetch_module.total = len(todo)
if todo:
    with ThreadPoolExecutor(max_workers=THREADS) as ex:
        results = list(ex.map(fetch_page, [titles[i] for i in todo]))
    for i, res in zip(todo, results):
        pages[i] = res
    with open(CACHE, "wb") as f:
        pickle.dump(pages, f)

print("\033[0m", end="")
if len(todo) != len(pages):
    print(f"Loaded pages from cache: {len(pages) - len(todo)}")
if len(todo):
    print(f"Downloaded pages from wiki: {len(todo)}")
print(f"Parsing...")
print("\033[32m", end="")
# Обработка страниц
bp = []
rows = []
for i, ((brand, title, raw), (html, err)) in enumerate(zip(tasks, pages), 1):
    try:
        if err:
            raise RuntimeError(err)
        page = BeautifulSoup(html, "lxml")
        for s in page.select(".mw-editsection"):
            s.decompose()
        model, obt = parse_title(title, raw, brand)
        pl, cr, om = parse_acq(get_acq(page), title)
        dct = parse_infobox(page, title)
        rows.append({
            "brand": brand,
            "model": model,
            "obtainable": obt,
            "dealership": pl,
            "credits": cr,
            "other_methods": om,
            # Production Info
            "year": dct["Production Info"]["Year"],
            "type": dct["Production Info"]["Type"],
            "country": dct["Production Info"]["Country"],
            # Engine and Power
            "engine_code": dct["Engine and Power"]["Engine Code"],
            "displacement": dct["Engine and Power"]["Displacement"],
            "engine_type": dct["Engine and Power"]["Engine Type"],
            "aspiration": dct["Engine and Power"]["Aspiration"],
            "power": dct["Engine and Power"]["Power"],
            "torque": dct["Engine and Power"]["Torque"],
            "electric_system": dct["Engine and Power"]["Electric System"],
            # Drivetrain and Weight
            "layout": dct["Drivetrain and Weight"]["Layout"],
            "Drivetrain": dct["Drivetrain and Weight"]["Drivetrain"],
            "Gearbox": dct["Drivetrain and Weight"]["Gearbox"],
            "Weight": dct["Drivetrain and Weight"]["Weight"],
            "Balance": dct["Drivetrain and Weight"]["Balance"],
            # Performance
            "0-60_time": dct["Performance"]["0-60 Time"],
            "Top Speed": dct["Performance"]["Top Speed"],
            "Weight-to-Power Ratio": dct["Performance"]["Weight-to-Power Ratio"],
            "PP in GT5/6": dct["Performance"]["PP in GT5/6"],
            "Class": dct["Performance"]["Class"],
            # Dimensions
            "Length": dct["Dimensions"]["Length"],
            "Width": dct["Dimensions"]["Width"],
            "Height": dct["Dimensions"]["Height"],
            # Miscellaneous
            "GT5 Type": dct["Miscellaneous"]["GT5 Type"]
        })
        beautiful_print(f"{i}/{len(tasks)} {title}", bp, 4)
    except Exception as e:
        print(f"{i}/{len(tasks)} Ошибка {raw}: {e!r}")
        bp = []
print("\033[0m", end="")
# Сохранение
print("Parsing complete")
df = pd.DataFrame(rows)
df["obtained"] = None
df = df.convert_dtypes()
print(f"Total rows: {len(df)}")
print("How to save: csv/xlsx/both? (1/2/3)")
a = input()
while a not in ("1", "2", "3", "279936"):
    print("Incorrect input! Try again")
    a = input()
if a == "1" or a == "3" or a == "279936":
    df.to_csv("gt5cars.csv", index=False, encoding="utf-8-sig")
    print("Saved as gt5cars.csv")
if a == "2" or a == "3" or a == "279936":
    df.to_excel("gt5cars.xlsx", index=False)
    print("Saved as gt5cars.xlsx")
if a != "279936":
    print("Removing cache...")
    os.remove(CACHE)
    print("Removed cache")
for i in range(5, 0, -1):
    print(f"\rClosing in {i} seconds...", end="")
    time.sleep(1)
