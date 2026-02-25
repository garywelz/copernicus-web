# Extract features - reads glmp_features.csv, outputs glmp_feature_matrix.npy
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

df = pd.read_csv("glmp_features.csv")
num_cols = ["node_count", "conditional_count", "or_gates", "and_gates", "loops"]
avail = [c for c in num_cols if c in df.columns]
X = StandardScaler().fit_transform(df[avail].fillna(0).astype(float))
np.save("glmp_feature_matrix.npy", X)
print("Saved glmp_feature_matrix.npy")
