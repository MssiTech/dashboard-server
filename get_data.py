import json
import re
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile


EXCEL_FILE = Path(__file__).resolve().parent / "gemotologiya2.xlsx"
JSON_FILE = Path(__file__).resolve().parent / "gemotologiya2.json"
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


CYR_TO_LAT = {
    "А": "A", "а": "a", "Б": "B", "б": "b", "В": "V", "в": "v",
    "Г": "G", "г": "g", "Д": "D", "д": "d", "Е": "E", "е": "e",
    "Ё": "Yo", "ё": "yo", "Ж": "J", "ж": "j", "З": "Z", "з": "z",
    "И": "I", "и": "i", "Й": "Y", "й": "y", "К": "K", "к": "k",
    "Л": "L", "л": "l", "М": "M", "м": "m", "Н": "N", "н": "n",
    "О": "O", "о": "o", "П": "P", "п": "p", "Р": "R", "р": "r",
    "С": "S", "с": "s", "Т": "T", "т": "t", "У": "U", "у": "u",
    "Ф": "F", "ф": "f", "Х": "X", "х": "x", "Ц": "Ts", "ц": "ts",
    "Ч": "Ch", "ч": "ch", "Ш": "Sh", "ш": "sh", "Щ": "Sh", "щ": "sh",
    "Ъ": "'", "ъ": "'", "Ь": "", "ь": "", "Ы": "I", "ы": "i",
    "Э": "E", "э": "e", "Ю": "Yu", "ю": "yu", "Я": "Ya", "я": "ya",
    "Ў": "Oʻ", "ў": "oʻ", "Қ": "Q", "қ": "q", "Ғ": "Gʻ", "ғ": "gʻ",
    "Ҳ": "H", "ҳ": "h",
}


def is_cyrillic_upper(char):
    mapped = CYR_TO_LAT.get(char)
    return mapped is not None and char != mapped and char.upper() == char


def to_latin(text):
    result = []
    length = len(text)
    for index, char in enumerate(text):
        latin = CYR_TO_LAT.get(char)
        if latin is None:
            result.append(char)
            continue
        if is_cyrillic_upper(char) and any(part.islower() for part in latin):
            nxt = index + 1
            while nxt < length and text[nxt] in "ъьЪЬ":
                nxt += 1
            follow = text[nxt] if nxt < length else ""
            if follow == "" or not follow.isalpha() or is_cyrillic_upper(follow) or follow.isupper():
                latin = "".join(part.upper() if part.isalpha() else part for part in latin)
        result.append(latin)
    return "".join(result)


CYRILLIC_RE = re.compile(r"[А-Яа-яЁёЎўҚқҒғҲҳ]")


def cell(value):
    if value is None:
        return ""
    text = str(value).strip()
    if CYRILLIC_RE.search(text):
        return to_latin(text).strip()
    return text


CODE_PART = re.compile(r"^([A-Za-zА-Яа-яЁё]*)\s*(\d{2,})(?:\.(\d+))?$", re.I)


def expand_range(text):
    text = text.strip()
    match = re.match(r"^(.+?)\s*[-–—]\s*(.+)$", text)
    if not match:
        return [text]
    left = match.group(1).replace(" ", "")
    right = match.group(2).replace(" ", "")
    start = CODE_PART.match(left)
    end = CODE_PART.match(right)
    if not start or not end:
        return [text]
    letter = start.group(1) or end.group(1)
    start_letter, end_letter = start.group(1), end.group(1)
    if start_letter and end_letter and start_letter.casefold() != end_letter.casefold():
        return [text]
    start_whole, start_frac = start.group(2), start.group(3)
    end_whole, end_frac = end.group(2), end.group(3)
    if start_frac is None and end_frac is None:
        first, last = int(start_whole), int(end_whole)
        if first > last or last - first > 50:
            return [text]
        width = max(len(start_whole), len(end_whole))
        return [f"{letter}{number:0{width}d}" for number in range(first, last + 1)]
    if start_frac is None or end_frac is None or start_whole != end_whole:
        return [text]
    first, last = int(start_frac), int(end_frac)
    if first > last or last - first > 20:
        return [text]
    return [f"{letter}{start_whole}.{number}" for number in range(first, last + 1)]


