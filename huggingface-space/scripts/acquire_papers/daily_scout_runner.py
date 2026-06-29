#!/usr/bin/env python3
"""
Daily Paper Scout Runner

Runs paper acquisition scripts with queries focused on recent, popular papers
from top journals. Designed to be triggered by Ralph Wiggum or scheduled daily.

Usage:
    python3 daily_scout_runner.py --source pubmed --query "Nature[JOUR]"
    python3 daily_scout_runner.py --all  # Run all sources
    python3 daily_scout_runner.py --config daily_scout_config.json
"""

import json
import os
import sys
import subprocess
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# Configuration — resolve repo-relative path (works on Jetson and local dev)
_SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = _SCRIPT_DIR.parent.parent
CONFIG_FILE = _SCRIPT_DIR / "daily_scout_config.json"
LOG_DIR = BASE_DIR / "paper_acquisition_logs" / "daily_scout"
QUERY_DIR = _SCRIPT_DIR / ".scout_query_cache"
LOG_DIR.mkdir(parents=True, exist_ok=True)
QUERY_DIR.mkdir(parents=True, exist_ok=True)


def python_bin() -> str:
    """Prefer paper_acquisition_venv on Jetson/WSL; fall back to system python3."""
    venv_python = BASE_DIR / "paper_acquisition_venv" / "bin" / "python3"
    if venv_python.exists():
        return str(venv_python)
    return "python3"

def load_config(config_path: Path) -> Dict:
    """Load configuration from JSON file."""
    if not config_path.exists():
        print(f"❌ Config file not found: {config_path}")
        sys.exit(1)
    
    with open(config_path, 'r') as f:
        return json.load(f)


def write_scout_query_files(config: Dict) -> Dict[str, Optional[Path]]:
    """
    Write per-source query JSON files for batch scripts to read.
    Temp-file approach keeps batch scripts decoupled from config schema changes.
    """
    paths: Dict[str, Optional[Path]] = {
        "pubmed": None,
        "arxiv": None,
        "biorxiv_medrxiv": None,
    }
    if config.get("pubmed_queries"):
        pubmed_path = QUERY_DIR / "scout_pubmed_queries.json"
        pubmed_path.write_text(json.dumps(config["pubmed_queries"], indent=2), encoding="utf-8")
        paths["pubmed"] = pubmed_path
    if config.get("arxiv_queries"):
        arxiv_path = QUERY_DIR / "scout_arxiv_queries.json"
        arxiv_path.write_text(json.dumps(config["arxiv_queries"], indent=2), encoding="utf-8")
        paths["arxiv"] = arxiv_path
    if config.get("biorxiv_config"):
        biorxiv_path = QUERY_DIR / "scout_biorxiv_config.json"
        biorxiv_path.write_text(json.dumps(config["biorxiv_config"], indent=2), encoding="utf-8")
        paths["biorxiv_medrxiv"] = biorxiv_path
    return paths


def run_pubmed_recent(log_file: Path, count: int = 100, config_queries: Optional[Path] = None) -> bool:
    """Run PubMed acquisition for recent papers."""
    cmd = [
        python_bin(),
        str(_SCRIPT_DIR / 'acquire_pubmed_batch.py'),
        '--recent', str(count),
        '--classic', '0',
    ]
    if config_queries:
        cmd.extend(['--config-queries', str(config_queries)])
    
    print(f"  Running PubMed recent papers acquisition")
    print(f"    Target: {count} recent papers")
    
    try:
        with open(log_file, 'a') as log:
            log.write(f"\n{'='*80}\n")
            log.write(f"PubMed Recent Papers - {datetime.now().isoformat()}\n")
            log.write(f"{'='*80}\n")
            result = subprocess.run(
                cmd,
                cwd=str(BASE_DIR),
                stdout=log,
                stderr=subprocess.STDOUT,
                timeout=3600  # 60 minute timeout
            )
            return result.returncode == 0
    except subprocess.TimeoutExpired:
        print(f"    ⚠️  Acquisition timed out after 60 minutes")
        return False
    except Exception as e:
        print(f"    ❌ Error: {e}")
        return False

