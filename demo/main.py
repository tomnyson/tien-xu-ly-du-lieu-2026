import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats

# 1. Đọc dữ liệu
df = pd.read_csv('ITA105_Slide_2.csv')

# 2. Trực quan hóa trước khi xử lý (Boxplot & Scatter Plot)
plt.figure(figsize=(12, 5))

# Boxplot cho cột Price (thường chứa nhiều ngoại lệ nhất)
plt.subplot(1, 2, 1)
sns.boxplot(x=df['Price'], color='skyblue')
plt.title('Boxplot của Price (Trước khi xử lý)')

# Scatter Plot giữa Area và Price
plt.subplot(1, 2, 2)
sns.scatterplot(data=df, x='Area', y='Price')
plt.title('Scatter Plot: Area vs Price')
plt.show()

# --- PHƯƠNG PHÁP 1: Z-SCORE ---
# Tính Z-score cho các cột số
z_scores = np.abs(stats.zscore(df.select_dtypes(include=[np.number])))
# Ngưỡng thông thường là 3
df_zscore = df[(z_scores < 3).all(axis=1)]
print(f"Số lượng dòng sau khi dùng Z-Score: {len(df_zscore)}")

# --- PHƯƠNG PHÁP 2: IQR (Interquartile Range) ---
Q1 = df.quantile(0.25)
Q3 = df.quantile(0.75)
IQR = Q3 - Q1

# Xác định ranh giới
lower_bound = Q1 - 1.5 * IQR
upper_bound = Q3 + 1.5 * IQR

# Lọc dữ liệu trong khoảng [lower_bound, upper_bound]
df_iqr = df[~((df < lower_bound) | (df > upper_bound)).any(axis=1)]
print(f"Số lượng dòng sau khi dùng IQR: {len(df_iqr)}")

# 3. Trực quan hóa sau khi xử lý (So sánh)
fig, axes = plt.subplots(1, 2, figsize=(12, 5))

sns.boxplot(x=df_iqr['Price'], ax=axes[0], color='lightgreen')
axes[0].set_title('Boxplot Price (Sau khi lọc IQR)')

sns.scatterplot(data=df_iqr, x='Area', y='Price', ax=axes[1], color='green')
axes[1].set_title('Scatter Area vs Price (Sau khi lọc IQR)')

plt.tight_layout()
plt.show()

# 4. Lưu dữ liệu sạch
# df_iqr.to_csv('data_cleaned