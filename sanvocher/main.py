from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time

# Danh sách trang voucher (có thể thêm)
VOUCHER_SITES = [
    "https://highlandsvoucher.com/",
    "https://voucherhighlands.com/",
    "https://voucherhighlandcoffee.com/",
    "https://khuyenmaihighland.online/",
    "https://voucherhighlandstoanquoc.com/",   # ← trang bị modal
]

def auto_collect_highland():
    print("🚀 Khởi động tool auto collect voucher Highlands (đã fix modal popup)...")

    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    # chrome_options.add_argument("--headless")  # Bỏ comment nếu muốn chạy ngầm

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    wait = WebDriverWait(driver, 8)  # Chờ tối đa 8 giây

    for url in VOUCHER_SITES:
        try:
            print(f"📌 Đang xử lý: {url}")
            driver.get(url)
            time.sleep(3)

            # ==================== FIX MODAL VÒNG QUAY MAY MẮN ====================
            try:
                # Tìm và đóng nút X của modal (dùng nhiều cách để chắc ăn)
                close_selectors = [
                    "//button[contains(@class, 'close') or contains(@aria-label, 'Close') or @class='modal-close']",
                    "//*[contains(@class, 'close') or contains(text(), '×') or contains(text(), '✕')]",
                    "//button[contains(@class, 'ant-modal-close') or contains(@class, 'popup-close')]",
                    "//div[contains(@class, 'modal')]//button",  # fallback
                ]
                
                for selector in close_selectors:
                    close_btns = driver.find_elements(By.XPATH, selector)
                    for btn in close_btns:
                        if btn.is_displayed():
                            driver.execute_script("arguments[0].scrollIntoView();", btn)
                            btn.click()
                            print("✅ Đã đóng modal Vòng Quay May Mắn!")
                            time.sleep(2)
                            break
                    else:
                        continue
                    break
            except:
                print("ℹ️ Không thấy modal hoặc đã đóng rồi.")

            # ==================== CLICK CLAIM VOUCHER ====================
            claim_buttons = wait.until(
                EC.presence_of_all_elements_located(
                    (By.XPATH, "//button[contains(text(), 'Nhận Ưu Đãi Ngay') or contains(text(), 'Lấy Deal') or contains(text(), 'Chốt Deal') or contains(text(), 'Nhận Voucher')]")
                )
            )

            for btn in claim_buttons:
                try:
                    if btn.is_displayed():
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                        time.sleep(1)
                        btn.click()
                        print("✅ Đã click claim 1 voucher!")
                        time.sleep(2.5)  # Chờ chuyển Zalo Mini App
                except:
                    pass

            time.sleep(4)
        except Exception as e:
            print(f"❌ Lỗi với {url}: {e}")

    print("🎉 HOÀN THÀNH! Kiểm tra Zalo Mini App Highlands Rewards ngay nhé.")
    input("Nhấn Enter để đóng trình duyệt...")

if __name__ == "__main__":
    auto_collect_highland()