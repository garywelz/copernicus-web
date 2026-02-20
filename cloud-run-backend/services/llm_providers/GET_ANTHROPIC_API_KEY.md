# Getting Your Anthropic API Key

## Important Distinction

**Claude Code** (IDE integration) and **Anthropic API** (programmatic access) are **different products**:

- **Claude Code:** IDE integration for coding assistance (what you're using now)
- **Anthropic API:** Programmatic API access for your applications (what CopernicusAI needs)

Your Claude Code Pro plan subscription does **not** include API access. You need a separate API key for programmatic use.

## How to Get Your Anthropic API Key

### Step 1: Go to Anthropic Console

Visit: **https://console.anthropic.com/settings/keys**

### Step 2: Sign In

Use the same account you use for Claude Code (if you have one), or create a new account.

### Step 3: Create API Key

1. Click **"Create Key"** or **"Generate API Key"**
2. Give it a name (e.g., "CopernicusAI Production")
3. Copy the key (it starts with `sk-ant-`)
4. **Important:** Save it immediately - you won't be able to see it again!

### Step 4: Add to Secret Manager

Once you have the key, add it to Google Cloud Secret Manager:

```bash
# Using the helper script (easiest)
cd cloud-run-backend
./scripts/add_anthropic_key.sh

# Or manually
echo -n "sk-ant-..." | gcloud secrets create anthropic-api-key \
  --data-file=- \
  --project=regal-scholar-453620-r7
```

## Pricing

Anthropic API has separate pricing from Claude Code:

- **Claude 3.5 Haiku:** $1 input / $5 output per 1M tokens (recommended for RAG)
- **Claude 3.5 Sonnet:** $3 input / $15 output per 1M tokens (higher quality)

**Note:** API usage is billed separately from your Claude Code subscription.

## Why You Need This

The CopernicusAI system needs programmatic API access to:
- Generate RAG (Retrieval-Augmented Generation) responses
- Process queries using Claude models
- Integrate with your knowledge graph

Claude Code is great for development, but your production system needs the API key.

## Verification

After adding the key, test it:

```python
from services.llm_providers.secret_manager_helpers import get_anthropic_api_key

key = get_anthropic_api_key()
if key:
    print("✅ Anthropic API key found!")
    print(f"Key starts with: {key[:10]}...")
else:
    print("❌ Anthropic API key not found")
```

## Next Steps

1. ✅ Get API key from https://console.anthropic.com/settings/keys
2. ✅ Add to Secret Manager using the script or gcloud
3. ✅ Restart your Cloud Run service
4. ✅ System will automatically use Claude for RAG

---

**TL;DR:** Claude Code ≠ Anthropic API. You need a separate API key from https://console.anthropic.com/ for programmatic access.
