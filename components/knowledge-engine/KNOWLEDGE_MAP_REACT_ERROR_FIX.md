# Knowledge Map React Error Fix Plan

## Error Analysis

**Error:** `NotFoundError: Failed to execute 'removeChild' on 'Node': The node to be removed is not a child of this node.`

**Root Cause:** React's virtual DOM reconciliation conflicts with Cytoscape.js's direct DOM manipulation. The error occurs AFTER the map loads successfully, suggesting React tries to reconcile during re-renders.

**Observations:**
- Map loads successfully ("Knowledge map loaded successfully!")
- Error appears after map loads
- Error is in React's reconciliation code (removeChild)
- We've tried: innerHTML clearing, useEffect cleanup, key-based remounting

## Fix Strategy

### Option 1: Prevent React Reconciliation (Recommended)
**Approach:** Use a wrapper div that React doesn't manage, or use a ref callback to isolate Cytoscape's DOM.

**Implementation:**
1. Create a stable container div that React treats as a leaf node
2. Use `contentEditable={false}` to prevent React from managing children
3. Or use a ref callback that creates a separate div inside for Cytoscape

### Option 2: Error Suppression (Quick Fix)
**Approach:** Suppress the error if it doesn't break functionality.

**Implementation:**
1. Wrap Cytoscape operations in try-catch
2. Suppress removeChild errors if they don't affect functionality
3. Document as a known issue

### Option 3: Alternative Library (Long-term)
**Approach:** Use a React-friendly graph visualization library.

**Options:**
- react-cytoscapejs (React wrapper for Cytoscape)
- vis.js (more React-friendly)
- d3.js with React (full control)

## Recommended: Option 1 (Prevent Reconciliation)

We'll use a stable container approach where React treats the Cytoscape container as a leaf node.
