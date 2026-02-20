#!/bin/bash
# Progress Checker for Paper Acquisition
# Shows running processes and paper counts

cd /home/gdubs/copernicus-web-public/huggingface-space

echo "=== Paper Acquisition Progress ==="
echo ""

# Check running processes
RUNNING=$(ps aux | grep "acquire_" | grep -v grep | wc -l)
echo "Running processes: $RUNNING"
ps aux | grep "acquire_" | grep -v grep | awk '{print "  PID: " $2 " - " $11 " " $12 " " $13 " " $14 " " $15 " " $16}'
echo ""

# Count papers acquired
echo "Papers acquired so far:"
TOTAL=$(find metadata-database/papers -name "*.json" -type f 2>/dev/null | wc -l)
echo "  Total: $TOTAL"

# By source
PUBMED=$(find metadata-database/papers -name "pubmed_*.json" -type f 2>/dev/null | wc -l)
ARXIV=$(find metadata-database/papers -name "arxiv_*.json" -type f 2>/dev/null | wc -l)
CROSSREF=$(find metadata-database/papers -name "crossref_*.json" -type f 2>/dev/null | wc -l)
NASA_ADS=$(find metadata-database/papers -name "nasa_ads_*.json" -type f 2>/dev/null | wc -l)

echo "  PubMed: $PUBMED"
echo "  arXiv: $ARXIV"
echo "  Crossref: $CROSSREF"
echo "  NASA ADS: $NASA_ADS"
echo ""

# By discipline
echo "By discipline:"
BIOLOGY=$(find metadata-database/papers/biology -name "*.json" -type f 2>/dev/null | wc -l)
CHEMISTRY=$(find metadata-database/papers/chemistry -name "*.json" -type f 2>/dev/null | wc -l)
PHYSICS=$(find metadata-database/papers/physics -name "*.json" -type f 2>/dev/null | wc -l)
MATH=$(find metadata-database/papers/mathematics -name "*.json" -type f 2>/dev/null | wc -l)
CS=$(find metadata-database/papers/computer_science -name "*.json" -type f 2>/dev/null | wc -l)

echo "  Biology: $BIOLOGY"
echo "  Chemistry: $CHEMISTRY"
echo "  Physics: $PHYSICS"
echo "  Mathematics: $MATH"
echo "  Computer Science: $CS"
echo ""

# Check log files
echo "Recent log activity (last 5 lines each):"
echo ""
for log in paper_acquisition_logs/*.log; do
    if [ -f "$log" ]; then
        echo "=== $(basename $log) ==="
        tail -5 "$log" 2>/dev/null || echo "  (empty or error)"
        echo ""
    fi
done

echo "=== Targets ==="
echo "PubMed: 30,000 papers (15K recent + 15K classic)"
echo "arXiv: 10,000 papers (5K recent + 5K classic)"
echo "Total target: 40,000+ papers"
echo ""
echo "Progress: $TOTAL / 40,000 (%.1f%%)" | awk -v total=$TOTAL '{printf $1 " " $2 " " $3, total/40000*100}'
echo ""
