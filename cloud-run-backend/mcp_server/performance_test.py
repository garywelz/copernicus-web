"""
Performance testing script for MCP server tools

Run with: python -m mcp_server.performance_test
"""

import asyncio
import time
import json
from typing import Dict, List
import statistics

from mcp_server.tools.papers import query_research_papers, get_paper_by_id
from mcp_server.tools.glmp import list_glmp_processes, get_glmp_categories
from mcp_server.tools.podcasts import list_podcasts
from mcp_server.tools.cross_component import search_across_components


async def time_tool(tool_func, *args, **kwargs) -> Dict:
    """Time a tool execution"""
    start = time.time()
    try:
        result = await tool_func(*args, **kwargs)
        elapsed = time.time() - start
        result_size = len(result) if isinstance(result, str) else 0
        return {
            "success": True,
            "time": elapsed,
            "result_size": result_size,
            "error": None
        }
    except Exception as e:
        elapsed = time.time() - start
        return {
            "success": False,
            "time": elapsed,
            "result_size": 0,
            "error": str(e)
        }


async def run_performance_tests():
    """Run performance tests on all tools"""
    print("=" * 60)
    print("MCP Server Performance Tests")
    print("=" * 60)
    print()
    
    tests = [
        ("query_research_papers (basic)", query_research_papers, {"query": "test", "limit": 5}),
        ("list_glmp_processes", list_glmp_processes, {"limit": 10}),
        ("get_glmp_categories", get_glmp_categories, {}),
        ("list_podcasts", list_podcasts, {"limit": 5}),
        ("search_across_components", search_across_components, {"query": "test", "limit": 5}),
    ]
    
    results = {}
    
    for test_name, tool_func, args in tests:
        print(f"Testing: {test_name}...")
        
        # Run 3 times and average
        times = []
        for i in range(3):
            result = await time_tool(tool_func, **args)
            times.append(result["time"])
            if not result["success"]:
                print(f"  ⚠️  Error: {result['error']}")
        
        if times:
            avg_time = statistics.mean(times)
            min_time = min(times)
            max_time = max(times)
            
            results[test_name] = {
                "avg": avg_time,
                "min": min_time,
                "max": max_time
            }
            
            print(f"  ✅ Average: {avg_time:.2f}s (min: {min_time:.2f}s, max: {max_time:.2f}s)")
            
            # Check performance targets
            if avg_time > 5.0:
                print(f"  ⚠️  WARNING: Average time exceeds 5s target")
            elif avg_time > 2.0:
                print(f"  ⚠️  NOTE: Average time exceeds 2s target")
            else:
                print(f"  ✅ Performance target met (< 2s)")
        
        print()
    
    # Summary
    print("=" * 60)
    print("Performance Summary")
    print("=" * 60)
    
    for test_name, metrics in results.items():
        print(f"{test_name}:")
        print(f"  Average: {metrics['avg']:.2f}s")
        print(f"  Range: {metrics['min']:.2f}s - {metrics['max']:.2f}s")
        print()
    
    # Overall assessment
    all_avg_times = [m["avg"] for m in results.values()]
    overall_avg = statistics.mean(all_avg_times)
    
    print(f"Overall Average Response Time: {overall_avg:.2f}s")
    
    if overall_avg < 2.0:
        print("✅ Excellent performance - all tools meet target")
    elif overall_avg < 5.0:
        print("⚠️  Good performance - some optimization may be needed")
    else:
        print("❌ Performance needs improvement - consider caching or optimization")


if __name__ == "__main__":
    asyncio.run(run_performance_tests())



