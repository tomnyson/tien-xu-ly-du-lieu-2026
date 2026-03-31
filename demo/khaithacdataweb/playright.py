import csv
import json
import re
import time
import random
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

START_URL = "https://www.nhatot.com/mua-ban-bat-dong-san-thanh-pho-buon-ma-thuot-dak-lak"

# ---------------------------------------------------------------------------
# Stealth JS — injected into every page to evade Cloudflare bot detection.
# This replaces the need for 'playwright-stealth' or 'cloudscraper'.
# ---------------------------------------------------------------------------
STEALTH_JS = """
() => {
    // 1. Remove the 'webdriver' flag that Playwright/Puppeteer sets
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

    // 2. Fake a real Chrome runtime object
    window.chrome = {
        runtime: {
            onConnect: { addListener: function() {} },
            id: undefined
        },
        loadTimes: function() { return {} },
        csi: function() { return {} },
    };

    // 3. Fake plugins (headless Chrome has 0 plugins)
    Object.defineProperty(navigator, 'plugins', {
        get: () => [
            { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer' },
            { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai' },
            { name: 'Native Client', filename: 'internal-nacl-plugin' },
        ],
    });

    // 4. Fake languages
    Object.defineProperty(navigator, 'languages', {
        get: () => ['vi-VN', 'vi', 'en-US', 'en'],
    });

    // 5. Override permissions query to avoid detection
    const originalQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (parameters) => (
        parameters.name === 'notifications'
            ? Promise.resolve({ state: Notification.permission })
            : originalQuery(parameters)
    );

    // 6. Patch webGL vendor/renderer to look like real GPU
    const getParameter = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(parameter) {
        if (parameter === 37445) return 'Intel Inc.';
        if (parameter === 37446) return 'Intel Iris OpenGL Engine';
        return getParameter.call(this, parameter);
    };
}
"""


