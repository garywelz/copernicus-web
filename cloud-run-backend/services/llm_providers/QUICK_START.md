# Quick Start: Using OpenAI & Anthropic Instead of Vertex AI

## Current Status ✅

Based on your Secret Manager, you have:
- ✅ **OpenAI API key** (`openai-api-key`) - Ready to use!
- ❌ **Anthropic API key** (`anthropic-api-key`) - Need to add

## What Works Right Now

With just the OpenAI key, the system will:
- ✅ Use **OpenAI for embeddings** (87% cheaper than Vertex AI)
- ⚠️ Fall back to **Vertex AI for RAG** (until you add Anthropic key)

## Adding Anthropic API Key

### Option 1: Using the Helper Script (Easiest)

```bash
cd cloud-run-backend
./scripts/add_anthropic_key.sh
```

The script will:
1. Prompt you for your Anthropic API key
2. Create or update the secret in Secret Manager
3. Verify the format

### Option 2: Using gcloud CLI

```bash
# Get your API key from: https://console.anthropic.com/settings/keys
echo -n "sk-ant-..." | gcloud secrets create anthropic-api-key \
  --data-file=- \
  --project=regal-scholar-453620-r7
```

### Option 3: Using Google Cloud Console

1. Go to: https://console.anthropic.com/settings/keys
2. Copy your API key (starts with `sk-ant-`)
3. Go to: https://console.cloud.google.com/security/secret-manager?project=regal-scholar-453620-r7
4. Click "CREATE SECRET"
5. Name: `anthropic-api-key`
6. Paste your API key
7. Click "CREATE SECRET"

## After Adding the Key

Once you add the Anthropic key:

1. **Restart your Cloud Run service** (or wait for next deployment)
2. The system will automatically:
   - Use **OpenAI for embeddings** (cheapest)
   - Use **Claude for RAG** (good quality/cost balance)

## Testing

After adding the key, test it:

```python
# Test embeddings (should use OpenAI)
from services.embedding_service import get_embedding_service

embedding_service = get_embedding_service()
print(f"Embeddings: {embedding_service.provider}")  # Should show "openai"

# Test RAG (should use Claude after you add the key)
from services.rag_service import get_rag_service

rag_service = get_rag_service()
print(f"RAG: {rag_service.provider}")  # Should show "anthropic" after adding key
```

## Expected Cost Savings

| Service | Before (Vertex AI) | After (OpenAI/Claude) | Savings |
|---------|-------------------|----------------------|---------|
| Embeddings | $0.15 per 1M tokens | $0.02 per 1M tokens | **87%** ✅ |
| RAG | $10 per 1M tokens | $5 per 1M tokens | **50%** ✅ |
| **Total** | **$1,162.75/month** | **~$310/month** | **73%** ✅ |

## Current Configuration

- **Embeddings:** Will use OpenAI (✅ key exists)
- **RAG:** Will use Claude (⏳ add key to enable)
- **Fallback:** Vertex AI (if new keys unavailable)

## Next Steps

1. ✅ OpenAI key is ready - embeddings will use it automatically
2. ⏳ Add Anthropic key using one of the methods above
3. ✅ Restart service or wait for next deployment
4. ✅ System will automatically switch to cheaper providers

---

**You're all set!** The system will automatically use OpenAI for embeddings right away. Just add the Anthropic key when you're ready to also use Claude for RAG.