def run_arxiv_recent(log_file: Path, count: int = 100, config_queries: Optional[Path] = None) -> bool:
    """Run arXiv acquisition for recent papers."""
    cmd = [
        python_bin(),
        str(_SCRIPT_DIR / 'acquire_arxiv_batch.py'),
        '--recent', str(count),
        '--classic', '0',
    ]
    if config_queries:
        cmd.extend(['--config-queries', str(config_queries)])
    
    print(f"  Running arXiv recent papers acquisition")
    print(f"    Target: {count} recent papers")
    
    try:
        with open(log_file, 'a') as log:
            log.write(f"\n{'='*80}\n")
            log.write(f"arXiv Recent Papers - {datetime.now().isoformat()}\n")
            log.write(f"{'='*80}\n")
            result = subprocess.run(
                cmd,
                cwd=str(BASE_DIR),
                stdout=log,
                stderr=subprocess.STDOUT,
                timeout=3600
            )
            return result.returncode == 0
    except Exception as e:
        print(f"    ❌ Error: {e}")
        return False

def run_biorxiv_medrxiv_recent(log_file: Path, count: int = 100, config_queries: Optional[Path] = None) -> bool:
    """Run BioRxiv/MedRxiv acquisition for recent preprints."""
    cmd = [
        python_bin(),
        str(_SCRIPT_DIR / 'acquire_biorxiv_medrxiv_batch.py'),
        '--recent', str(count),
    ]
    if config_queries:
        cmd.extend(['--config-queries', str(config_queries)])
    
    print(f"  Running BioRxiv/MedRxiv recent preprint acquisition")
    print(f"    Target: {count} recent preprints")
    
    try:
        with open(log_file, 'a') as log:
            log.write(f"\n{'='*80}\n")
            log.write(f"BioRxiv/MedRxiv Recent Preprints - {datetime.now().isoformat()}\n")
            log.write(f"{'='*80}\n")
            result = subprocess.run(
                cmd,
                cwd=str(BASE_DIR),
                stdout=log,
                stderr=subprocess.STDOUT,
                timeout=3600
            )
            return result.returncode == 0
    except subprocess.TimeoutExpired:
        print(f"    ⚠️  Acquisition timed out after 60 minutes")
        return False
    except Exception as e:
        print(f"    ❌ Error: {e}")
        return False

def run_nasa_ads_recent(log_file: Path, count: int = 100) -> bool:
    """Run NASA ADS acquisition (requires NASA_ADS_API_TOKEN or Secret Manager)."""
    cmd = [
        python_bin(),
        str(_SCRIPT_DIR / 'acquire_nasa_ads_batch.py'),
        '--count', str(count),
    ]
    print(f"  Running NASA ADS paper acquisition")
    print(f"    Target: {count} papers")
    try:
        with open(log_file, 'a') as log:
            log.write(f"\n{'='*80}\n")
            log.write(f"NASA ADS - {datetime.now().isoformat()}\n")
            log.write(f"{'='*80}\n")
            result = subprocess.run(
                cmd,
                cwd=str(BASE_DIR),
                stdout=log,
                stderr=subprocess.STDOUT,
                timeout=3600
            )
            return result.returncode == 0
    except subprocess.TimeoutExpired:
        print(f"    ⚠️  NASA ADS acquisition timed out after 60 minutes")
        return False
    except Exception as e:
        print(f"    ❌ Error: {e}")
        return False