def clean_text(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def parse_number_from_text(text: str):
    if not text:
        return None
    t = text.lower().replace(".", "").replace(",", ".")
    m = re.search(r"(\d+(?:\.\d+)?)", t)
    if not m:
        return None
    try:
        return float(m.group(1))
    except Exception:
        return None


def random_delay(min_s=1.0, max_s=3.0):
    """Human-like random delay to avoid rate limiting."""
    time.sleep(random.uniform(min_s, max_s))


def human_scroll(page):
    """Simulate human-like scrolling behavior."""
    page.evaluate("""
        () => {
            const distance = Math.floor(Math.random() * 300) + 200;
            window.scrollBy(0, distance);
        }
    """)
    page.wait_for_timeout(random.randint(500, 1500))


def _is_cloudflare_challenge(page) -> bool:
    """Check if the current page is a Cloudflare challenge."""
    try:
        title = page.title().lower()
        url = page.url.lower()
        cf_indicators = [
            "just a moment" in title,
            "attention required" in title,
            "challenges.cloudflare.com" in url,
        ]
        # Only check page content if title didn't match (avoid expensive call)
        if not any(cf_indicators):
            content = page.content()[:3000].lower()
            cf_indicators.extend([
                "cf-browser-verification" in content,
                "challenge-platform" in content,
                'id="challenge-running"' in content,
                'id="challenge-stage"' in content,
            ])
        return any(cf_indicators)
    except Exception:
        return False


def wait_for_cloudflare(page, timeout_ms=30000):
    """
    Detect and wait for Cloudflare challenge pages.
    Phase 1: Auto-wait up to timeout_ms for the challenge to resolve.
    Phase 2: If still stuck, ask the user to solve it manually in the browser.
    Returns True once the page loads normally.
    """
    # ---- Phase 1: Auto-wait ----
    start = time.time()
    while (time.time() - start) * 1000 < timeout_ms:
        if not _is_cloudflare_challenge(page):
            return True
        print("  -> Cloudflare challenge detected, waiting...")
        page.wait_for_timeout(3000)

    # ---- Phase 2: Interactive (user solves CAPTCHA in browser window) ----
    if _is_cloudflare_challenge(page):
        print()
        print("  ╔════════════════════════════════════════════════════════╗")
        print("  ║  CLOUDFLARE CAPTCHA — Please solve it in the browser  ║")
        print("  ║  The script will continue automatically once cleared. ║")
        print("  ╚════════════════════════════════════════════════════════╝")
        print()

        # Poll every 2 seconds until user solves it (no timeout)
        while _is_cloudflare_challenge(page):
            page.wait_for_timeout(2000)

        print("  -> ✅ Cloudflare challenge cleared! Continuing...")

    return True


def create_stealth_context(playwright):
    """
    Create a Playwright browser context with stealth settings.
    Uses a persistent user data dir so Cloudflare cookies persist across pages.
    Uses the real system Chrome (channel='chrome') instead of Chromium.
    """
    import tempfile
    import os

    user_data_dir = os.path.join(tempfile.gettempdir(), "pw_cf_bypass_profile")
    os.makedirs(user_data_dir, exist_ok=True)

    context = playwright.chromium.launch_persistent_context(
        user_data_dir,
        headless=False,
        channel="chrome",  # Use real Chrome — much harder for CF to detect
        # Stealth args to make Chrome look real
        args=[
            "--disable-blink-features=AutomationControlled",
            "--disable-features=IsolateOrigins,site-per-process",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-infobars",
        ],
        ignore_default_args=["--enable-automation"],
        viewport={"width": 1440, "height": 900},
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/125.0.0.0 Safari/537.36",
        locale="vi-VN",
        timezone_id="Asia/Ho_Chi_Minh",
        color_scheme="light",
    )

    # Inject stealth script into every new page/frame
    context.add_init_script(STEALTH_JS)

    return context


def click_load_more(page, max_clicks=10, wait_ms=2500):
    for _ in range(max_clicks):
        try:
            btn = page.get_by_text("Xem thêm", exact=False)
            if btn.count() == 0:
                break
            if not btn.first.is_visible():
                break
            btn.first.click(timeout=3000)
            page.wait_for_timeout(wait_ms)
            human_scroll(page)
        except Exception:
            break


def extract_cards_from_dom(page):
    data = page.locator("a[href]").evaluate_all(
        """
        (els) => {
          const rows = [];
          const seen = new Set();
          for (const a of els) {
            const href = a.href || "";
            const txt = (a.innerText || "").replace(/\\s+/g, " ").trim();
            if (!href || !txt) continue;
            if (!/nha-tot|chotot/i.test(href)) continue;
            if (txt.length < 20) continue;
            const key = href + "||" + txt;
            if (seen.has(key)) continue;
            seen.add(key);
            rows.push({ title: txt, url: href });
          }
          return rows;
        }
        """
    )
    return data


def scrape_listing(page):
    items = page.locator("a[href]").evaluate_all(
        """
        (anchors) => {
          const results = [];
          const seen = new Set();
          function clean(s) { return (s || "").replace(/\\s+/g, " ").trim(); }
          function findCard(node) {
            let cur = node;
            for (let i = 0; i < 6 && cur; i++) {
              const txt = clean(cur.innerText);
              if (txt.length > 30) return cur;
              cur = cur.parentElement;
            }
            return node;
          }
          for (const a of anchors) {
            const href = a.href || "";
            if (!href) continue;
            const title = clean(a.innerText);
            if (title.length < 15) continue;
            const card = findCard(a);
            const text = clean(card.innerText);
            if (/Giá dưới|Giá 1 - 2 tỷ|Kinh nghiệm|Vay mua nhà|Tham khảo giá/.test(text)) continue;
            if (text.length < 25) continue;
            const key = href + "||" + title;
            if (seen.has(key)) continue;
            seen.add(key);
            results.push({ title, url: href, raw_text: text });
          }
          return results;
        }
        """
    )

    cleaned = []
    seen_urls = set()

    for item in items:
        url = item.get("url", "")
        title = clean_text(item.get("title", ""))
        raw = clean_text(item.get("raw_text", ""))

        if not url or url in seen_urls:
            continue
        if title.startswith("http"):
            continue

        seen_urls.add(url)

        time_posted = ""
        price_text = ""
        price_per_m2 = ""
        area_text = ""
        location = ""
        seller = ""

        m_time = re.search(r"^(.*?)(\d+\s*phút trước|\d+\s*giờ trước|hôm qua)", raw, re.IGNORECASE)
        if m_time: time_posted = clean_text(m_time.group(2))

        m_price = re.search(r"(\d+(?:[.,]\d+)?)\s*(tỷ|triệu)", raw, re.IGNORECASE)
        if m_price: price_text = clean_text(m_price.group(0))

        m_ppm2 = re.search(r"(\d+(?:[.,]\d+)?)\s*tr/m²|<\s*1\s*tr/m²", raw, re.IGNORECASE)
        if m_ppm2: price_per_m2 = clean_text(m_ppm2.group(0))

        m_area = re.search(r"(\d+(?:[.,]\d+)?)\s*m²", raw)
        if m_area: area_text = clean_text(m_area.group(0))

        m_loc = re.search(r"(Phường|Xã)\s+.+?(?=(?:[A-ZÀ-Ỹa-zà-ỹ].*\d+\s*tin đăng|\Z))", raw)
        if m_loc: location = clean_text(m_loc.group(0))

        m_seller = re.search(r"([A-ZÀ-Ỹa-zà-ỹ0-9 ._-]{2,})\s+\d+\s+tin đăng\s*$", raw)
        if m_seller: seller = clean_text(m_seller.group(1))

        cleaned.append({
            "title": title,
            "url": url,
            "time_posted": time_posted,
            "price_text": price_text,
            "price_value_number": parse_number_from_text(price_text),
            "price_per_m2_text": price_per_m2,
            "area_text": area_text,
            "area_m2_number": parse_number_from_text(area_text),
            "location": location,
            "seller": seller,
            "raw_text": raw,
        })

    return cleaned


def scrape_detail_with_playwright(page, url: str):
    """
    Uses the same stealth Playwright browser to fetch detail pages.
    This is far more reliable than cloudscraper for modern Cloudflare.
    """
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)

        # Wait for Cloudflare challenge if present
        if not wait_for_cloudflare(page, timeout_ms=15000):
            print("  -> Could not bypass Cloudflare on detail page")
            return {"detail_title": "", "detail_text": "", "image_urls": []}

        # Wait a bit for content to render
        page.wait_for_timeout(random.randint(1500, 3000))

        # Scroll down to trigger lazy-loaded images
        human_scroll(page)

        # Extract data using Playwright's DOM access
        detail = page.evaluate("""
            () => {
                function clean(s) { return (s || "").replace(/\\s+/g, " ").trim(); }

                const title = clean(document.title);

                // Get main body text
                const body = document.body;
                const bodyText = clean(body ? body.innerText : "");

                // Get all image URLs
                const images = new Set();
                document.querySelectorAll('img').forEach(img => {
                    const src = img.src || img.dataset.src || '';
                    if (src && !src.startsWith('data:') && src.length > 10) {
                        images.add(src.split(' ')[0]);
                    }
                });

                return {
                    detail_title: title,
                    detail_text: bodyText,
                    image_urls: Array.from(images),
                };
            }
        """)

        print(f"  -> OK: title={detail['detail_title'][:60]}, images={len(detail['image_urls'])}")
        return detail

    except PlaywrightTimeoutError:
        print(f"  -> Timeout loading detail page")
        return {"detail_title": "", "detail_text": "", "image_urls": []}
    except Exception as e:
        print(f"  -> Error fetching detail: {e}")
        return {"detail_title": "", "detail_text": "", "image_urls": []}


