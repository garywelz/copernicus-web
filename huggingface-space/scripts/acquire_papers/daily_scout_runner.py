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

# Configuration
BASE_DIR = Path("/home/gdubs/copernicus-web-public/huggingface-space")
CONFIG_FILE = BASE_DIR / "scripts" / "acquire_papers" / "daily_scout_config.json"
LOG_DIR = BASE_DIR / "paper_acquisition_logs" / "daily_scout"
LOG_DIR.mkdir(parents=True, exist_ok=True)

def load_config(config_path: Path) -> Dict:
    """Load configuration from JSON file."""
    if not config_path.exists():
        print(f"❌ Config file not found: {config_path}")
        sys.exit(1)
    
    with open(config_path, 'r') as f:
        return json.load(f)

def run_pubmed_recent(log_file: Path, count: int = 100) -> bool:
    """Run PubMed acquisition for recent papers."""
    # Use existing script with --recent flag (small batch for daily collection)
    # Pass --classic 0 to prevent acquiring classic papers
    cmd = [
        'python3',
        str(BASE_DIR / 'scripts' / 'acquire_papers' / 'acquire_pubmed_batch.py'),
        '--recent', str(count),  # Small daily batch
        '--classic', '0',  # Don't acquire classic papers in daily scout
    ]
    
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

def run_arxiv_recent(log_file: Path, count: int = 100) -> bool:
    """Run arXiv acquisition for recent papers."""
    # Use existing script with --recent flag (small batch for daily collection)
    # Pass --classic 0 to prevent acquiring classic papers
    cmd = [
        'python3',
        str(BASE_DIR / 'scripts' / 'acquire_papers' / 'acquire_arxiv_batch.py'),
        '--recent', str(count),  # Small daily batch
        '--classic', '0',  # Don't acquire classic papers in daily scout
    ]
    
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
    
    # Get daily limits from config
    limits = config.get('limits', {})
    papers_per_source = limits.get('papers_per_source_per_day', 100)
    
    for source_name, source_config in sources:
        print(f"\n📚 Source: {source_name.upper()}")
        print(f"{'-'*80}")
        
        source_results = {
            'papers_targeted': papers_per_source,
            'success': False
        }
        
        log_file = LOG_DIR / f"{source_name}_{datetime.now().strftime('%Y%m%d')}.log"
        
        if source_name == 'pubmed':
            success = run_pubmed_recent(log_file, papers_per_source)
        elif source_name == 'arxiv':
            success = run_arxiv_recent(log_file, papers_per_source)
        elif source_name == 'nasa_ads':
            # TODO: Implement NASA ADS runner
            print(f"  ⚠️  NASA ADS acquisition not yet implemented in daily scout")
            print(f"  💡 Run manually: python3 acquire_nasa_ads_batch.py --count {papers_per_source}")
            success = False
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
    
    # Activate virtual environment if available
    venv_python = BASE_DIR / 'paper_acquisition_venv' / 'bin' / 'python3'
    if venv_python.exists():
        # If running in venv, use venv python
        # For now, assume we're already in the right environment
        pass
    
    # Run the scout
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
    
    sys.exit(0 if results['success'] else 1)

if __name__ == '__main__':
    main()
