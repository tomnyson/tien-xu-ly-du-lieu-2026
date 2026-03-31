
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.preprocessing import MinMaxScaler, StandardScaler

DATASETS = {
    "Finance": "ITA105_Lab_3_Finance.csv",
    "Gaming": "ITA105_Lab_3_Gaming.csv",
    "Health": "ITA105_Lab_3_Health.csv",
    "Sports": "ITA105_Lab_3_Sports.csv",
}

OUTPUT_DIR = "lab3_outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def analyze_dataset(name, df):
    numeric_cols = df.select_dtypes(include=np.number).columns.tolist()
    print(f"\n{'='*80}\n{name}")
    print("Shape:", df.shape)
    print("Missing values:\n", df.isna().sum())

    desc = df[numeric_cols].describe().T
    desc["median"] = df[numeric_cols].median()
    desc["missing"] = df[numeric_cols].isna().sum()
    print("\nDescriptive statistics:")
    print(desc[["mean", "50%", "std", "min", "max", "median", "missing"]])

    # Outlier detection with IQR and Z-score
    print("\nOutlier summary:")
    for col in numeric_cols:
        q1, q3 = df[col].quantile([0.25, 0.75])
        iqr = q3 - q1
        lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        iqr_mask = (df[col] < lower) | (df[col] > upper)

        z = ((df[col] - df[col].mean()) / df[col].std(ddof=0)).abs()
        z_mask = z > 3

        print(f"{col}: IQR={iqr_mask.sum()} | Z-score={z_mask.sum()}")

        # Histogram + boxplot
        fig, axes = plt.subplots(1, 2, figsize=(10, 4))
        axes[0].hist(df[col], bins=15)
        axes[0].set_title(f"{name} - Histogram - {col}")
        axes[1].boxplot(df[col], vert=True)
        axes[1].set_title(f"{name} - Boxplot - {col}")
        plt.tight_layout()
        fig.savefig(os.path.join(OUTPUT_DIR, f"{name.lower()}_{col}_hist_box.png"), dpi=150)
        plt.close(fig)

    # Scaling
    minmax_df = pd.DataFrame(MinMaxScaler().fit_transform(df[numeric_cols]), columns=numeric_cols)
    zscore_df = pd.DataFrame(StandardScaler().fit_transform(df[numeric_cols]), columns=numeric_cols)

    minmax_df.to_csv(os.path.join(OUTPUT_DIR, f"{name.lower()}_minmax.csv"), index=False)
    zscore_df.to_csv(os.path.join(OUTPUT_DIR, f"{name.lower()}_zscore.csv"), index=False)

    # Distribution comparison
    for col in numeric_cols:
        fig, axes = plt.subplots(1, 3, figsize=(12, 4))
        axes[0].hist(df[col], bins=15)
        axes[0].set_title("Before")
        axes[1].hist(minmax_df[col], bins=15)
        axes[1].set_title("Min-Max")
        axes[2].hist(zscore_df[col], bins=15)
        axes[2].set_title("Z-Score")
        fig.suptitle(f"{name} - Distribution comparison - {col}")
        plt.tight_layout()
        fig.savefig(os.path.join(OUTPUT_DIR, f"{name.lower()}_{col}_compare.png"), dpi=150)
        plt.close(fig)

    # Dataset-specific scatterplots
    if name == "Finance":
        for tag, data in [("before", df), ("minmax", minmax_df), ("zscore", zscore_df)]:
            plt.figure(figsize=(5, 4))
            plt.scatter(data["doanh_thu_musd"], data["loi_nhuan_musd"], alpha=0.7)
            plt.xlabel("doanh_thu_musd")
            plt.ylabel("loi_nhuan_musd")
            plt.title(f"Finance {tag}: doanh_thu_musd vs loi_nhuan_musd")
            plt.tight_layout()
            plt.savefig(os.path.join(OUTPUT_DIR, f"finance_scatter_{tag}.png"), dpi=150)
            plt.close()

    if name == "Sports":
        plt.figure(figsize=(5, 4))
        plt.scatter(df["chieu_cao_cm"], df["can_nang_kg"], alpha=0.7)
        plt.xlabel("chieu_cao_cm")
        plt.ylabel("can_nang_kg")
        plt.title("Sports: chieu_cao_cm vs can_nang_kg")
        plt.tight_layout()
        plt.savefig(os.path.join(OUTPUT_DIR, "sports_scatter_height_weight.png"), dpi=150)
        plt.close()


def main():
    for name, filename in DATASETS.items():
        df = pd.read_csv(filename)
        analyze_dataset(name, df)
    print("\nDone. Check the lab3_outputs folder.")

if __name__ == "__main__":
    main()
