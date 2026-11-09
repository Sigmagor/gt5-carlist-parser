import os
import pickle
import pandas as pd
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
import fetch as fetch_module
from fetch import fetch, fetch_page, get_acquisition
from parse import parse_title, parse_acq, beautiful_print

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
        if a is None or not a.get("title"):
            print(f"Skip: {raw}")
            continue
        tasks.append((brand, a.get("title"), raw))

# Многопоточные запросы с кэшированием
titles = [t[1] for t in tasks]
CACHE = "pages.pkl"

if os.path.exists(CACHE):
    with open(CACHE, "rb") as f:
        pages = pickle.load(f)
else:
    pages = [None] * len(tasks)

todo = [i for i, p in enumerate(pages) if p is None or p[1] is not None]
print(f"{len(tasks)} tasks found, {len(todo)} to download")
if len(todo):
    print(f"Downloading pages in {THREADS} threads...")

fetch_module.total = len(todo)
if todo:
    with ThreadPoolExecutor(max_workers=THREADS) as ex:
        results = list(ex.map(fetch_page, [titles[i] for i in todo]))
    for i, res in zip(todo, results):
        pages[i] = res
    with open(CACHE, "wb") as f:
        pickle.dump(pages, f)

if len(todo) != len(pages):
    print(f"Loaded pages from cache: {len(pages) - len(todo)}")
if len(todo):
    print(f"Downloaded pages from wiki: {len(todo)}")
print(f"Parsing...")
pr = []
# Обработка страниц
rows = []
for i, ((brand, title, raw), (html, err)) in enumerate(zip(tasks, pages), 1):
    try:
        if err:
            raise RuntimeError(err)
        model, year, obt = parse_title(title, raw, brand)
        pl, cr, om = parse_acq(get_acquisition(html), title)
        rows.append({
            "brand": brand,
            "model": model,
            "year": year,
            "obtainable": obt,
            "dealership": pl,
            "credits": cr,
            "other_methods": om,
        })
        beautiful_print(f"{i}/{len(tasks)} {title}", pr, 8)
    except Exception as e:
        print(f"{i}/{len(tasks)} Ошибка {raw}: {e!r}\n")
        pr = []

print("Parsing complete")

# Сохранение
df = pd.DataFrame(rows).convert_dtypes()
print(f"Total rows: {len(df)}")
print("How to save: csv/xlsx/both? (1/2/3)")
a = input()
while a not in ("1", "2", "3", "1488"):
    print("Incorrect input! Try again")
    a = input()
if a == "1" or a == "3" or a == "1488":
    df.to_csv("gt5cars.csv", index=False, encoding="utf-8-sig")
    print("Saved as gt5cars.csv")
if a == "2" or a == "3" or a == "1488":
    df.to_excel("gt5cars.xlsx", index=False)
    print("Saved as gt5cars.xlsx")
if a != "1488":
    os.remove(CACHE)