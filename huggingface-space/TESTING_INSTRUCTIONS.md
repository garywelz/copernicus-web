# Knowledge Map Testing Instructions

## Dev Server Status

The Next.js development server should be running. 

## Testing Steps

### 1. Open the Knowledge Map

**URL:** http://localhost:3000/knowledge-engine

### 2. Open Browser Developer Console

- **Chrome/Edge:** Press F12 or Right-click → Inspect → Console tab
- **Firefox:** Press F12 or Right-click → Inspect Element → Console tab
- **Safari:** Enable Developer Menu, then Develop → Show JavaScript Console

### 3. What to Look For

#### ✅ **Success Indicators:**

1. **Map loads successfully**
   - Graph visualization appears
   - Nodes and edges are visible

2. **Console shows success messages:**
   ```
   Loading knowledge map from: https://copernicus-podcast-api-phzp4ie2sq-uc.a.run.app/api/knowledge-map/graph
   Response status: 200
   Knowledge map data received: Object
   Added X nodes to graph
   Added Y edges to graph
   Knowledge map loaded successfully!
   Graph fitted to viewport
   ```

3. **NO React removeChild error**
   - Should NOT see: `NotFoundError: Failed to execute 'removeChild' on 'Node'`
   - Should NOT see: `The node to be removed is not a child of this node.`

4. **Map is interactive**
   - Can click nodes
   - Can zoom (scroll) and pan (drag)
   - Controls work (filters, buttons)

#### ❌ **If Error Still Present:**

If you see:
```
Uncaught NotFoundError: Failed to execute 'removeChild' on 'Node': 
The node to be removed is not a child of this node.
```

This means the fix didn't work and we need to try a different approach.

### 4. Test Different Scenarios

1. **Initial Load** - Page loads, map appears
2. **Reload Map** - Click "Reload Map" button
3. **Change Filters** - Adjust filters and reload
4. **Navigate Away/Back** - Go to another page, come back
5. **Multiple Reloads** - Reload the map several times

### 5. Report Results

Please report:
- ✅ Error is gone (success!)
- ❌ Error still appears (need different fix)
- Any other errors or issues

## Quick Access

- **Knowledge Map:** http://localhost:3000/knowledge-engine
- **Main Site:** http://localhost:3000

## Stopping the Dev Server

When done testing, stop the server:
```bash
# Find the process
ps aux | grep "next dev"

# Kill it (replace PID with actual process ID)
kill <PID>
```

Or press Ctrl+C in the terminal where it's running.
