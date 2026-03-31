import pandas as pd
import matplotlib.pyplot as plt

# ==========================================
# 1. ĐỌC VÀ CHUẨN BỊ DỮ LIỆU
# ==========================================
# Đọc file CSV
df = pd.read_csv('ITA105_Slide_5.csv')

# Chuyển cột 'date' sang kiểu dữ liệu datetime
df['date'] = pd.to_datetime(df['date'])

# Đặt 'date' làm index (chỉ số) của DataFrame
df.set_index('date', inplace=True)

print("--- Dữ liệu gốc (có giá trị thiếu tại 2019-01-02) ---")
print(df.head())

# ==========================================
# 2. XỬ LÝ DỮ LIỆU THIẾU (MISSING DATA)
# ==========================================
# Sử dụng phương pháp Nội suy tuyến tính (Linear Interpolation) 
# để lấp đầy các ô trống trước khi tính toán trung bình trượt
df['price_interp'] = df['price'].interpolate(method='linear')

# ==========================================
# 3. TÍNH TOÁN TRUNG BÌNH TRƯỢT (MA_3 & MA_6)
# ==========================================
# MA_3: Trung bình trượt cửa sổ 3 ngày
df['MA_3'] = df['price_interp'].rolling(window=3).mean()

# MA_6: Trung bình trượt cửa sổ 6 ngày
df['MA_6'] = df['price_interp'].rolling(window=6).mean()

print("\n--- Dữ liệu sau khi tính MA_3 và MA_6 ---")
print(df[['price', 'price_interp', 'MA_3', 'MA_6']].head(10))

# ==========================================
# 4. TRỰC QUAN HÓA (VISUALIZATION)
# ==========================================
plt.figure(figsize=(12, 6))

# Vẽ đường giá gốc (đã nội suy)
plt.plot(df.index, df['price_interp'], label='Giá nội suy (Interpolated)', color='lightgray', alpha=0.7)

# Vẽ đường MA_3
plt.plot(df.index, df['MA_3'], label='Moving Average 3 ngày', color='blue', linewidth=1.5)

# Vẽ đường MA_6
plt.plot(df.index, df['MA_6'], label='Moving Average 6 ngày', color='red', linewidth=2)

plt.title('So sánh làm mịn dữ liệu: MA_3 vs MA_6')
plt.xlabel('Ngày')
plt.ylabel('Giá')
plt.legend()
plt.grid(True, linestyle='--', alpha=0.6)
plt.show()