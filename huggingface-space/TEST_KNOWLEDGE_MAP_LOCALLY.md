# Testing Knowledge Map Locally

## Prerequisites

1. **Node.js and npm** installed
2. **Backend API** running (Cloud Run or local)
3. **Environment variables** configured

## Step 1: Check Environment Setup

### Verify API URL

The Knowledge Map uses the API URL from environment variables. Check:
- `.env.local` file (if exists)
- Or the default: `http://localhost:8000`

The component uses:
```typescript
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
```

### Set API URL (if needed)

Create `.env.local` in the project root:
```bash
NEXT_PUBLIC_API_URL=https://copernicus-podcast-api-phzp4ie2sq-uc.a.run.app
```

Or use the Cloud Run URL directly (already set as default in production).

## Step 2: Install Dependencies (if needed)

```bash
cd /home/gdubs/copernicus-web-public
npm install
```

## Step 3: Run Development Server

```bash
cd /home/gdubs/copernicus-web-public
npm run dev
```

This starts the Next.js development server (usually on `http://localhost:3000`)

## Step 4: Open Knowledge Map in Browser

1. Open browser: `http://localhost:3000/knowledge-engine`
2. Open Developer Console (F12 or Right-click → Inspect → Console tab)
3. Watch for the React error

## Step 5: Test the Fix

### What to Check:

1. **Map loads successfully** ✅
   - You should see the graph visualization
   - Console shows "Knowledge map loaded successfully!"

2. **No React removeChild error** ✅ (This is what we're testing)
   - Check browser console for errors
   - Should NOT see: `NotFoundError: Failed to execute 'removeChild' on 'Node'`
   - Old error was: `The node to be removed is not a child of this node.`

3. **Map is interactive** ✅
   - Can click nodes
   - Can zoom/pan
   - Controls work (filters, etc.)

### Expected Console Output (Success):

```
Loading knowledge map from: https://copernicus-podcast-api-phzp4ie2sq-uc.a.run.app/api/knowledge-map/graph
Fetching from: [URL]
Response status: 200
Knowledge map data received: Object
Added X nodes to graph (0 invalid)
Added Y edges to graph (Z filtered out)
Total elements for Cytoscape: N
Knowledge map loaded successfully!
Graph fitted to viewport
```

### What We Fixed:

- **Before:** Error appeared after "Knowledge map loaded successfully!"
- **After:** Error should be gone - state updates are deferred with `startTransition`

## Step 6: Test Different Scenarios

1. **Load map multiple times** (click "Reload Map" button)
2. **Change filters** and reload
3. **Navigate away and back** to the page
4. **Check for any new errors**

## Troubleshooting

### If API URL is wrong:
- Check `.env.local` file
- Verify backend is accessible
- Check network tab in browser DevTools

### If map doesn't load:
- Check browser console for API errors
- Verify backend is running
- Check network connectivity

### If errors persist:
- Clear browser cache
- Hard refresh (Ctrl+Shift+R or Cmd+Shift+R)
- Check if changes were saved correctly

## Quick Test Command

```bash
cd /home/gdubs/copernicus-web-public && npm run dev
```

Then open: `http://localhost:3000/knowledge-engine`

## Next Steps After Testing

If the fix works:
1. ✅ Build and deploy to production
2. ✅ Test on production URL
3. ✅ Monitor for any issues

If errors persist:
1. Check browser console for specific error messages
2. Review the implementation
3. Consider alternative approaches
