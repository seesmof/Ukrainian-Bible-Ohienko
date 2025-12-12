import requests
from bs4 import BeautifulSoup
import re
import os

# Base URL for relative links
BASE_URL = "https://uk.wikisource.org"
MAIN_PAGE = "https://uk.wikisource.org/wiki/%D0%91%D1%96%D0%B1%D0%BB%D1%96%D1%8F_(%D0%9E%D0%B3%D1%96%D1%94%D0%BD%D0%BA%D0%BE)"

# Output directory
OUTPUT_DIR = "USFM_Output"
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# USFM Book Code Mapping (Partial list - extend as needed for all 66 books)
# You must ensure the keys match the text in the Wikisource links exactly or partially.
BOOK_MAP = {
    # OT
    "Буття": "GEN",
    "Вихід": "EXO",
    "Левит": "LEV",
    "Числа": "NUM",
    "Повторення Закону": "DEU",
    "Ісуса Навина": "JOS",
    "Суддів": "JDG",
    "Рут": "RUT",
    "Перша книга Самуїлова": "1SA",
    "Друга книга Самуїлова": "2SA",
    "Перша книга царів": "1KI",
    "Друга книга царів": "2KI",
    "Перша книга хроніки": "1CH",
    "Друга книга хроніки": "2CH",
    "Ездри": "EZR",
    "Неемії": "NEH",
    "Естер": "EST",
    "Йова": "JOB",
    "Псалмів": "PSA",
    "приказок Соломонових": "PRO",
    "Екклезіястова": "ECC",
    "Пісня над піснями": "SNG",
    "Ісаї": "ISA",
    "Єремії": "JER",
    "Плач Єремії": "LAM",
    "Єзекіїля": "EZK",
    "Даниїла": "DAN",
    "Осії": "HOS",
    "Йоіла": "JOL",
    "Амоса": "AMO",
    "Овдія": "OBA",
    "Йони": "JON",
    "Михея": "MIC",
    "Наума": "NAM",
    "Авакума": "HAB",
    "Софонії": "ZEP",
    "Огія": "HAG",
    "Захарія": "ZEC",
    "Малахії": "MAL",
    # NT
    "Матвія": "MAT",
    "Марка": "MRK",
    "Луки": "LUK",
    "Івана": "JHN",
    "Дії": "ACT",
    "римлян": "ROM",
    "1-е до коринтян": "1CO",
    "2-е до коринтян": "2CO",  # Check specific link text on wiki
    "Перше послання св. апостола Павла до коринтян": "1CO",
    "Друге послання св. апостола Павла до коринтян": "2CO",
    "галатів": "GAL",
    "ефесян": "EPH",
    "филип'ян": "PHP",
    "колосян": "COL",
    "Перше послання св. апостола Павла до солунян": "1TH",
    "Друге послання св. апостола Павла до солунян": "2TH",
    "Перше послання св. апостола Павла до Тимофія": "1TI",
    "Друге послання св. апостола до Тимофія": "2TI",
    "Тита": "TIT",
    "Филимона": "PHM",
    "євреїв": "HEB",
    "Якова": "JAS",
    "Перше соборне послання св. апостола Петра": "1PE",
    "Друге соборне послання св. апостола Петра": "2PE",
    "Перше соборне послання св. апостола Івана": "1JN",
    "Друге соборне послання св. апостола Івана": "2JN",
    "Третє соборне послання св. апостола Івана": "3JN",
    "Юди": "JUD",
    "Об'явлення": "REV",
}


def clean_text(text):
    # Remove footnotes markers like [1], [2]
    return re.sub(r"\[\d+\]", "", text).strip()


def get_book_code(link_text):
    for key, code in BOOK_MAP.items():
        if key in link_text:
            return code
    return None


def parse_book(book_url, usfm_code, book_title):
    print(f"Processing {usfm_code} from {book_url}...")
    resp = requests.get(book_url)
    soup = BeautifulSoup(resp.content, "html.parser")

    usfm_content = [
        f"\\id {usfm_code} Ohienko Bible 1988 (Wikisource)",
        f"\\ide UTF-8",
        f"\\h {book_title}",
        f"\\toc1 {book_title}",
        f"\\mt1 {book_title}",
    ]

    # Find the main content div
    content_div = soup.find("div", class_="mw-parser-output")
    if not content_div:
        print(f"Error: Could not find content for {usfm_code}")
        return

    current_chapter = 0

    # Iterate through paragraphs to find verses and chapters
    # Note: Wikisource structure for this Bible typically uses <p> tags.
    # Chapter numbers are often bold <b> or just text at start of <p>.

    for p in content_div.find_all(["p", "h3", "h2"]):
        text = clean_text(p.get_text())

        if not text:
            continue

        # Check for Section Headers (optional, adds \s markers)
        if p.name in ["h2", "h3"]:
            usfm_content.append(f"\\s1 {text}")
            continue

        # Regex to find verse numbers at the start of the line
        # Logic:
        # 1. If we see a big number (relative to current chapter) at start -> New Chapter + Verse 1
        # 2. If we see a small number -> Verse number

        match = re.match(r"^(\d+)\s*(.*)", text)
        if match:
            num = int(match.group(1))
            rest_of_text = match.group(2)

            # Heuristic: If number is current_chapter + 1, it's a new chapter
            # AND it acts as Verse 1.
            if num == current_chapter + 1:
                current_chapter = num
                usfm_content.append(f"\\c {current_chapter}")
                usfm_content.append(f"\\v 1 {rest_of_text}")
            else:
                # Regular verse
                usfm_content.append(f"\\v {num} {rest_of_text}")
        else:
            # Paragraph without a number? Likely continuation of previous verse or intro
            if current_chapter == 0:
                usfm_content.append(f"\\rem {text}")  # Intro text
            else:
                usfm_content.append(f"\\p")  # Paragraph break
                usfm_content.append(text)

    # Write to file
    filename = os.path.join(OUTPUT_DIR, f"{usfm_code}.usfm")
    with open(filename, "w", encoding="utf-8") as f:
        f.write("\n".join(usfm_content))
    print(f"Saved {filename}")


def main():
    print("Fetching book list...")
    resp = requests.get(MAIN_PAGE)
    soup = BeautifulSoup(resp.content, "html.parser")

    # Find all links in the content area
    content_area = soup.find("div", class_="mw-parser-output")
    links = content_area.find_all("a", href=True)

    processed_codes = set()

    for link in links:
        href = link["href"]
        title = link.get_text()

        # Filter mostly likely book links (skip irrelevant wiki links)
        if "/wiki/" not in href or "Вікіджерела" in title or "Редагувати" in title:
            continue

        code = get_book_code(title)
        if code and code not in processed_codes:
            full_url = BASE_URL + href
            parse_book(full_url, code, title)
            processed_codes.add(code)


if __name__ == "__main__":
    main()
