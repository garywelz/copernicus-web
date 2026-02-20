# Add Anthropic API Key - Quick Command

## Run This Command

Paste your API key when prompted:

```bash
cd cloud-run-backend
echo -n "YOUR_API_KEY_HERE" | gcloud secrets create anthropic-api-key \
  --data-file=- \
  --project=regal-scholar-453620-r7
```

**Replace `YOUR_API_KEY_HERE` with your actual API key (the one that starts with `sk-ant-`)**

## Or Use This One-Liner

If you want to paste the key directly:

```bash
gcloud secrets create anthropic-api-key \
  --data-file=- \
  --project=regal-scholar-453620-r7 <<< "YOUR_API_KEY_HERE"
```

## Verify It Was Added

```bash
gcloud secrets list --project=regal-scholar-453620-r7 | grep anthropic
```

You should see `anthropic-api-key` in the list.

## That's It!

Once the key is added:
1. ✅ The system will automatically detect it on next startup
2. ✅ RAG will switch from Vertex AI to Claude (50% cheaper)
3. ✅ Embeddings will use OpenAI (87% cheaper)
4. ✅ Total savings: ~73% vs Vertex AI

## Test It

After adding, you can test:

```python
from services.llm_providers.secret_manager_helpers import get_anthropic_api_key

key = get_anthropic_api_key()
if key:
    print("✅ Anthropic API key found!")
else:
    print("❌ Key not found")
```
