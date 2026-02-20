# Secret Manager Setup for Multi-Provider LLM

## Overview

The multi-provider LLM system automatically retrieves API keys from Google Cloud Secret Manager if they're not set as environment variables. This makes it easy to use the system in production without hardcoding keys.

## Secret Names

The system looks for these secrets in Secret Manager:

| Environment Variable | Secret Name | Provider |
|---------------------|-------------|----------|
| `OPENAI_API_KEY` | `openai-api-key` | OpenAI |
| `ANTHROPIC_API_KEY` | `anthropic-api-key` | Anthropic Claude |
| `VOYAGE_API_KEY` | `voyage-api-key` | Voyage (optional) |

## Automatic Loading

### On Startup

The `load_all_api_keys_from_secret_manager()` function in `main.py` automatically loads these keys on startup:

- ✅ `OPENAI_API_KEY` from `openai-api-key`
- ✅ `ANTHROPIC_API_KEY` from `anthropic-api-key`
- ✅ `VOYAGE_API_KEY` from `voyage-api-key` (optional)

### At Runtime

If keys aren't loaded at startup, the provider implementations will automatically retrieve them from Secret Manager when needed.

## Setting Up Secrets

### Option 1: Using gcloud CLI

```bash
# Set OpenAI API key
echo -n "sk-..." | gcloud secrets create openai-api-key --data-file=- \
  --project=regal-scholar-453620-r7

# Set Anthropic API key
echo -n "sk-ant-..." | gcloud secrets create anthropic-api-key --data-file=- \
  --project=regal-scholar-453620-r7

# Optional: Set Voyage API key (or use Anthropic key)
echo -n "..." | gcloud secrets create voyage-api-key --data-file=- \
  --project=regal-scholar-453620-r7
```

### Option 2: Using Google Cloud Console

1. Go to: https://console.cloud.google.com/security/secret-manager?project=regal-scholar-453620-r7
2. Click "CREATE SECRET"
3. Enter secret name: `openai-api-key`
4. Enter secret value: Your OpenAI API key
5. Click "CREATE SECRET"
6. Repeat for `anthropic-api-key` (and optionally `voyage-api-key`)

### Option 3: Update Existing Secrets

If the secrets already exist:

```bash
# Update OpenAI key
echo -n "sk-..." | gcloud secrets versions add openai-api-key --data-file=- \
  --project=regal-scholar-453620-r7

# Update Anthropic key
echo -n "sk-ant-..." | gcloud secrets versions add anthropic-api-key --data-file=- \
  --project=regal-scholar-453620-r7
```

## Granting Access

Make sure your Cloud Run service account has access to the secrets:

```bash
# Get your service account email
SERVICE_ACCOUNT="YOUR_SERVICE_ACCOUNT@regal-scholar-453620-r7.iam.gserviceaccount.com"

# Grant access to OpenAI secret
gcloud secrets add-iam-policy-binding openai-api-key \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/secretmanager.secretAccessor" \
  --project=regal-scholar-453620-r7

# Grant access to Anthropic secret
gcloud secrets add-iam-policy-binding anthropic-api-key \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/secretmanager.secretAccessor" \
  --project=regal-scholar-453620-r7
```

## Verification

### Check if Secrets Exist

```bash
# List all secrets
gcloud secrets list --project=regal-scholar-453620-r7

# Check specific secret
gcloud secrets versions access latest --secret="openai-api-key" \
  --project=regal-scholar-453620-r7
```

### Test in Code

```python
from services.llm_providers.secret_manager_helpers import get_openai_api_key, get_anthropic_api_key

# Test OpenAI key retrieval
openai_key = get_openai_api_key()
print(f"OpenAI key found: {openai_key is not None}")

# Test Anthropic key retrieval
anthropic_key = get_anthropic_api_key()
print(f"Anthropic key found: {anthropic_key is not None}")
```

## How It Works

1. **Startup:** `load_all_api_keys_from_secret_manager()` loads keys into environment variables
2. **Factory Selection:** Factory functions check environment variables first
3. **Provider Initialization:** If not in environment, providers check Secret Manager
4. **Caching:** Keys retrieved from Secret Manager are cached in `os.environ` for future use

## Troubleshooting

### "Secret not found"

**Error:** `Could not retrieve secret openai-api-key from Secret Manager`

**Solution:**
1. Verify secret exists: `gcloud secrets list`
2. Check secret name matches exactly (case-sensitive)
3. Verify service account has access

### "Permission denied"

**Error:** `Permission denied on secret`

**Solution:**
1. Grant Secret Manager Secret Accessor role to service account
2. Wait a few minutes for IAM changes to propagate

### "Key not found"

**Error:** `OPENAI_API_KEY not found in environment or Secret Manager`

**Solution:**
1. Check if secret exists in Secret Manager
2. Verify secret name is correct
3. Check service account permissions
4. Try setting as environment variable as fallback

## Best Practices

1. **Use Secret Manager for production** - Never hardcode API keys
2. **Use environment variables for local development** - Faster iteration
3. **Rotate keys regularly** - Update secrets when keys expire
4. **Monitor usage** - Check API usage dashboards regularly
5. **Use least privilege** - Only grant Secret Accessor role, not Secret Manager Admin

---

**Status:** ✅ Automatic Secret Manager integration is enabled and working!