def save_json(rows, filename="nhatot_bmt_bds.json"):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)


def save_csv(rows, filename="nhatot_bmt_bds.csv"):
    if not rows:
        return
    keys = list(rows[0].keys())
    with open(filename, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def run():
    with sync_playwright() as p:
        # 1. Create a stealth browser context (replaces both Playwright + cloudscraper)
        print("Launching stealth browser...")
        context = create_stealth_context(p)
        page = context.pages[0] if context.pages else context.new_page()

        # 2. Navigate to listing page
        print("Opening listing page...")
        page.goto(START_URL, wait_until="domcontentloaded", timeout=60000)

        # Wait for Cloudflare challenge (will pause for manual solving if needed)
        wait_for_cloudflare(page, timeout_ms=30000)

        page.wait_for_timeout(4000)

        # Dismiss cookie/consent banners
        for text in ["Đồng ý", "Cho phép", "OK", "Tôi hiểu"]:
            try:
                btn = page.get_by_text(text, exact=False)
                if btn.count() > 0 and btn.first.is_visible():
                    btn.first.click(timeout=2000)
                    page.wait_for_timeout(1000)
                    break
            except Exception:
                pass

        click_load_more(page, max_clicks=8, wait_ms=2500)

        # 3. Extract listings
        print("Extracting listing data...")
        rows = scrape_listing(page)

        if not rows:
            fallback = extract_cards_from_dom(page)
            rows = [
                {
                    "title": clean_text(x.get("title", "")),
                    "url": x.get("url", ""),
                    "time_posted": "",
                    "price_text": "",
                    "price_value_number": None,
                    "price_per_m2_text": "",
                    "area_text": "",
                    "area_m2_number": None,
                    "location": "",
                    "seller": "",
                    "raw_text": "",
                }
                for x in fallback
            ]

        filtered = []
        seen = set()
        for row in rows:
            url = row.get("url", "")
            title = row.get("title", "")
            if not url or not title or url in seen:
                continue
            seen.add(url)
            filtered.append(row)

        print(f"Found {len(filtered)} listings")

        # 4. Fetch detail pages using the SAME stealth browser
        print("\nFetching detail pages with stealth Playwright...")
        detail_page = context.new_page()

        for i, row in enumerate(filtered[:10], start=1):
            print(f"[{i}] detail -> {row['title'][:70]}")

            detail_data = scrape_detail_with_playwright(detail_page, row["url"])
            row.update(detail_data)

            # Human-like random delay between requests
            random_delay(1.5, 3.5)

        detail_page.close()

        # 5. Save results
        save_json(filtered, "nhatot_bmt_bds.json")
        save_csv(filtered, "nhatot_bmt_bds.csv")

        print("\nSaved: nhatot_bmt_bds.json")
        print("Saved: nhatot_bmt_bds.csv")

        context.close()


if __name__ == "__main__":
    run()