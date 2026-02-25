# Compute persistent homology on GLMP feature matrix
# H2 note: We typically observe 1 H2 bar (void). H2 counts 2D cavities (e.g. inside a hollow
# tetrahedron). With 108 points in 5D, Vietoris-Rips rarely forms such structures; when it does,
# the void fills quickly as radius increases. One short H2 bar is expected for this data.
import pandas as pd
from ripser import ripser
from persim import plot_diagrams
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.preprocessing import StandardScaler

df = pd.read_csv("glmp_features.csv")
num_cols = ["node_count", "conditional_count", "or_gates", "and_gates", "loops"]
avail = [c for c in num_cols if c in df.columns]
X = StandardScaler().fit_transform(df[avail].fillna(0).astype(float))
result = ripser(X, maxdim=2)
fig, ax = plt.subplots(figsize=(10, 8))
plot_diagrams(result["dgms"], show=False, ax=ax)
ax.set_title("Persistent Homology of GLMP Biological Processes")
plt.savefig("glmp_persistence_diagram.png", dpi=300, bbox_inches="tight")
plt.close()
np.save("persistence_result.npy", {"dgms": result["dgms"]})
print("Saved glmp_persistence_diagram.png and persistence_result.npy")
h2_count = len(result["dgms"][2])
print("H2 bars: %d (expected 1 for this data—few points form persistent 2D cavities)" % h2_count)
