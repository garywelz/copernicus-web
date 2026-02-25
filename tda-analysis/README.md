# TDA Analysis of GLMP Biological Processes

Topological data analysis (TDA) on 108 genetic regulatory circuits from the [Genome Logic Modeling Project](https://github.com/garywelz/glmp). Uses persistent homology (Vietoris-Rips, Ripser) to detect structural patterns—notably, that feedback circuits (lac operon, two-component signaling, SOS response) appear in the most persistent H1 loops.

**Collaboration:** Dr. Mikael Vejdemo-Johansson, CUNY Graduate Center. Part of the CopernicusAI / NSF CISE proposal.

## Quick Start

```bash
# Setup
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Run pipeline
python fetch_glmp_data.py      # Fetches metadata, adds flowchart loop counts, produces glmp_features.csv
python add_loops_to_features.py  # (Or run automatically via fetch) Adds loops = back-edges per process
python compute_persistence.py  # Ripser with 6 features (incl. loops), produces glmp_persistence_diagram.png
python generate_report.py     # HTML report

# H1 loop analysis (maps loops to specific processes)
python analyze_h1_loops.py     # Produces h1_loop_results.json

# H1 loop visualization (makes homology visible)
python visualize_h1_loops.py   # Produces PNG, interactive HTML, Mapper graph
```

## Outputs

| File | Description |
|------|-------------|
| `glmp_features.csv` | 108 processes, feature matrix (nodes, conditionals, gates, **loops**) |
| `glmp_persistence_diagram.png` | Persistence diagram (H0, H1, H2) |
| `glmp_tda_report.html` | Summary report |
| `glmp_h1_loops_2d.png` | PCA projection with H1 cocycle edges drawn as cycles |
| `glmp_h1_loops_interactive.html` | Interactive Plotly plot (hover for process names) |
| `glmp_mapper_graph.png` | Mapper graph: clusters as nodes, overlaps as edges |
| `glmp_mapper_graph_interactive.html` | Interactive Mapper (hover nodes to see processes) |
| `H1_LOOP_ANALYSIS.pdf` | Top 5 H1 loops mapped to biological processes |
| `BIOLOGICAL_COHERENCE_CHECK.pdf` | Does topology capture known feedback circuits? |
| `ADDENDUM_FOR_VEJDEMO_JOHANSSON.pdf` | Methods, persistence values, discussion questions |
| `ONE_PAGE_SUMMARY.pdf` | One-page overview |

## Key Finding

The most persistent H1 loop (persistence = 0.330) includes ara operon, SOS response, stringent response, catabolite repression, Pho regulon, quorum sensing. Loop #3 contains **lac operon**; Loop #5 contains **two-component EnvZ-OmpR signaling**. This suggests TDA on structural features detects regulatory architecture.

## Regenerating PDFs

```bash
./make_pdfs.sh
```

Requires `pandoc` and `pdflatex`.

## Flowchart Loop Count (6th Feature)

**Definition:** A loop = back-edge: an edge u→v where v is at an earlier layer than u. Layers are computed via BFS from source nodes (in-degree 0). Self-loops count as 1 each.

- `count_flowchart_loops.py` – parses Mermaid, counts back-edges
- `add_loops_to_features.py` – adds `loops` column to glmp_features.csv
- `build_metadata_with_loops.py` – merges loops into metadata for the database table
- `glmp-database-table.html` – table with Loops column (deploy to GCS)

To add loops to the live GLMP database table:
1. Run `python build_metadata_with_loops.py` (after fetch + add_loops)
2. Upload `metadata_with_loops.json` to GCS as `glmp-v2/data/metadata.json`
3. Upload `glmp-database-table.html` to GCS as `glmp-database-table.html`

## Data Source

GLMP metadata: `https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/glmp-v2/data/metadata.json`
