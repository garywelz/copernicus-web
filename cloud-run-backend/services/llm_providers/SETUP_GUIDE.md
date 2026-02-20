# Multi-Provider LLM Setup Guide

This guide explains how to switch from Vertex AI to OpenAI/Anthropic for embeddings and RAG services.

## Quick Start

### 1. Install Required Packages

```bash
# For OpenAI (recommended - cheapest embeddings)
pip install openai

# For Anthropic/Voyage (good quality/cost balance)
pip install anthropic voyageai
```

### 2. Set Environment Variables

Add to your `.env` file or Google Cloud Secret Manager:

```bash
# OpenAI (for embeddings - 87% cheaper than Vertex AI)
OPENAI_API_KEY=sk-...

# Anthropic (for RAG - 50% cheaper than Vertex AI)
ANTHROPIC_API_KEY=sk-ant-...

# Optional: Voyage (alternative embeddings - 33% cheaper than Vertex AI)
VOYAGE_API_KEY=...
```

### 3. Update Your Code

The system will automatically use the best available provider. No code changes needed if you're using:

```python
from services.embedding_service import get_embedding_service
from services.rag_service import get_rag_service
```

**However**, to use the new multi-provider system, update imports:

```python
# Old way (still works, but uses factory internally)
from services.embedding_service import get_embedding_service
from services.rag_service import get_rag_service

# New way (explicit multi-provider)
from services.llm_providers import get_embedding_service, get_rag_service
```

### 4. Provider Selection Priority

The factory automatically selects providers based on API key availability:

**Embeddings:**
1. OpenAI (if `OPENAI_API_KEY` is set) - **87% cheaper**
2. Voyage (if `VOYAGE_API_KEY` or `ANTHROPIC_API_KEY` is set) - **33% cheaper**
3. Vertex AI (fallback, if not disabled)

**RAG:**
1. Anthropic Claude (if `ANTHROPIC_API_KEY` is set) - **50% cheaper**
2. OpenAI (if `OPENAI_API_KEY` is set) - **85% cheaper**
3. Vertex AI (fallback, if not disabled)

### 5. Explicit Provider Selection

You can force a specific provider:

```bash
# Force OpenAI for embeddings
export EMBEDDING_PROVIDER=openai

# Force Claude for RAG
export RAG_PROVIDER=anthropic

# Force Vertex AI (not recommended due to cost)
export EMBEDDING_PROVIDER=vertex_ai
export RAG_PROVIDER=vertex_ai
```

## Cost Comparison

### Embeddings (per 1M tokens)

| Provider | Cost | Savings vs Vertex AI |
|----------|------|---------------------|
| **OpenAI** | $0.02 | **87% cheaper** ✅ Recommended |
| **Voyage** | $0.10 | **33% cheaper** |
| **Vertex AI** | $0.15 | Baseline |

### RAG/LLM Generation (per 1M output tokens)

| Provider | Cost | Savings vs Vertex AI |
|----------|------|---------------------|
| **OpenAI GPT-3.5** | $1.50 | **85% cheaper** |
| **Claude Haiku** | $5.00 | **50% cheaper** ✅ Recommended |
| **Vertex AI Gemini** | $10.00 | Baseline |

## Migration Steps

### Step 1: Get API Keys

1. **OpenAI:** https://platform.openai.com/api-keys
2. **Anthropic:** https://console.anthropic.com/
3. **Voyage:** https://www.voyageai.com/ (optional)

### Step 2: Set Environment Variables

**For Google Cloud Run:**
```bash
gcloud run services update YOUR_SERVICE \
  --set-env-vars OPENAI_API_KEY=sk-...,ANTHROPIC_API_KEY=sk-ant-...
```

**Or use Secret Manager:**
```bash
# Create secrets
echo -n "sk-..." | gcloud secrets create openai-api-key --data-file=-
echo -n "sk-ant-..." | gcloud secrets create anthropic-api-key --data-file=-

# Grant access
gcloud secrets add-iam-policy-binding openai-api-key \
  --member="serviceAccount:YOUR_SERVICE_ACCOUNT" \
  --role="roles/secretmanager.secretAccessor"
```

### Step 3: Disable Vertex AI (Optional)

To prevent accidental Vertex AI usage:

```bash
export DISABLE_VERTEX_AI=1
```

### Step 4: Test the Migration

```python
# Test embeddings
from services.llm_providers import get_embedding_service

service = get_embedding_service()
print(f"Using: {service.provider} ({service.model_name})")
embedding = service.embed_text("Test text")
print(f"Dimension: {len(embedding)}")
```

### Step 5: Monitor Costs

- Check OpenAI usage: https://platform.openai.com/usage
- Check Anthropic usage: https://console.anthropic.com/settings/usage
- Compare to previous Vertex AI costs

## Expected Savings

For a typical workload processing 5 billion embedding tokens and 42 million LLM output tokens:

| Provider Combination | Monthly Cost | Savings |
|---------------------|--------------|---------|
| **Vertex AI** (current) | $1,162.75 | Baseline |
| **OpenAI Embeddings + Claude RAG** | ~$310 | **73% savings** ✅ |
| **OpenAI Embeddings + OpenAI RAG** | ~$163 | **86% savings** |

## Troubleshooting

### "No embedding service available"

**Solution:** Set at least one API key:
```bash
export OPENAI_API_KEY=sk-...
# OR
export VOYAGE_API_KEY=...
# OR
export ANTHROPIC_API_KEY=sk-ant-...
```

### "ModuleNotFoundError: No module named 'openai'"

**Solution:** Install the package:
```bash
pip install openai
```

### Dimension Mismatch

**Note:** Different providers have different embedding dimensions:
- OpenAI: 1536 dimensions
- Voyage: 1024 dimensions
- Vertex AI: 768 dimensions

If you have existing embeddings in Firestore, you may need to:
1. Re-index with the new provider, OR
2. Continue using the same provider for consistency

### Want to Keep Using Vertex AI?

Just don't set the new API keys, and the system will fall back to Vertex AI (if not disabled).

## Next Steps

1. ✅ Install packages
2. ✅ Set API keys
3. ✅ Test with small batch
4. ✅ Monitor costs
5. ✅ Re-index if needed (for dimension changes)
6. ✅ Update documentation

---

**Questions?** Check the code in `services/llm_providers/` for implementation details.
