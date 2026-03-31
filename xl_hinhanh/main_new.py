
import cv2
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt
import easyocr
import re

BASE_DIR = Path(__file__).resolve().parent
reader = easyocr.Reader(['en'], gpu=False)
image_path = str(BASE_DIR / "image.png")

# ── Hằng số ──────────────────────────────────────────────────────────────────
RAW_PLATE_RE  = re.compile(r"\d{2}[A-Z]{1,2}[\-\.]?\d{3,5}")
PLATE_PATTERN = re.compile(r"(\d{2}[A-Z]{1,2})-(\d{3})\.(\d{2})")
OCR_ALLOWLIST = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-"
CHAR_MAP = {"I":"1","L":"1","Z":"2","S":"5","B":"8","Q":"0","D":"0","O":"0"}


# ── Làm sạch text ────────────────────────────────────────────────────────────
def clean_plate_text(raw: str) -> str:
    text = re.sub(r"[^A-Z0-9]", "", raw.upper())
    if len(text) < 7:
        return raw.upper()
    chars = list(text)
    for i in (0, 1):
        if not chars[i].isdigit():
            chars[i] = CHAR_MAP.get(chars[i], chars[i])
    if chars[2].isdigit():
        chars[2] = {"1":"I","0":"O","8":"B","5":"S"}.get(chars[2], chars[2])
    if chars[2] in {"8","6"}:
        chars[2] = "A"
    if len(chars) >= 8 and not chars[3].isdigit():
        prefix = "".join(chars[:4])
        suffix = "".join(c for c in chars[4:] if c.isdigit())
    else:
        prefix = "".join(chars[:3])
        suffix = "".join(c for c in chars[3:] if c.isdigit())
    if len(suffix) < 5:
        return "".join(chars)
    return f"{prefix}-{suffix[:3]}.{suffix[3:5]}"


# ── Tiền xử lý ───────────────────────────────────────────────────────────────
def preprocess_variants(gray: np.ndarray) -> list:
    clahe    = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    blurred  = cv2.GaussianBlur(enhanced, (3, 3), 0)
    k        = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))

    _, otsu = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    otsu    = cv2.morphologyEx(otsu, cv2.MORPH_CLOSE, k)

    ag = cv2.adaptiveThreshold(blurred, 255,
         cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 10)
    ag = cv2.morphologyEx(ag, cv2.MORPH_CLOSE, k)

    am = cv2.adaptiveThreshold(blurred, 255,
         cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 31, 10)

    return [("OTSU", otsu), ("Adaptive_Gauss", ag), ("Adaptive_Mean", am)]


def resize_for_ocr(img: np.ndarray, target_h: int = 80) -> np.ndarray:
    h, w = img.shape[:2]
    scale = target_h / max(h, 1)
    return cv2.resize(img, (max(int(w * scale), 1), target_h),
                      interpolation=cv2.INTER_CUBIC)


# ── OCR một vùng crop ────────────────────────────────────────────────────────
def ocr_region(gray_crop: np.ndarray) -> tuple:
    resized  = resize_for_ocr(gray_crop)
    variants = preprocess_variants(resized)
    best_text, best_score, best_img = "", 0.0, resized

    for name, thresh in variants:
        results   = reader.readtext(thresh, detail=1, paragraph=False,
                                    allowlist=OCR_ALLOWLIST, width_ths=0.9,
                                    text_threshold=0.4)
        combined  = "".join(d[1] for d in results)
        avg_score = sum(d[2] for d in results) / len(results) if results else 0.0
        cleaned   = clean_plate_text(combined)
        is_valid  = bool(PLATE_PATTERN.match(cleaned))

        print(f"    [{name}] raw='{combined}' -> '{cleaned}' score={avg_score:.3f} valid={is_valid}")

        if is_valid and not PLATE_PATTERN.match(best_text):
            best_text, best_score, best_img = cleaned, avg_score, thresh
        elif is_valid and avg_score > best_score:
            best_text, best_score, best_img = cleaned, avg_score, thresh
        elif not PLATE_PATTERN.match(best_text) and avg_score > best_score:
            best_text, best_score, best_img = cleaned, avg_score, thresh

    return best_text, best_score, best_img


