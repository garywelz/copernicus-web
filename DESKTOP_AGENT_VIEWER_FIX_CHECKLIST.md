# 🔧 Desktop Agent - GLMP Viewer Fix Checklist

**Quick Reference for Fixing the Viewer**

---

## ✅ What's Already Fixed (by Web Agent)

- ✅ CORS configured on GCS bucket
- ✅ metadata.json is publicly accessible
- ✅ Database table works perfectly
- ✅ Data contains all 58 processes

**Bottom line: The data is fine. The viewer's JavaScript needs fixing.**

---

## 🎯 Your Task: Fix the Viewer JavaScript

### Step 1: Find the Viewer Files

Look for these files in your workspace:
- `glmp-v2/viewer/index.html`
- `glmp-v2/viewer/viewer.js` (might be inline in index.html)
- `glmp-v2/viewer/app.js` (or similar)

### Step 2: Find the Fetch Call

Search for:
```javascript
fetch(
```

### Step 3: Check the URL

**It MUST be exactly:**
```javascript
const METADATA_URL = 'https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/glmp-v2/data/metadata.json';
```

**Common mistakes:**
- ❌ `glmp-v2/metadata.json` (missing `/data/`)
- ❌ `./metadata.json` (relative path won't work)
- ❌ `/api/glmp/metadata` (API endpoint - wrong approach)
- ❌ `../data/metadata.json` (relative path)

### Step 4: Add Error Handling

Replace the fetch with this improved version:

```javascript
async function loadProcessList() {
    const METADATA_URL = 'https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/glmp-v2/data/metadata.json';
    
    console.log('🔄 Loading GLMP processes from:', METADATA_URL);
    
    try {
        console.log('📡 Fetching metadata...');
        const response = await fetch(METADATA_URL);
        console.log('📥 Response:', response.status, response.statusText);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        console.log('🔍 Parsing JSON...');
        const data = await response.json();
        console.log('✅ Loaded successfully:', data.totalProcesses, 'processes');
        console.log('First process:', data.processes[0].name);
        
        renderProcessList(data.processes);
        hideLoading();
        
    } catch (error) {
        console.error('❌ Error loading processes:', error);
        console.error('Error details:', {
            message: error.message,
            name: error.name,
            stack: error.stack
        });
        
        showError(`Failed to load processes: ${error.message}`);
    }
}
```

### Step 5: Fix Navigation Bug

**Problem:** "Back to Home" button visible on home page

**Find the showHome and showProcess functions, update them:**

```javascript
function showHome() {
    // Hide process view, show home
    document.getElementById('home-view').style.display = 'block';
    document.getElementById('process-view').style.display = 'none';
    
    // Hide back button on home page
    const backBtn = document.querySelector('.back-btn') || document.getElementById('back-btn');
    if (backBtn) {
        backBtn.style.display = 'none';
    }
}

function showProcess(processId) {
    // Hide home, show process view
    document.getElementById('home-view').style.display = 'none';
    document.getElementById('process-view').style.display = 'block';
    
    // Show back button when viewing a process
    const backBtn = document.querySelector('.back-btn') || document.getElementById('back-btn');
    if (backBtn) {
        backBtn.style.display = 'inline-block';
    }
    
    loadProcess(processId);
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    showHome(); // This will hide the back button initially
    loadProcessList();
});
```

---

## 🧪 Quick Test

**Before deploying, test in browser console:**

1. Open the viewer locally or on GCS
2. Open DevTools (F12)
3. Paste this in console:

```javascript
fetch('https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/glmp-v2/data/metadata.json')
  .then(r => r.json())
  .then(d => {
    console.log('✅ SUCCESS! Total processes:', d.totalProcesses);
    console.log('Organisms:', [...new Set(d.processes.map(p => p.organism))]);
    console.log('First 3 processes:', d.processes.slice(0,3).map(p => p.name));
    return d;
  })
  .catch(e => console.error('❌ FAILED:', e));
```

**Expected output:**
```
✅ SUCCESS! Total processes: 58
Organisms: ["E. coli", "Yeast", "Bacillus subtilis"]
First 3 processes: ["Lac Operon Regulation", "DNA Replication Initiation at oriC", ...]
```

**If this works in console but NOT in your page → your JavaScript code has a bug!**

---

## 📦 Deploy to GCS

Once fixed:

```bash
# Upload the fixed viewer
gsutil cp glmp-v2/viewer/index.html gs://regal-scholar-453620-r7-podcast-storage/glmp-v2/viewer/index.html

# If you have separate JS files:
gsutil cp glmp-v2/viewer/viewer.js gs://regal-scholar-453620-r7-podcast-storage/glmp-v2/viewer/viewer.js

# Set public access
gsutil acl ch -u AllUsers:R gs://regal-scholar-453620-r7-podcast-storage/glmp-v2/viewer/index.html

# Set cache headers
gsutil setmeta -h "Cache-Control:public, max-age=300" gs://regal-scholar-453620-r7-podcast-storage/glmp-v2/viewer/index.html
```

---

## ✅ Final Verification

After deploying, test these URLs:

1. **Database Table (already working):**
   https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/glmp-database-table.html
   - Should show 58 processes in a table
   - Process names should be clickable

2. **GLMP Viewer (your fix):**
   https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/glmp-v2/viewer/index.html
   - Should show process list (58 processes)
   - Back button should NOT show on home
   - Clicking a process should show it
   - Back button SHOULD show when viewing a process

3. **Test a specific process:**
   https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/glmp-v2/viewer/index.html?process=ecoli_lac_operon
   - Should load the Lac Operon flowchart directly
   - Back button should be visible

---

## 🆘 If Still Not Working

**Check browser console for errors:**
- Look for red error messages
- Check Network tab for failed requests
- Verify the fetch URL is correct

**Common issues:**
1. **CORS error:** Should be fixed already by Web Agent
2. **404 Not Found:** Wrong URL in fetch call
3. **TypeError:** Bug in render function
4. **Silent failure:** Missing error handling

**Share with Web Agent:**
- The exact error message from console
- The fetch URL you're using
- The JavaScript code snippet

---

**This should take 5-10 minutes to fix once you locate the viewer files!**

---

*Quick Reference Created: October 16, 2025*  
*All data and CORS issues are already resolved - just need to fix the JavaScript!*

