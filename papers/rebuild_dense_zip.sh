#!/usr/bin/env bash
# Rebuild Zenodo dense track A bundle (June 2026).
set -euo pipefail
cd "$(dirname "$0")"

OUT="dense_track_a_bundle_20260608.zip"

for f in \
  rankings_openai_dense.csv \
  table4_metrics_lexical_vs_openai.csv \
  run_dense_track_a.py \
  rankings_lexical.csv \
  judgments.csv \
  manifest.json \
  appendix_queries.json \
  appendix_queries.sha256 \
  openai_doc_embeddings.npz
do
  if [[ ! -f "$f" ]]; then
    echo "Missing required file: $f" >&2
    exit 1
  fi
done

rm -f "$OUT"
zip -j "$OUT" \
  rankings_openai_dense.csv \
  table4_metrics_lexical_vs_openai.csv \
  run_dense_track_a.py \
  rankings_lexical.csv \
  judgments.csv \
  manifest.json \
  appendix_queries.json \
  appendix_queries.sha256 \
  openai_doc_embeddings.npz

echo "Wrote $OUT ($(du -h "$OUT" | cut -f1))"
unzip -l "$OUT"
