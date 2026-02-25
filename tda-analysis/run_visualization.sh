#!/bin/bash
# Run full TDA pipeline including loop counts and H1 visualizations.
cd "$(dirname "$0")"
source venv/bin/activate
python fetch_glmp_data.py          # Fetches metadata, adds loops column via add_loops_to_features
python compute_persistence.py      # Ripser with 6 features (incl. loops)
python visualize_h1_loops.py
echo "Outputs: glmp_features.csv (with loops), glmp_h1_loops_2d.png, glmp_h1_loops_interactive.html, glmp_mapper_graph.png, glmp_mapper_graph_interactive_v2.html"
