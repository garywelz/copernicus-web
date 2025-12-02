# Simple Deployment - One Command

## Current Situation
- ✅ Code fixed (Gemini 3.0 configured)
- ✅ Code committed and pushed to GitHub
- ❌ **Cloud Run still running old code** (that's why podcasts are failing)

## The Fix: Deploy Now

You have a deployment script ready. Just run this:

```bash
cd /home/gdubs/copernicus-web-public/cloud-run-backend
bash deploy.sh
```

This will:
1. Build the new code
2. Deploy to Cloud Run
3. Update the service with Gemini 3.0 fixes

**Estimated time: 5-10 minutes**

---

## After Deployment

1. **Wait for deployment to finish** (you'll see "✅ Deployment completed successfully!")
2. **Wait 1-2 more minutes** for the service to fully start
3. **Test with one podcast creation**
4. **Verify it works** - should use Gemini 3.0 now

---

## Don't Test Until After Deployment

**Please don't create more podcasts until after deployment** - they'll all fail with the same error until Cloud Run is updated.

Once deployed, then test with one podcast to verify the fix works.

---

**Ready? Just run: `cd cloud-run-backend && bash deploy.sh`**