# ── Chiến lược 1: OCR-first scan ─────────────────────────────────────────────
def detect_by_ocr(gray: np.ndarray, scan_scale: float = 0.5):
    """
    Chạy EasyOCR trên ảnh thu nhỏ để tìm vùng có text dạng biển số.
    Trả về crop vùng biển số trên ảnh gốc (hoặc None nếu không tìm thấy).
    """
    h, w = gray.shape
    small = cv2.resize(gray, (int(w * scan_scale), int(h * scan_scale)),
                       interpolation=cv2.INTER_AREA)

    results = reader.readtext(small, detail=1, paragraph=False,
                              allowlist=OCR_ALLOWLIST, text_threshold=0.3,
                              width_ths=1.0)

    print(f"  [OCR-scan x{scan_scale}] {len(results)} boxes:")
    plate_boxes = []
    for (bbox, text, score) in results:
        t = re.sub(r"[^A-Z0-9]", "", text.upper())
        print(f"    '{text}' score={score:.3f}")
        # Chấp nhận nếu khớp pattern hoặc >= 6 ký tự alnum với >= 4 chữ số
        is_candidate = bool(RAW_PLATE_RE.search(t)) or \
                       (len(t) >= 6 and sum(c.isdigit() for c in t) >= 4)
        if is_candidate:
            pts = (np.array(bbox) / scan_scale).astype(int)
            xs, ys = pts[:, 0], pts[:, 1]
            x1 = max(0, xs.min() - 10)
            y1 = max(0, ys.min() - 8)
            x2 = min(w, xs.max() + 10)
            y2 = min(h, ys.max() + 8)
            plate_boxes.append((score, x1, y1, x2, y2, text))

    if not plate_boxes:
        return None

    plate_boxes.sort(reverse=True)
    _, x1, y1, x2, y2, txt = plate_boxes[0]
    print(f"  [OCR-scan] -> chọn '{txt}' crop ({x1},{y1})-({x2},{y2})")
    crop = gray[y1:y2, x1:x2]
    return crop if crop.size > 0 else None


# ── Chiến lược 2: Contour fallback ───────────────────────────────────────────
def detect_by_contour(gray: np.ndarray) -> np.ndarray:
    h_img, w_img = gray.shape
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    # Dùng Sobel + morphology dilation ngang mạnh
    sx  = cv2.convertScaleAbs(cv2.Sobel(blurred, cv2.CV_64F, 1, 0, ksize=3))
    sy  = cv2.convertScaleAbs(cv2.Sobel(blurred, cv2.CV_64F, 0, 1, ksize=3))
    mag = cv2.addWeighted(sx, 0.5, sy, 0.5, 0)
    _, thresh = cv2.threshold(mag, 50, 255, cv2.THRESH_BINARY)
    k      = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 5))
    closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, k)

    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL,
                                   cv2.CHAIN_APPROX_SIMPLE)
    best_sc, best_box = -1, None
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        if h < 8 or w < 30:
            continue
        ratio = w / h
        if not (2.0 <= ratio <= 7.5):
            continue
        rs = max(0.0, 1.0 - abs(ratio - 4.5) / 4.5)
        hr = h / h_img
        hs = 1.0 if 0.02 <= hr <= 0.20 else max(0.0, 1.0 - abs(hr - 0.11) * 10)
        cy = (y + h / 2) / h_img
        ps = 1.0 if 0.4 <= cy <= 0.92 else 0.3
        sc = rs * 0.5 + hs * 0.3 + ps * 0.2
        if sc > best_sc:
            best_sc, best_box = sc, (x, y, w, h)

    if best_box is None:
        print("  [contour] Không tìm thấy, dùng toàn ảnh")
        return gray

    x, y, w, h = best_box
    print(f"  [contour] score={best_sc:.3f} ratio={w/h:.2f} box=({x},{y},{w},{h})")
    return gray[max(0,y-6):min(h_img,y+h+6),
                max(0,x-8):min(w_img,x+w+8)]


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    img = cv2.imread(image_path)
    if img is None:
        print("Khong doc duoc anh:", image_path)
        return

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Bước 1: OCR-first (scale nhỏ để nhanh)
    print("\n[B1] OCR-scan scale=0.5...")
    plate_crop = detect_by_ocr(gray, scan_scale=0.5)

    # Bước 2: fallback contour
    if plate_crop is None:
        print("\n[B2] Fallback contour...")
        plate_crop = detect_by_contour(gray)

    print(f"\nPlate region: {plate_crop.shape}")

    # Bước 3: OCR vùng crop
    print("\n[B3] OCR crop:")
    plate_text, score, best_thresh = ocr_region(plate_crop)

    # Bước 4: Nếu vẫn sai → scan toàn ảnh scale=1.0
    if not PLATE_PATTERN.match(plate_text):
        print("\n[B4] OCR-scan scale=1.0 (full res)...")
        crop2 = detect_by_ocr(gray, scan_scale=1.0)
        if crop2 is not None:
            t2, s2, th2 = ocr_region(crop2)
            if PLATE_PATTERN.match(t2) or s2 > score:
                plate_text, score, best_thresh, plate_crop = t2, s2, th2, crop2

    print(f"\n✅ Bien so: {plate_text}  (score={score:.3f})")

    # Visualize
    fig, axes = plt.subplots(1, 4, figsize=(16, 4))
    axes[0].imshow(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    axes[0].set_title("Anh goc")
    axes[1].imshow(gray, cmap="gray")
    axes[1].set_title("Anh xam")
    axes[2].imshow(plate_crop, cmap="gray")
    axes[2].set_title("Vung bien so")
    axes[3].imshow(best_thresh, cmap="gray")
    axes[3].set_title(f"OCR: {plate_text}")
    for ax in axes:
        ax.axis("off")
    plt.tight_layout()
    plt.savefig("result.jpg", dpi=150)
    plt.show()


if __name__ == "__main__":
    main()