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


def beautiful_print(s, pr, window):
    if len(pr) < window:
        print(s + "\033[K", flush=True)
    else:
        print(f"\033[{window}A", flush=True, end="")
        del pr[0]
        pr.append(s + "\033[K")
        print(*pr, flush=True, sep="\n")
