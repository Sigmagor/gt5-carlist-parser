def clean(text: str) -> str:
    return " ".join(text.replace("\xa0", " ").split())


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


def parse_prod(fields: dict) -> dict:
    line = list(fields.values())[0].strip().split()
    car_ind = line.index("Car")
    car_type = line[car_ind - 1]
    if car_ind != len(line) - 1:
        country = " ".join(line[car_ind + 1:])
    else:
        country = None
    if line[car_ind - 2].isdigit():
        year = int(line[car_ind - 2])
    else:
        year = None
    return {
        "Year": year,
        "Type": car_type,
        "Country": country
    }


def parse_engine(fields: dict) -> dict:
    if "Engine Code" in fields:
        line = fields["Engine Code"]
        line = clean(line.replace("[ 1 ]", "").strip())
        fields["Engine Code"] = line
    else:
        fields["Engine Code"] = None
    if "Displacement" in fields:
        line = fields["Displacement"]
        line = clean(line.replace("[ 1 ]", "").replace("[ 2 ]", "").strip())
        if "L" in line:
            line = float(line.replace("L", "").strip())
        elif "×" in line:
            line = clean(line.replace("cc", "").replace("×", "").strip())
            line = list(map(int, line.split()))
            line = (line[0] * line[1]) / 1000
        elif "cc" in line:
            line = int(line.replace("cc", "").replace(",", "").strip()) / 1000
        fields["Displacement"] = line
    else:
        fields["Displacement"] = None
    if "Engine Type" in fields:
        line = fields["Engine Type"]
        line = clean(line.replace("[ 1 ]", "").strip())
        fields["Engine Type"] = line
    else:
        fields["Engine Type"] = None
    if "Aspiration" not in fields:
        fields["Aspiration"] = None
    if "Power" in fields:
        line = fields["Power"]
        line = clean(line.replace(",", "").strip())
        if "bhp" in line:
            line = int(round(int(clean(line.replace("bhp", "").strip())) * 1.01387, 0))
        else:
            line = int(clean(line.replace("PS", "").strip()))
        fields["Power"] = line
    else:
        fields["Power"] = None
    if "Torque" in fields:
        line = fields["Torque"]
        if "kgf·m" in line:
            line = float(line.replace("kgf·m", "").strip())
        else:
            line = float(line.replace("lb·ft", "").strip())
            line *= .138255
        fields["Torque"] = line
    else:
        fields["Torque"] = None
    if "Electric System" not in fields:
        fields["Electric System"] = None
    return fields


def parse_drivetrain(fields: dict) -> dict:
    if "Layout" not in fields:
        fields["Layout"] = None
    if "Drivetrain" not in fields:
        fields["Drivetrain"] = None
    if "Gearbox" not in fields:
        fields["Gearbox"] = None
    if "Weight" in fields:
        line = fields["Weight"]
        line = clean(line.replace(",", "").replace(".", "").strip())
        if "lbs" in line:
            line = int(int(clean(line.replace("lbs", "").strip())) * 0.453592)
        else:
            line = int(clean(line.replace("kg", "").strip()))
        fields["Weight"] = line
    else:
        fields["Weight"] = None
    if "Balance" not in fields:
        fields["Balance"] = None
    return fields


def parse_performance(fields: dict) -> dict:
    if "Top Speed" in fields:
        line = fields["Top Speed"]
        if "mph" in line:
            line = int(round(int(clean(line.replace("mph", "").strip())) * 1.609, 0))
        else:
            line = int(clean(line.replace("km/h", "").strip()))
        fields["Top Speed"] = line
    else:
        fields["Top Speed"] = None
    if "Weight-to-Power Ratio" in fields:
        # преобразовать lb/bhp в kg/PS
        pass
    else:
        fields["Weight-to-Power Ratio"] = None
    if "PP in GT5/6" in fields:
        # обработать исключения с mazda mx-5 и nissan fairlady z
        pass
    else:
        fields["PP in GT5/6"] = None
    if "0-60 Time" in fields:
        line = fields["0-60 Time"]
        line = float(line.replace("seconds", "").strip())
        fields["0-60 Time"] = line
    else:
        fields["0-60 Time"] = None
    if "PP in GT7" in fields:
        del fields["PP in GT7"]
    if "Class" in fields:
        if "GT Sport only" in fields:
            fields["Class"] = None
    else:
        fields["Class"] = None
    return fields


def parse_dimensions(fields):
    for key in fields.keys():
        fields[key] = float(clean(fields[key].replace(",", ".").replace("mm", "").strip()))
    for attr in ("Length", "Width", "Height"):
        if attr not in fields:
            fields[attr] = None
    return fields


def parse_miscellaneous(fields):
    keys = list(fields.keys())
    for key in keys:
        if key != "GT5 Type":
            del fields[key]
    if "GT5 Type" not in fields:
        fields["GT5 Type"] = None
    return fields


def parse_infobox(page):
    infobox = page.find("aside", class_="portable-infobox")
    title = clean(infobox.find("h2", class_="pi-title").get_text())
    if title == "Mazda DEMIO GL-X '99":
        infobox = page.find_all("aside", class_="portable-infobox")[-1]
    result = {}
    for section in infobox.find_all("section", class_="pi-group"):
        header = section.find("h2", class_="pi-header")
        if header is None:
            continue
        section_name = clean(header.get_text())
        fields = {}
        for item in section.find_all("div", class_="pi-data"):
            key_tag = item.find("h3", class_="pi-data-label")
            value_tag = item.find("div", class_="pi-data-value")
            if key_tag is None or value_tag is None:
                continue
            key = clean(key_tag.get_text(" "))
            for alt_tag in value_tag.find_all("i"):
                alt_tag.decompose()
            value = clean(value_tag.get_text(" "))
            fields[key] = value
        if section_name == "Production Info":
            fields = parse_prod(fields)
        elif section_name == "Engine and Power":
            fields = parse_engine(fields)
        elif section_name == "Drivetrain and Weight":
            fields = parse_drivetrain(fields)
        elif section_name == "Performance":
            fields = parse_performance(fields)
        elif section_name == "Dimensions":
            fields = parse_dimensions(fields)
        elif section_name == "Miscellaneous":
            fields = parse_miscellaneous(fields)
        result[section_name] = fields
    if len(result) != 6:
        if "Dimensions" not in result:
            result["Dimensions"] = {
                "Length": None,
                "Width": None,
                "Height": None
            }
        if "Miscellaneous" not in result:
            result["Miscellaneous"] = {
                "GT5 Type": None
            }
    return result
