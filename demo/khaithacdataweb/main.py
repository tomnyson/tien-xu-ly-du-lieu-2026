import re
import time
import json
import hashlib
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://batdongsandaklak.net/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36"
}

session = requests.Session()
session.headers.update(HEADERS)


def get_html(url, timeout=20):
    resp = session.get(url, timeout=timeout)
    resp.raise_for_status()
    return resp.text


def clean_text(text):
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def slug_from_url(url):
    path = urlparse(url).path.strip("/")
    return path.split("/")[-1].replace(".html", "")


def extract_listing_links(html, base_url=BASE_URL):
    soup = BeautifulSoup(html, "html.parser")
    links = set()

    # link bài chi tiết thường nằm ở tiêu đề H1/H2/H3 hoặc anchor trong block listing
    for a in soup.select("a[href]"):
        href = a.get("href", "").strip()
        full = urljoin(base_url, href)

        # lọc link bài đăng chi tiết
        if "/nha-dat/" in full and full.endswith(".html"):
            links.add(full)

    return sorted(links)


def extract_images(soup, base_url=BASE_URL):
    images = []
    for img in soup.select("img[src]"):
        src = img.get("src", "").strip()
        if not src:
            continue
        full = urljoin(base_url, src)
        if full not in images:
            images.append(full)
    return images


def parse_price_to_number(price_text):
    """
    Ví dụ:
    '4.59 Tỷ' -> 4590000000
    '115 Triệu' -> 115000000
    """
    t = clean_text(price_text).lower().replace(",", ".")
    m = re.search(r"(\d+(?:\.\d+)?)\s*(tỷ|triệu)", t)
    if not m:
        return None, ""
    value = float(m.group(1))
    unit = m.group(2)
    if unit == "tỷ":
        return int(value * 1_000_000_000), unit
    if unit == "triệu":
        return int(value * 1_000_000), unit
    return None, unit


def find_label_value(text, label):
    """
    Tìm dạng:
    Giá : 4.59 Tỷ
    Hướng : Bắc
    """
    pattern = rf"{re.escape(label)}\s*:?\s*(.+)"
    m = re.search(pattern, text, re.IGNORECASE)
    return clean_text(m.group(1)) if m else ""


def extract_phone(text):
    phones = re.findall(r"(0\d{9,10})", text)
    return phones[0] if phones else ""


def parse_detail_page(url):
    html = get_html(url)
    soup = BeautifulSoup(html, "html.parser")
    raw_text = soup.get_text("\n", strip=True)
    text = clean_text(raw_text)

    title = ""
    # ưu tiên heading chính
    for sel in ["h1", "h2", "title"]:
        el = soup.select_one(sel)
        if el and clean_text(el.get_text()):
            title = clean_text(el.get_text())
            break

    # ngày đăng dạng 14-01-2026
    date_match = re.search(r"\b\d{2}-\d{2}-\d{4}\b", raw_text)
    posted_date = date_match.group(0) if date_match else ""

    # lấy các field cơ bản
    price_text = find_label_value(raw_text, "Giá")
    direction = find_label_value(raw_text, "Hướng")
    road = find_label_value(raw_text, "Đường")
    ward = find_label_value(raw_text, "Phường (xã)")
    area_text = find_label_value(raw_text, "Diện Tích") or find_label_value(raw_text, "Diện tích")

    price_value, price_unit = parse_price_to_number(price_text)

    # liên hệ
    contact_name = ""
    # có thể tinh chỉnh selector sau khi test thực tế
    for possible in soup.select("a, strong, b, div, span"):
        txt = clean_text(possible.get_text())
        if txt.lower().startswith("mr ") or txt.lower().startswith("chị ") or txt.lower().startswith("anh "):
            contact_name = txt
            break

    contact_phone = extract_phone(raw_text)

    # mô tả: có thể lấy block sau "THÔNG TIN LIÊN HỆ" hoặc gom text
    description = raw_text
    images = extract_images(soup)

    data = {
        "url": url,
        "slug": slug_from_url(url),
        "title": title,
        "posted_date": posted_date,
        "price_text": clean_text(price_text),
        "price_value": price_value,
        "price_unit": price_unit,
        "direction": clean_text(direction),
        "road": clean_text(road),
        "ward_or_commune": clean_text(ward),
        "district_or_city": "Buôn Ma Thuột / Đắk Lắk",
        "area_text": clean_text(area_text),
        "area_m2": None,
        "dimensions_text": clean_text(area_text),
        "category": "",
        "demand": "",
        "contact_name": clean_text(contact_name),
        "contact_phone": clean_text(contact_phone),
        "description": description,
        "image_urls": images,
    }
    return data


def crawl_seed_pages(seed_urls):
    all_links = set()

    for url in seed_urls:
        try:
            html = get_html(url)
            links = extract_listing_links(html)
            all_links.update(links)
            time.sleep(1)
        except Exception as e:
            print(f"[ERROR] Seed failed: {url} -> {e}")

    return sorted(all_links)


if __name__ == "__main__":
    seed_urls = [
        "https://batdongsandaklak.net/",
        "https://batdongsandaklak.net/nhu-cau/cho-thue",
    ]

    detail_links = crawl_seed_pages(seed_urls)
    print(f"Found {len(detail_links)} detail links")

    rows = []
    for i, link in enumerate(detail_links, 1):
        try:
            item = parse_detail_page(link)
            rows.append(item)
            print(f"[{i}] OK {item['title']}")
            time.sleep(1)
        except Exception as e:
            print(f"[{i}] FAIL {link} -> {e}")

    with open("batdongsandaklak.json", "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)

    print("Saved batdongsandaklak.json")