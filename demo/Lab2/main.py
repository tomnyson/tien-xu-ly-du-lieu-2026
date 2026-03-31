
# ITA105 - LAB 2
# Giải bài tập phát hiện và xử lý ngoại lệ
# Chạy file này trong cùng thư mục với:
# - ITA105_Lab_2_Housing.csv
# - ITA105_Lab_2_Ecommerce.csv
# - ITA105_Lab_2_Iot.csv

from pathlib import Path
import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from scipy import stats

sns.set_theme(style="whitegrid")

BASE = Path(".")

housing = pd.read_csv("ITA105_Lab_2_Housing.csv")
ecom = pd.read_csv("ITA105_Lab_2_Ecommerce.csv")
iot = pd.read_csv("ITA105_Lab_2_Iot.csv")
iot["timestamp"] = pd.to_datetime(iot["timestamp"])

def numeric_summary(df):
    nums = df.select_dtypes(include=np.number)
    out = nums.describe().T[["mean", "std", "min", "50%", "max"]]
    return out.rename(columns={"50%": "median"})

def iqr_bounds(series):
    q1 = series.quantile(0.25)
    q3 = series.quantile(0.75)
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    return q1, q3, iqr, lower, upper

def iqr_mask(series):
    _, _, _, lower, upper = iqr_bounds(series)
    return (series < lower) | (series > upper)

def zscore_mask(series, threshold=3):
    z = np.abs(stats.zscore(series, nan_policy="omit"))
    return pd.Series(z > threshold, index=series.index)

def compare_outliers(df, cols):
    rows = []
    for col in cols:
        rows.append({
            "column": col,
            "iqr_outliers": int(iqr_mask(df[col]).sum()),
            "zscore_outliers": int(zscore_mask(df[col]).sum()),
            "boxplot_outliers": int(iqr_mask(df[col]).sum())  # boxplot ~= IQR whisker rule
        })
    return pd.DataFrame(rows)

print("=== BÀI 1: HOUSING ===")
print("Shape:", housing.shape)
print("Missing values:\n", housing.isna().sum())
print("\nThống kê mô tả:\n", numeric_summary(housing).round(2))
print("\nSo sánh số ngoại lệ:\n", compare_outliers(housing, ["dien_tich", "gia", "so_phong"]))

# Boxplot
fig, axes = plt.subplots(1, 3, figsize=(15, 4))
for ax, col in zip(axes, ["dien_tich", "gia", "so_phong"]):
    sns.boxplot(x=housing[col], ax=ax)
    ax.set_title(f"Boxplot {col}")
plt.tight_layout()
plt.show()

# Scatter diện tích - giá
housing["multi_iqr_housing"] = iqr_mask(housing["dien_tich"]) | iqr_mask(housing["gia"])
plt.figure(figsize=(7, 5))
sns.scatterplot(data=housing, x="dien_tich", y="gia", hue="multi_iqr_housing", palette={False: "steelblue", True: "red"})
plt.title("Housing: dien_tich vs gia")
plt.show()

# Chi tiết IQR cho từng biến
for col in ["dien_tich", "gia", "so_phong"]:
    q1, q3, iqr, low, up = iqr_bounds(housing[col])
    print(f"\n{col}:")
    print(f"Q1={q1:.2f}, Q3={q3:.2f}, IQR={iqr:.2f}, lower={low:.2f}, upper={up:.2f}")
    print(housing.loc[iqr_mask(housing[col]), [col]].sort_values(col))

# Xử lý: loại bỏ bản ghi sai rõ ràng rồi clip theo IQR
housing_clean = housing[(housing["dien_tich"] > 0) & (housing["gia"] > 0) & (housing["so_phong"] > 0)].copy()
for col in ["dien_tich", "gia", "so_phong"]:
    _, _, _, low, up = iqr_bounds(housing_clean[col])
    housing_clean[col] = housing_clean[col].clip(low, up)

print("\nSau xử lý Housing:\n", numeric_summary(housing_clean).round(2))

fig, axes = plt.subplots(1, 3, figsize=(15, 4))
for ax, col in zip(axes, ["dien_tich", "gia", "so_phong"]):
    sns.boxplot(x=housing_clean[col], ax=ax)
    ax.set_title(f"Boxplot sau xử lý - {col}")
plt.tight_layout()
plt.show()

print("\n=== BÀI 2: IOT ===")
print("Shape:", iot.shape)
print("Missing values:\n", iot.isna().sum())
print("\nThống kê mô tả:\n", numeric_summary(iot).round(2))

# Line plot temperature theo sensor
plt.figure(figsize=(12, 5))
sns.lineplot(data=iot, x="timestamp", y="temperature", hue="sensor_id")
plt.title("Temperature theo thời gian")
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()

# Rolling mean ± 3*std dùng 10 điểm trước đó (shift 1)
iot = iot.sort_values(["sensor_id", "timestamp"]).reset_index(drop=True)
for col in ["temperature", "pressure", "humidity"]:
    iot[f"{col}_roll_outlier"] = False
    iot[f"{col}_z_outlier"] = False
    iot[f"{col}_iqr_outlier"] = False

for sid, idx in iot.groupby("sensor_id").groups.items():
    g = iot.loc[idx].copy()
    for col in ["temperature", "pressure", "humidity"]:
        rm = g[col].rolling(window=10, min_periods=10).mean().shift(1)
        rs = g[col].rolling(window=10, min_periods=10).std().shift(1)
        roll_mask = ((g[col] < rm - 3*rs) | (g[col] > rm + 3*rs)).fillna(False)
        z_mask = zscore_mask(g[col])
        i_mask = iqr_mask(g[col])

        iot.loc[idx, f"{col}_roll_outlier"] = roll_mask.values
        iot.loc[idx, f"{col}_z_outlier"] = z_mask.values
        iot.loc[idx, f"{col}_iqr_outlier"] = i_mask.values

