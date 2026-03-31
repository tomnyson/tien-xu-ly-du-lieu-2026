import pandas as pd
from sklearn.preprocessing import LabelEncoder, OneHotEncoder

le = LabelEncoder()
ohe = OneHotEncoder(sparse_output=False)

df = pd.read_csv('ITA105_Slide_4.csv')
print(df.head())
df['housetype_len'] = le.fit_transform(df['HouseType'])
for label, encoded in zip(le.classes_, le.transform(le.classes_)):
    print(f"{label}: {encoded}")

region_encoded = ohe.fit_transform(df[['Region']])
region_ohe_sklearn =     pd.DataFrame(region_encoded, columns=ohe.get_feature_names_out())
print(region_ohe_sklearn.head())
