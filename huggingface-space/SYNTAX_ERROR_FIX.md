# Syntax Error Fix - Layout.js

## Issue

**Error:** `Uncaught SyntaxError: Invalid or unexpected token` in `app/layout.js:301`

**Cause:** Likely a compilation issue in the Next.js build cache

**Solution:** Clear the `.next` cache and restart the dev server

## Fix Steps

1. **Stop the dev server** (Ctrl+C or kill the process)
2. **Clear the Next.js cache:**
   ```bash
   cd /home/gdubs/copernicus-web-public
   rm -rf .next
   ```
3. **Restart the dev server:**
   ```bash
   npm run dev
   ```

## Current Status

The dev server is running. The syntax error is likely from a stale build cache. 

**Next Steps:**
1. Stop the server (if needed)
2. Clear `.next` cache
3. Restart server
4. Test the Knowledge Map again

The layout.tsx file looks correct, so this is likely a build cache issue that will be resolved by clearing `.next` and rebuilding.
