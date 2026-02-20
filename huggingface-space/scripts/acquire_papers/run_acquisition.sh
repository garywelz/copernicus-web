#!/bin/bash
# Paper Acquisition Background Runner
# Starts all paper acquisition scripts in background with logging

cd /home/gdubs/copernicus-web-public/huggingface-space
source paper_acquisition_venv/bin/activate

LOG_DIR="paper_acquisition_logs"
mkdir -p "$LOG_DIR"

echo "Starting paper acquisition scripts in background..."
echo "Logs will be in: $LOG_DIR/"
echo ""

# PubMed: Start with smaller batches (rate limited to 3 req/sec without API key)
# Target: 30,000 papers (15K recent + 15K classic)
echo "Starting PubMed acquisition (recent papers)..."
nohup python3 scripts/acquire_papers/acquire_pubmed_batch.py --recent 15000 > "$LOG_DIR/pubmed_recent.log" 2>&1 &
echo "  PID: $! (log: $LOG_DIR/pubmed_recent.log)"

sleep 5

echo "Starting PubMed acquisition (classic papers)..."
nohup python3 scripts/acquire_papers/acquire_pubmed_batch.py --classic 15000 > "$LOG_DIR/pubmed_classic.log" 2>&1 &
echo "  PID: $! (log: $LOG_DIR/pubmed_classic.log)"

sleep 5

# arXiv: Target 10,000 papers (5K recent + 5K classic)
echo "Starting arXiv acquisition (recent papers)..."
nohup python3 scripts/acquire_papers/acquire_arxiv_batch.py --recent 5000 > "$LOG_DIR/arxiv_recent.log" 2>&1 &
echo "  PID: $! (log: $LOG_DIR/arxiv_recent.log)"

sleep 5

echo "Starting arXiv acquisition (classic papers)..."
nohup python3 scripts/acquire_papers/acquire_arxiv_batch.py --classic 5000 > "$LOG_DIR/arxiv_classic.log" 2>&1 &
echo "  PID: $! (log: $LOG_DIR/arxiv_classic.log)"

sleep 5

# Crossref: Skip for now (API query format needs debugging)
# Can be run manually later with journal ISSN searches
# echo "Starting Crossref acquisition..."
# nohup python3 scripts/acquire_papers/acquire_crossref_batch.py --query "machine learning" --count 5000 > "$LOG_DIR/crossref.log" 2>&1 &
# echo "  PID: $! (log: $LOG_DIR/crossref.log)"

echo ""
echo "All acquisition scripts started in background!"
echo "Monitor progress with: tail -f $LOG_DIR/*.log"
echo "Check running processes: ps aux | grep acquire_"
