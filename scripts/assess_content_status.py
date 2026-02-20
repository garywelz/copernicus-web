#!/usr/bin/env python3
"""
Quick assessment script to check current content status across all systems.

This script checks:
1. Research Paper Metadata Database (PostgreSQL)
2. Science Video Database (PostgreSQL) - if accessible
3. CopernicusAI Firestore (papers and podcasts)
"""

import sys
from pathlib import Path
from typing import Dict, Any

# Add cloud-run-backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "cloud-run-backend"))

def assess_research_papers_postgres() -> Dict[str, Any]:
    """Assess research papers in PostgreSQL database."""
    print("\n" + "="*70)
    print("1. RESEARCH PAPER METADATA DATABASE (PostgreSQL)")
    print("="*70)
    
    try:
        # Try to import and check
        sys.path.insert(0, "/home/gdubs/copernicusai-research-metadata")
        from app.core.database import SessionLocal
        from app.models.paper import Paper
        from sqlalchemy import func
        from collections import Counter
        
        db = SessionLocal()
        try:
            total = db.query(Paper).count()
            print(f"✅ Total papers: {total}")
            
            # Math papers
            all_papers = db.query(Paper).all()
            math_papers = sum(1 for p in all_papers if p.categories and any(cat.startswith('math.') for cat in p.categories))
            print(f"✅ Mathematics papers: {math_papers}")
            
            # Category distribution
            category_counter = Counter()
            for paper in all_papers:
                if paper.categories:
                    for cat in paper.categories:
                        if cat.startswith('math.'):
                            category_counter[cat] += 1
            
            if category_counter:
                print(f"\n📊 Top math categories:")
                for cat, count in category_counter.most_common(10):
                    print(f"   {cat}: {count}")
            else:
                print("⚠️  No math categories found")
            
            # Sample papers
            samples = db.query(Paper).limit(3).all()
            if samples:
                print(f"\n📄 Sample papers:")
                for i, paper in enumerate(samples, 1):
                    print(f"   {i}. {paper.title[:60]}...")
                    print(f"      arXiv ID: {paper.arxiv_id}")
                    print(f"      Categories: {', '.join(paper.categories[:3]) if paper.categories else 'None'}")
            
            return {
                "status": "success",
                "total_papers": total,
                "math_papers": math_papers,
                "categories": dict(category_counter)
            }
        finally:
            db.close()
            
    except ImportError as e:
        print(f"⚠️  Cannot access PostgreSQL database: {e}")
        print("   Make sure you're in the right environment and database is accessible")
        return {"status": "error", "error": str(e)}
    except Exception as e:
        print(f"❌ Error assessing PostgreSQL: {e}")
        return {"status": "error", "error": str(e)}


def assess_firestore() -> Dict[str, Any]:
    """Assess content in CopernicusAI Firestore."""
    print("\n" + "="*70)
    print("2. COPERNICUSAI FIRESTORE")
    print("="*70)
    
    try:
        from mcp_server.utils.firestore_client import get_firestore_client
        
        db = get_firestore_client()
        
        # Check research papers
        papers_ref = db.collection('research_papers')
        papers = list(papers_ref.stream())
        papers_with_embeddings = sum(1 for p in papers if p.to_dict().get('embedding') is not None)
        
        print(f"✅ Research papers: {len(papers)}")
        print(f"✅ Papers with embeddings: {papers_with_embeddings}")
        
        # Check podcasts
        podcasts_ref = db.collection('podcast_jobs')
        podcasts = list(podcasts_ref.stream())
        podcasts_with_embeddings = sum(1 for p in podcasts if p.to_dict().get('embedding') is not None)
        
        print(f"✅ Podcasts: {len(podcasts)}")
        print(f"✅ Podcasts with embeddings: {podcasts_with_embeddings}")
        
        # Sample papers
        if papers:
            print(f"\n📄 Sample papers in Firestore:")
            for i, paper_doc in enumerate(papers[:3], 1):
                paper_data = paper_doc.to_dict()
                print(f"   {i}. {paper_data.get('title', 'Untitled')[:60]}...")
                print(f"      ID: {paper_doc.id}")
                print(f"      Has embedding: {'Yes' if paper_data.get('embedding') else 'No'}")
        
        return {
            "status": "success",
            "papers": len(papers),
            "papers_with_embeddings": papers_with_embeddings,
            "podcasts": len(podcasts),
            "podcasts_with_embeddings": podcasts_with_embeddings
        }
        
    except Exception as e:
        print(f"❌ Error assessing Firestore: {e}")
        return {"status": "error", "error": str(e)}


def assess_videos() -> Dict[str, Any]:
    """Assess videos in Science Video Database."""
    print("\n" + "="*70)
    print("3. SCIENCE VIDEO DATABASE (PostgreSQL)")
    print("="*70)
    
    print("⚠️  Video database assessment requires direct database access")
    print("   Run this command in the scienceviddb directory:")
    print("   cd /home/gdubs/scienceviddb")
    print("   npm run verify-ingestion --workspace=packages/ingestion")
    print("\n   Or check the database directly for:")
    print("   - Total video count")
    print("   - Videos per discipline")
    print("   - Active channel count")
    print("   - Embedding coverage")
    
    return {
        "status": "manual_check_required",
        "instructions": "Run verification script in scienceviddb directory"
    }


def main():
    """Run all assessments."""
    print("\n" + "="*70)
    print("CONTENT STATUS ASSESSMENT")
    print("="*70)
    print("\nThis script checks the current state of content across all systems.")
    print("Use this information to plan ingestion activities.\n")
    
    results = {}
    
    # Assess research papers (PostgreSQL)
    results["research_papers"] = assess_research_papers_postgres()
    
    # Assess Firestore
    results["firestore"] = assess_firestore()
    
    # Assess videos (manual)
    results["videos"] = assess_videos()
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    if results["research_papers"].get("status") == "success":
        total = results["research_papers"].get("total_papers", 0)
        math = results["research_papers"].get("math_papers", 0)
        print(f"📚 Research Papers (PostgreSQL): {total} total, {math} mathematics")
    
    if results["firestore"].get("status") == "success":
        papers = results["firestore"].get("papers", 0)
        podcasts = results["firestore"].get("podcasts", 0)
        print(f"📄 Research Papers (Firestore): {papers}")
        print(f"🎙️  Podcasts (Firestore): {podcasts}")
    
    print(f"\n📹 Videos: Manual check required (see instructions above)")
    
    print("\n" + "="*70)
    print("NEXT STEPS")
    print("="*70)
    print("1. Review the assessment results above")
    print("2. See CONTENT_INGESTION_PLAN.md for detailed ingestion strategy")
    print("3. Begin with paper ingestion (target: 500+ mathematics papers)")
    print("4. Expand video channels and ingest 1000+ videos")
    print("5. Create sync scripts to integrate with Firestore")
    print()


if __name__ == "__main__":
    main()

