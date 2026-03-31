import cv2
from pathlib import Path
import matplotlib.pyplot as plt
import easyocr
import re

# thư mục chứa file python đang chạy
BASE_DIR = Path(__file__).resolve().parent
reader = easyocr.Reader(['en'], gpu=False)
# đường dẫn tương đối tới ảnh
image_path = str(BASE_DIR / "image.png")

def clean_plate_text(text: str) -> str:
    text = text.upper().replace("-", "").replace(".", "").replace(" ", "")

    mapping = {
        "I": "1",
        "L": "1",
        "Z": "2",
        "S": "5",
        "B": "8",
        "Q": "0",
        "D": "0",
        "O": "0",
    }

    chars = list(text)
    if len(chars) >= 1:
        chars[0] = mapping.get(chars[0], chars[0])
    if len(chars) >= 2:
        chars[1] = mapping.get(chars[1], chars[1])

    # ký tự thứ 3 của biển số Việt Nam thường là chữ cái, OCR hay nhầm A thành 4/8/6/H
    if len(chars) >= 3:
        third_char_map = {
            "4": "A",
            "8": "A",
            "6": "A",
            "H": "A",
        }
        chars[2] = third_char_map.get(chars[2], chars[2])

    cleaned = "".join(ch for ch in chars if ch.isalnum())

    # nếu OCR đọc thiếu dấu, cố gắng chuẩn hóa về dạng 2 số + 1 chữ + 5 số
    if re.match(r"^\d{3}\d{5}$", cleaned):
        cleaned = cleaned[:2] + "A" + cleaned[3:]

    match = re.match(r"(\d{2}[A-Z])(\d{5})", cleaned)
    if match:
        return f"{match.group(1)}-{match.group(2)[:3]}.{match.group(2)[3:]}"

    return cleaned

def main():
    img = cv2.imread(image_path)
    
    # chuyển đổi ảnh sang ảnh xám
    
    if img is None:
        print("Không thể đọc ảnh từ đường dẫn:", image_path)
        return
    # cv2.imshow("Hình ảnh", img)
    biensoxe  = img.copy()
    gray = cv2.cvtColor(biensoxe, cv2.COLOR_BGR2GRAY)
    # xu ly nhieu anh
    nhieuanh = cv2.GaussianBlur(gray, (5, 5), 0)
    # tang sang cua anh
    tangsang = cv2.equalizeHist(gray)
    # cv2.imshow("hinh anh xám", gray)
    # cv2.imshow("hinh anh nhieuanh", nhieuanh)
    # cv2.imshow("hinh anh tangsang", tangsang)
    # chuẩn hóa và nhị phân hóa để OCR tốt hơn
    nomormalize = cv2.normalize(tangsang, None, 0, 255, cv2.NORM_MINMAX)
    resize_img = cv2.resize(nomormalize, (400, 400), interpolation=cv2.INTER_CUBIC)

    # cắt biển số theo tọa độ đã xác định trên ảnh 400x400
    crop_img = resize_img[258:304, 140:276]

    # phóng to vùng biển số trước khi OCR
    crop_img = cv2.resize(crop_img, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)

    thresh = cv2.adaptiveThreshold(
        crop_img,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        10,
    )

    cv2.imwrite("crop_img.jpg", crop_img)
    cv2.imwrite("crop_thresh.jpg", thresh)

    print("Extracted Text:")
    result = reader.readtext(
        thresh,
        detail=1,
        paragraph=False,
        allowlist='ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-'
    )

    best_text = ""
    best_score = 0.0
    for detection in result:
        text = detection[1]
        score = detection[2]
        print(text, "| score:", round(score, 3))
        if score > best_score:
            best_text = text
            best_score = score

    cleaned_text = clean_plate_text(best_text)
    print("Biển số sau làm sạch:", cleaned_text)
    plt.figure(figsize=(12, 4))
    plt.subplot(1, 5, 1)
    plt.imshow(img, cmap='gray')
    plt.title('Hình ảnh gốc')
    plt.axis('off')
    plt.subplot(1, 5, 2)
    plt.imshow(gray, cmap='gray')
    plt.title('Hình ảnh xám')
    plt.axis('off')
    plt.subplot(1, 5, 3)
    plt.imshow(nhieuanh, cmap='gray')
    plt.title('Hình ảnh nhiễu')
    plt.axis('off')
    plt.subplot(1, 5, 4)
    plt.imshow(tangsang, cmap='gray')
    plt.title('Hình ảnh tăng sáng')
    plt.axis('off')
    plt.subplot(1, 5, 5)
    plt.imshow(thresh, cmap='gray')
    plt.title(f'OCR: {cleaned_text}')
    plt.axis('off')
    plt.tight_layout()
    plt.show()

    cv2.waitKey(0)
    cv2.destroyAllWindows()
if __name__ == "__main__":
    main()
    