for col in ["temperature", "pressure", "humidity"]:
    print(f"\n{col}:")
    print("Rolling outliers =", int(iot[f"{col}_roll_outlier"].sum()))
    print("Z-score outliers =", int(iot[f'{col}_z_outlier'].sum()))
    print("IQR/Boxplot outliers =", int(iot[f'{col}_iqr_outlier'].sum()))

# Scatter plots
iot["temp_press_outlier"] = iot["temperature_iqr_outlier"] | iot["pressure_iqr_outlier"]
plt.figure(figsize=(7, 5))
sns.scatterplot(data=iot, x="temperature", y="pressure", hue="temp_press_outlier", palette={False: "steelblue", True: "red"})
plt.title("IoT: temperature vs pressure")
plt.show()

iot["press_hum_outlier"] = iot["pressure_iqr_outlier"] | iot["humidity_iqr_outlier"]
plt.figure(figsize=(7, 5))
sns.scatterplot(data=iot, x="pressure", y="humidity", hue="press_hum_outlier", palette={False: "steelblue", True: "red"})
plt.title("IoT: pressure vs humidity")
plt.show()

# Xử lý IoT: nội suy các điểm bất thường
iot_clean = iot.copy()
for sid, idx in iot_clean.groupby("sensor_id").groups.items():
    g = iot_clean.loc[idx].copy()
    for col in ["temperature", "pressure", "humidity"]:
        union_mask = g[f"{col}_roll_outlier"] | g[f"{col}_z_outlier"] | g[f"{col}_iqr_outlier"]
        g.loc[union_mask, col] = np.nan
        g[col] = g[col].interpolate(method="linear", limit_direction="both")
    iot_clean.loc[idx, ["temperature", "pressure", "humidity"]] = g[["temperature", "pressure", "humidity"]]

print("\nSau xử lý IoT:\n", numeric_summary(iot_clean).round(2))

plt.figure(figsize=(12, 5))
sns.lineplot(data=iot_clean, x="timestamp", y="temperature", hue="sensor_id")
plt.title("Temperature sau nội suy")
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()

print("\n=== BÀI 3: E-COMMERCE ===")
print("Shape:", ecom.shape)
print("Missing values:\n", ecom.isna().sum())
print("\nThống kê mô tả:\n", numeric_summary(ecom).round(2))
print("\nTần suất category:\n", ecom["category"].value_counts())

print("\nSo sánh số ngoại lệ:\n", compare_outliers(ecom, ["price", "quantity", "rating"]))

fig, axes = plt.subplots(1, 3, figsize=(15, 4))
for ax, col in zip(axes, ["price", "quantity", "rating"]):
    sns.boxplot(x=ecom[col], ax=ax)
    ax.set_title(f"Boxplot {col}")
plt.tight_layout()
plt.show()

ecom["multi_iqr_ecom"] = iqr_mask(ecom["price"]) | iqr_mask(ecom["quantity"]) | iqr_mask(ecom["rating"])
plt.figure(figsize=(7, 5))
sns.scatterplot(data=ecom, x="price", y="quantity", hue="multi_iqr_ecom", palette={False: "steelblue", True: "red"})
plt.title("E-commerce: price vs quantity")
plt.show()

print("\nCác dòng nghi ngờ lỗi nghiệp vụ:")
print(ecom[(ecom["price"] <= 0) | (ecom["quantity"] <= 0) | (ecom["rating"] > 5)])

# Xử lý: loại bỏ lỗi nhập liệu, sau đó clip price và quantity
ecom_clean = ecom[(ecom["price"] > 0) & (ecom["quantity"] > 0) & (ecom["rating"].between(1, 5))].copy()
for col in ["price", "quantity"]:
    _, _, _, low, up = iqr_bounds(ecom_clean[col])
    ecom_clean[col] = ecom_clean[col].clip(low, up)

print("\nSau xử lý E-commerce:\n", numeric_summary(ecom_clean).round(2))

fig, axes = plt.subplots(1, 3, figsize=(15, 4))
for ax, col in zip(axes, ["price", "quantity", "rating"]):
    sns.boxplot(x=ecom_clean[col], ax=ax)
    ax.set_title(f"Boxplot sau xử lý - {col}")
plt.tight_layout()
plt.show()

plt.figure(figsize=(7, 5))
sns.scatterplot(data=ecom_clean, x="price", y="quantity")
plt.title("price vs quantity sau xử lý")
plt.show()

print("\n=== BÀI 4: MULTIVARIATE OUTLIER ===")

housing_multi = iqr_mask(housing["dien_tich"]) | iqr_mask(housing["gia"])
iot_multi = iqr_mask(iot["temperature"]) | iqr_mask(iot["pressure"])
ecom_multi = iqr_mask(ecom["price"]) | iqr_mask(ecom["quantity"]) | iqr_mask(ecom["rating"])

print("Housing multivariate outliers:", int(housing_multi.sum()))
print("IoT multivariate outliers:", int(iot_multi.sum()))
print("E-commerce multivariate outliers:", int(ecom_multi.sum()))

print("\nNhận xét:")
print("- Housing: IQR phát hiện nhiều điểm hơn Z-score vì dữ liệu lệch mạnh do các giá trị cực lớn.")
print("- IoT: các spike 50°C, 5°C, 90% humidity lặp lại theo sensor gợi ý lỗi sensor hoặc calibration.")
print("- E-commerce: rating > 5 và giá/số lượng bằng 0 là lỗi nhập liệu rõ ràng; price/quantity quá lớn có thể là đơn bulk/premium.")
