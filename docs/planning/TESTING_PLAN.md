# Vector Search & RAG Testing Plan

**Date:** December 2025  
**Estimated Time:** 15-30 minutes  
**Status:** Test script created, ready to run

---

## Testing Time Estimate

### Quick Smoke Tests (5-10 minutes)
- Basic semantic search (3-5 queries)
- Content type filtering (2-3 tests)
- Verify results are returned

### Comprehensive Testing (15-30 minutes)
- Multiple query types
- All content types
- Similarity search
- RAG question answering
- Edge cases

### Full Validation (30-60 minutes)
- Performance testing
- Result quality assessment
- Cross-content type search
- RAG accuracy validation

---

## Can I Test It?

**Yes!** I can run the tests myself. I've created a test script that will:

1. ✅ Test semantic search across all content types
2. ✅ Test content type filtering
3. ✅ Test similarity search
4. ✅ Test RAG question answering
5. ✅ Provide detailed results and success rates

---

## Current Test Results

**Initial Test Run:**
- ✅ Test script created and runs
- ⚠️  Vector search returning 0 results (index may need propagation time)
- ⚠️  RAG service needs LLM client check fix

**Note:** Firestore vector indexes can take 2-5 minutes to fully propagate even after showing "READY" status. The GLMP index was just created, so it may need a few more minutes.

---

## Test Script

**Location:** `cloud-run-backend/scripts/test_vector_search.py`

**What it tests:**
1. Semantic search with various queries
2. Content type filtering (papers, GLMP, podcasts)
3. Similarity search (find similar content)
4. RAG question answering

**Usage:**
```bash
cd /home/gdubs/copernicus-web-public/cloud-run-backend
source venv/bin/activate
python3 scripts/test_vector_search.py
```

---

## Recommended Testing Approach

### Option 1: Wait and Test (Recommended)
1. Wait 2-5 minutes for index propagation
2. Run comprehensive test script
3. Review results

**Time:** 10-15 minutes total

### Option 2: Quick Verification
1. Test papers search (we know this works)
2. Test GLMP search with very lenient threshold
3. Verify embeddings are stored correctly

**Time:** 5 minutes

### Option 3: Manual Testing via MCP
1. Use MCP client to test individual queries
2. Verify results make sense
3. Test RAG with sample questions

**Time:** 10-20 minutes

---

## What I Can Do

I can:
- ✅ Run the automated test script
- ✅ Fix any issues found
- ✅ Verify results are reasonable
- ✅ Test edge cases
- ✅ Provide detailed test report

**Estimated time if I run it:** 15-30 minutes for comprehensive testing

---

## Next Steps

**Option A: I run tests now**
- Wait 2-3 minutes for index propagation
- Run comprehensive test script
- Report results and fix any issues

**Option B: You test manually**
- Wait 5 minutes for index propagation
- Test via MCP client
- Report any issues

**Option C: Defer testing**
- Index will be ready when you need it
- Test when you're ready to use vector search

---

**Recommendation:** Wait 2-3 minutes, then I can run the comprehensive test script. This will verify everything works and catch any issues early.

Would you like me to:
1. Wait a few minutes and run the tests now?
2. Just verify the setup is correct and you'll test later?
3. Do a quick verification test now?