def split_codes(value):
    text = re.sub(r"(\d),(\d)", r"\1.\2", cell(value))
    text = text.replace("–", "-").replace("—", "-")
    text = re.sub(r"\s+-\s+(?=[A-Za-zА-Яа-яЁё]*\d)", ",", text)
    text = re.sub(r"(?:(?<=[;,])|^)\s*-+\s*", ",", text)
    codes = []
    seen = set()
    for part in re.split(r"[;,]+", text):
        part = part.strip(" -").rstrip(".")
        part = re.sub(r"\s+", "", part)
        if not part:
            continue
        expanded = expand_range(part)
        if len(expanded) == 1 and "-" in expanded[0]:
            expanded = re.findall(r"[A-Za-zА-Яа-яЁё]+\d{2,}(?:\.\d+)?", expanded[0], re.I)
        for code in expanded:
            code = code.strip(" -")
            code = (code[0].upper() + code[1:]) if code else code
            if not code or not CODE_PART.match(code) or code in seen:
                continue
            seen.add(code)
            codes.append(code)
    return codes


def split_simple(text):
    parts = re.split(r"[\n,;]+|\.\s+|\.$", text)
    return [part.strip(" .;()") for part in parts if part.strip(" .;()")]


def hepatitis_type(letter):
    letter = letter.upper()
    if letter in "VB":
        return "B"
    if letter in "SC":
        return "C"
    return letter


def normalize_lab_name(name):
    name = re.sub(r"(?i)^konda\s+", "", name)
    name = re.sub(r"(?i)\balt\b", "ALT", name)
    name = re.sub(r"(?i)\bast\b", "AST", name)
    return name.strip()


def expand_hepatitis(text):
    pattern = re.compile(
        r"(?i)(gepatit|hepatit|geptit)\s+[bcvs](?:(?:\s*(?:,|/|&|va)\s*|\s+)[bcvs])+(?:\s+diagnostikasi)?"
    )

    def replace(match):
        letters = re.findall(r"(?i)(?<![A-Za-zА-Яа-я])([bcvs])(?![A-Za-zА-Яа-я])", match.group(0))
        types = []
        for letter in letters:
            name = hepatitis_type(letter)
            if name not in types:
                types.append(name)
        if len(types) < 2:
            return match.group(0)
        return "; ".join(f"Gepatit {name}" for name in types)

    return pattern.sub(replace, text)


def split_list(value):
    text = expand_hepatitis(cell(value).replace("\r\n", "\n").replace("\r", "\n"))
    if not text:
        return []
    parts = []
    index = 0
    for match in re.finditer(r"\(([^()]*)\)", text):
        parts.extend(split_simple(text[index:match.start()]))
        parts.extend(split_simple(match.group(1)))
        index = match.end()
    parts.extend(split_simple(text[index:]))
    return [normalize_lab_name(part) for part in parts]


def col_index(ref):
    n = 0
    for char in ref:
        if char.isdigit():
            break
        n = n * 26 + (ord(char) - 64)
    return n - 1


def read_sheet(path):
    with ZipFile(path) as archive:
        strings = []
        root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
        for item in root.findall("m:si", NS):
            texts = [node.text or "" for node in item.findall(".//m:t", NS)]
            strings.append("\n".join(texts) if len(texts) > 1 else (texts[0] if texts else ""))
        sheet = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))
        rows = []
        for row in sheet.findall("m:sheetData/m:row", NS):
            values = [""] * 5
            for node in row.findall("m:c", NS):
                index = col_index(node.get("r", "A"))
                if index > 4:
                    continue
                value = node.find("m:v", NS)
                text = value.text if value is not None else ""
                if node.get("t") == "s" and text != "":
                    text = strings[int(text)]
                values[index] = text
            rows.append(values)
        return rows


items = []
current = None
for row in read_sheet(EXCEL_FILE):
    mkb_code = split_codes(row[1])
    mkb_name = cell(row[2])
    if mkb_code and mkb_code[0].lower() == "mkb-kod":
        continue
    laboratories = split_list(row[3])
    diagnostics = split_list(row[4])
    if mkb_code:
        current = {
            "number": cell(row[0]) or len(items) + 1,
            "mkb_code": mkb_code,
            "mkb_name": mkb_name,
            "laboratory": laboratories,
            "diagnostic": diagnostics,
        }
        items.append(current)
        continue
    if current:
        current["laboratory"].extend(laboratories)
        current["diagnostic"].extend(diagnostics)

with JSON_FILE.open("w", encoding="utf-8") as f:
    json.dump(items, f, ensure_ascii=False, indent=2)

print(f"{len(items)} ta qator saqlandi: {JSON_FILE.name}")
for item in items[:5]:
    print(item["number"], item["mkb_code"], item["mkb_name"])
    print("  laboratory:", item["laboratory"])
    print("  diagnostic:", item["diagnostic"])
