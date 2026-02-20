# Ralph Wiggum Paper Acquisition Loop Setup Guide

## Overview
This guide helps you set up Ralph Wiggum browser automation loops to automate paper acquisition from PubMed, arXiv, NASA ADS, and other sources.

## Prerequisites

1. **Ralph Wiggum Extension** installed in Chrome
2. **Paper Acquisition Scripts** (already set up in `/scripts/acquire_papers/`)
3. **Understanding of your target sources** (PubMed, arXiv, NASA ADS, Crossref)

## Ralph Wiggum Loop Options

### Option A: Browser-Based Search & Collection Loop
**Best for:** Interactive searches, visual verification, manual selection
**Workflow:**
1. Navigate to PubMed/arXiv/NASA ADS search page
2. Enter search query
3. Click through results
4. Extract paper metadata from page
5. Save to local file or clipboard
6. Repeat for next query/batch

### Option B: API-Based Automation Loop
**Best for:** Large-scale automated collection (uses your existing Python scripts)
**Workflow:**
1. Ralph Wiggum triggers/launches Python script
2. Script uses APIs (PubMed API, arXiv API, etc.)
3. Script saves results to JSON files
4. Ralph Wiggum monitors script completion
5. Repeat with next batch of queries

### Option C: Hybrid Approach
**Best for:** Combination of browser interaction + API calls
**Workflow:**
1. Use Ralph Wiggum for navigation and search
2. Extract search URLs/IDs
3. Pass to Python scripts for API-based metadata collection
4. Combine results

## Recommended Setup: Option B (API-Based)

Since you already have Python scripts for paper acquisition, we'll set up Ralph Wiggum to:
1. **Orchestrate** the Python scripts
2. **Monitor** progress and errors
3. **Schedule** batch runs
4. **Handle** retries and error recovery

## Step-by-Step Setup Instructions

### Step 1: Prepare Your Paper Acquisition Scripts

Your scripts should:
- Accept command-line arguments for search terms, date ranges, limits
- Save results to consistent JSON format
- Log progress and errors
- Be idempotent (can run multiple times safely)

### Step 2: Create Ralph Wiggum Loop Structure

**Loop Pattern:**
```
FOR each search query/batch:
  - Launch Python script with parameters
  - Wait for completion
  - Check for errors
  - Log results
  - Move to next query
END FOR
```

### Step 3: Define Your Search Queries

Create a list of:
- Search terms (e.g., "rhinovirus", "quantum computing", "machine learning")
- Date ranges
- Source priorities
- Limits per query

### Step 4: Set Up Error Handling

- Retry failed requests
- Skip duplicate papers
- Handle API rate limits
- Log errors for manual review

## Next Steps

1. **Review your existing paper acquisition scripts** to understand the workflow
2. **Identify the automation points** (what needs to be automated)
3. **Create the Ralph Wiggum loop** with appropriate actions
4. **Test with a small batch** before scaling up

## Questions to Answer Before Creating the Loop

1. **Which sources should be prioritized?** (PubMed, arXiv, NASA ADS, Crossref)
2. **What search queries/terms do you want to use?**
3. **What date ranges should be covered?**
4. **How many papers per query/batch?**
5. **Should the loop run continuously or on a schedule?**
6. **How should results be stored?** (JSON files, database, etc.)
