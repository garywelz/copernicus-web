"""Visualize H1 loops: project to 2D and draw cocycle edges to make homology visible."""

import numpy as np
import pandas as pd
from ripser import ripser
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import os

try:
    import networkx as nx
    HAS_NX = True
except ImportError:
    HAS_NX = False


def load_data(csv_path="glmp_features.csv"):
    df = pd.read_csv(csv_path)
    num_cols = ["node_count", "conditional_count", "or_gates", "and_gates", "loops"]
    avail = [c for c in num_cols if c in df.columns]
    X = StandardScaler().fit_transform(df[avail].fillna(0).astype(float))
    return X, df


def get_edges(cocycle):
    edges = set()
    if cocycle.ndim == 2:
        for row in cocycle:
            i, j = int(row[0]), int(row[1])
            edges.add((min(i, j), max(i, j)))
    return list(edges)


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    if not os.path.exists("glmp_features.csv"):
        print("Run fetch_glmp_data.py first")
        return

    X, df = load_data()
    result = ripser(X, maxdim=2, do_cocycles=True)
    h1 = result["dgms"][1]
    cocycles = result["cocycles"][1]
    pers = h1[:, 1] - h1[:, 0]
    top = np.argsort(-pers)[:5]  # All top 5 H1 loops

    pca = PCA(n_components=2, random_state=42)
    X2d = pca.fit_transform(X)

    fig, ax = plt.subplots(figsize=(12, 10))
    ax.scatter(X2d[:, 0], X2d[:, 1], c="#cccccc", s=25, alpha=0.7)

    colors = ["#e41a1c", "#377eb8", "#4daf4a", "#984ea3", "#ff7f00"]  # red, blue, green, purple, orange
    for k, idx in enumerate(top):
        edges = get_edges(cocycles[idx])
        verts = set(i for i, j in edges) | set(j for i, j in edges)
        for i, j in edges:
            ax.plot([X2d[i, 0], X2d[j, 0]], [X2d[i, 1], X2d[j, 1]], c=colors[k], lw=2, alpha=0.8)
        v = np.array(list(verts))
        ax.scatter(X2d[v, 0], X2d[v, 1], c=colors[k], s=80, alpha=0.9, edgecolors="black", linewidths=0.5,
                   label="Loop #%d (pers=%.3f)" % (k + 1, pers[idx]))

    key = ["ecoli_lac_operon", "ecoli_e._coli_two_component_signaling", "ecoli_sos_response"]
    for pid in key:
        m = df["process_id"] == pid
        if m.any():
            i = df[m].index[0]
            ax.annotate(df.iloc[i]["process_name"][:25], (X2d[i, 0], X2d[i, 1]), fontsize=8, xytext=(5, 5),
                        textcoords="offset points")

    ax.set_xlabel("PC1")
    ax.set_ylabel("PC2")
    ax.set_title("H1 Loops in GLMP Feature Space (PCA)\nCocycle edges show cycle structure")
    ax.legend()
    ax.set_aspect("equal")
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig("glmp_h1_loops_2d.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("Saved glmp_h1_loops_2d.png")

    plot_interactive_html(X2d, df, result, top, cocycles, pers)
    plot_mapper_graph(X, df, result)


def plot_interactive_html(X2d, df, result, top, cocycles, pers, out_path="glmp_h1_loops_interactive.html"):
    """Interactive Plotly HTML with hover on processes and loop highlighting."""
    try:
        import plotly.graph_objects as go
        import plotly.express as px
    except ImportError:
        print("Skipping interactive HTML (plotly not installed)")
        return

    fig = go.Figure()

    colors = ["#e41a1c", "#377eb8", "#4daf4a", "#984ea3", "#ff7f00"]
    loop_labels = []
    for k, idx in enumerate(top):
        edges = get_edges(cocycles[idx])
        verts = set(i for i, j in edges) | set(j for i, j in edges)
        loop_labels.append(verts)

    hover_text = []
    loop_membership = []
    for i in range(len(df)):
        name = df.iloc[i]["process_name"]
        pid = df.iloc[i]["process_id"]
        org = df.iloc[i]["organism"]
        loops = []
        for k, verts in enumerate(loop_labels):
            if i in verts:
                loops.append(str(k + 1))
        loop_membership.append(loops)
        hover_text.append("<b>%s</b><br>%s<br>Organism: %s<br>Loops: %s" % (
            name, pid, org, ", ".join(loops) if loops else "none"))

    fig.add_trace(go.Scatter(
        x=X2d[:, 0], y=X2d[:, 1],
        mode="markers",
        marker=dict(size=8, color="#cccccc", opacity=0.8),
        hovertext=hover_text,
        hoverinfo="text",
        name="All processes",
    ))

    for k, idx in enumerate(top):
        verts = np.array(list(loop_labels[k]))
        edge_x, edge_y = [], []
        edges = get_edges(cocycles[idx])
        for i, j in edges:
            edge_x.extend([X2d[i, 0], X2d[j, 0], None])
            edge_y.extend([X2d[i, 1], X2d[j, 1], None])
        fig.add_trace(go.Scatter(x=edge_x, y=edge_y, mode="lines",
                                line=dict(color=colors[k], width=2, dash="solid"),
                                name="Loop #%d edges (pers=%.3f)" % (k + 1, pers[idx])))
        fig.add_trace(go.Scatter(
            x=X2d[verts, 0], y=X2d[verts, 1],
            mode="markers",
            marker=dict(size=14, color=colors[k], line=dict(width=1, color="black")),
            name="Loop #%d vertices (n=%d)" % (k + 1, len(verts)),
        ))

    fig.update_layout(
        title="H1 Loops in GLMP Feature Space (PCA) - Interactive",
        xaxis_title="PC1",
        yaxis_title="PC2",
        showlegend=True,
        hovermode="closest",
        template="plotly_white",
    )
    fig.write_html(out_path)
    print("Saved %s" % out_path)


def plot_mapper_graph(X, df, result, out_path="glmp_mapper_graph.png"):
    """Mapper-style graph: clusters as nodes, overlaps as edges. Loops become visible."""
    try:
        import kmapper as km
    except ImportError:
        print("Skipping Mapper (kmapper not installed)")
        return

    mapper = km.KeplerMapper(verbose=0)
    lens = mapper.fit_transform(X, projection=PCA(n_components=2, random_state=42))
    # Richer graph: n_cubes=12, perc_overlap=0.65 -> 18 nodes, 45 edges (same for static PNG and interactive HTML)
    graph = mapper.map(lens, X, cover=km.Cover(n_cubes=12, perc_overlap=0.65))
    nodes = graph["nodes"]
    links = graph["links"]

    # Interactive KeplerMapper HTML — click a node to see which processes are in each cluster
    tooltips = np.array([str(df.iloc[i]["process_name"]) for i in range(len(df))])
    mapper.visualize(
        graph,
        path_html=out_path.replace(".png", "_interactive_v2.html"),
        title="GLMP Mapper Graph - Click a node to see processes in that cluster",
        custom_tooltips=tooltips,
        X=X,
        X_names=["node_count", "conditional_count", "or_gates", "and_gates", "loops"],
        include_searchbar=True,
    )
    print("Saved %s" % out_path.replace(".png", "_interactive_v2.html"))

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(12, 10))
    G = nx.Graph()
    for node_id, members in nodes.items():
        G.add_node(node_id, size=len(members))
    for n1 in links:
        for n2 in links[n1]:
            G.add_edge(n1, n2)

    pos = nx.spring_layout(G, k=1.5, seed=42)
    sizes = [300 + 50 * len(nodes[n]) for n in G.nodes()]
    nx.draw_networkx_nodes(G, pos, node_size=sizes, node_color="#4fc3f7", ax=ax)
    nx.draw_networkx_edges(G, pos, ax=ax, width=2, alpha=0.7)
    nx.draw_networkx_labels(G, pos, {n: "n=%d" % len(nodes[n]) for n in G.nodes()}, ax=ax, font_size=9)
    ax.set_title("Mapper Graph of GLMP Processes\nNodes = clusters, Edges = overlap. Loops visible as cycles.")
    ax.axis("off")
    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()
    print("Saved %s" % out_path)


if __name__ == "__main__":
    main()
