import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
from scipy import stats

# 1. Đọc dữ liệu
df = pd.read_csv('ITA105_Slide_2.csv')

# Q1 = df.quantile(0.25)
# Q3 = df.quantile(0.75)
# IQR = Q3 - Q1
# lower_bound = Q1 - 1.5 * IQR
# upper_bound = Q3 + 1.5 * IQR
# outliers_iqr = df[(df['Price'] < lower_bound['Price']) | (df['Price'] > upper_bound['Price'])]
# print('lower_bound:', lower_bound['Price'])
# print('upper_bound:', upper_bound['Price'])
# print(f"Số lượng ngoại lệ theo IQR: {len(outliers_iqr)}")

cols = ['Area', 'Rooms', 'Price']
for col in cols:
    Q1 = df[col].quantile(0.25)
    Q3 = df[col].quantile(0.75)
    IQR = Q3 - Q1
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR
    outliers = df[(df[col] < lower_bound) | (df[col] > upper_bound)]
    print(f"Số lượng ngoại lệ theo IQR cho {col}: {len(outliers)}")

df_zscore = df.copy()
for col in cols:
    z_scores = np.abs(stats.zscore(df_zscore[col]))
    ## theo de yeu cau nguong >3
    df_zscore = df_zscore[z_scores < 3]
    print(f"Số lượng dòng sau khi dùng Z-Score cho {col}: {len(df_zscore)}")

# ve boxplot va scatter plot sau khi loc IQR
plt.figure(figsize=(8, 5))
sns.boxplot(x=df['Price'])
plt.title('Boxplot của Price (Trước khi xử lý)')
plt.show()
#Sử dụng Scatter
plt.figure(figsize=(8,6))
# Vẽ scatter plot
sns.scatterplot(x='Area', y='Price', data=df)
plt.title('Scatterplot: Diện tích vs Giá')
# Nhãn trục x
plt.xlabel('Diện tích (m²)')
# Nhãn trục y
plt.ylabel('Giá nhà')
plt.show()