def run_daily_scout(config: Dict) -> Dict:
    """Run the daily scout collection across all sources."""
    print(f"\n{'='*80}")
    print(f"Daily Paper Scout - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}\n")
    
    results = {
        'date': datetime.now().isoformat(),
        'sources': {},
        'total_papers': 0,
        'success': True
    }
    
    # Process sources in priority order
    sources = sorted(
        [(k, v) for k, v in config['sources'].items() if v.get('enabled', False)],
        key=lambda x: x[1].get('priority', 999)
    )
    
    query_paths = write_scout_query_files(config)
    if any(query_paths.values()):
        print("📋 Config queries written to:", QUERY_DIR)

    # Per-run limits — v2 config uses top-level volume + source_weights
    volume = config.get('volume', config.get('limits', {}))
    base_per_source = int(volume.get('papers_per_source_per_run', volume.get('papers_per_source_per_day', 750)))
    total_cap = volume.get('total_papers_per_run', volume.get('total_papers_per_day', 1000))
    source_weights = config.get('source_weights', volume.get('source_weights', {}))
    n_sources = len(sources)
    source_targets = {}
    if total_cap is not None and n_sources > 0 and source_weights:
        enabled_weights = {
            name: max(0.0, float(source_weights.get(name, source_config.get('budget_weight', 0))))
            for name, source_config in sources
        }
        total_weight = sum(enabled_weights.values())
        if total_weight > 0:
            for name, _source_config in sources:
                weighted_target = max(1, round(int(total_cap) * enabled_weights[name] / total_weight))
                source_targets[name] = min(base_per_source, weighted_target)
            print(
                f"📊 Per-run budget: up to {total_cap} total / {n_sources} source(s) "
                f"using configured weights → "
                + ", ".join(f"{name}: {count}" for name, count in source_targets.items())
                + f" (per-source cap {base_per_source})."
            )
        else:
            source_weights = {}
    
    if total_cap is not None and n_sources > 0 and not source_weights:
        # Split the run budget evenly across enabled sources, never exceeding base_per_source.
        per_source_from_cap = max(1, int(total_cap) // n_sources)
        source_targets = {name: min(base_per_source, per_source_from_cap) for name, _source_config in sources}
        print(f"📊 Per-run budget: up to {total_cap} total / {n_sources} source(s) → {per_source_from_cap} per source (cap {base_per_source} each).")
    else:
        if not source_targets:
            source_targets = {name: base_per_source for name, _source_config in sources}
            print(f"📊 {base_per_source} papers per enabled source (no total_papers_per_run split).")
    
    for source_name, source_config in sources:
        print(f"\n📚 Source: {source_name.upper()}")
        print(f"{'-'*80}")
        
        papers_for_source = source_targets[source_name]
        source_results = {
            'papers_targeted': papers_for_source,
            'success': False
        }
        
        log_file = LOG_DIR / f"{source_name}_{datetime.now().strftime('%Y%m%d')}.log"
        
        use_config = source_config.get('use_config_queries', True)
        qpath = query_paths.get(source_name) if use_config else None

        if source_name == 'pubmed':
            success = run_pubmed_recent(log_file, papers_for_source, qpath)
        elif source_name == 'biorxiv_medrxiv':
            success = run_biorxiv_medrxiv_recent(log_file, papers_for_source, qpath)
        elif source_name == 'arxiv':
            success = run_arxiv_recent(log_file, papers_for_source, qpath)
        elif source_name == 'nasa_ads':
            success = run_nasa_ads_recent(log_file, papers_for_source)
        else:
            print(f"  ⚠️  Unknown source: {source_name}")
            success = False
        
        source_results['success'] = success
        if success:
            print(f"    ✅ Success")
        else:
            print(f"    ❌ Failed (check logs: {log_file})")
        
        results['sources'][source_name] = source_results
        
        # Rate limiting between sources
        if source_name != sources[-1][0]:  # Don't wait after last source
            print(f"  ⏳ Waiting 10 seconds before next source...")
            time.sleep(10)
    
    # Overall run success only if every enabled source succeeded
    results['success'] = all(
        s.get('success', False) for s in results['sources'].values()
    )
    
    print(f"\n{'='*80}")
    print(f"Daily Scout Complete - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}\n")
    
    # Save results summary
    summary_file = LOG_DIR / f"summary_{datetime.now().strftime('%Y%m%d')}.json"
    with open(summary_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    return results

def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Daily Paper Scout Runner")
    parser.add_argument('--config', type=str, default=str(CONFIG_FILE),
                       help='Path to configuration file')
    parser.add_argument('--source', type=str, choices=['pubmed', 'arxiv', 'nasa_ads'],
                       help='Run only a specific source')
    parser.add_argument('--all', action='store_true',
                       help='Run all enabled sources (default)')
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(Path(args.config))
    
    # venv is selected automatically via python_bin() for subprocess calls
    if args.source:
        # Filter to single source
        config['sources'] = {args.source: config['sources'].get(args.source, {})}
        config['sources'][args.source]['enabled'] = True
    
    results = run_daily_scout(config)
    
    # Print summary
    print("\n📊 Summary:")
    for source_name, source_results in results['sources'].items():
        status = "✅ Success" if source_results.get('success', False) else "❌ Failed"
        papers = source_results.get('papers_targeted', 'N/A')
        print(f"  {source_name}: {status} (targeted {papers} papers)")
    
    any_failed = not results.get('success', True)
    if any_failed:
        print("\n⚠️  One or more sources failed; see logs in:", LOG_DIR)
    sys.exit(0 if results.get('success', False) else 1)

if __name__ == '__main__':
    main()
