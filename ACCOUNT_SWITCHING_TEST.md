# Account Switching Test Plan

## Issues Fixed:
1. ✅ Added `prompt: 'select_account'` to force Google account chooser
2. ✅ Clear all localStorage on logout
3. ✅ Clear localStorage on login page load
4. ✅ Fixed signOut to show immediate UI update
5. ✅ Removed hardcoded email from signup page

## Testing Steps:

### Test 1: gwelz@jjay.cuny.edu → gary.welz@me.com
1. Sign in as `gwelz@jjay.cuny.edu`
2. Click "Sign Out" - should immediately show logged out
3. Try to sign up as `gary.welz@me.com`
4. Google should show account chooser
5. Create new account with gary.welz@me.com
6. Verify dashboard shows "gary.welz@me.com" (not gwelz@jjay.cuny.edu)

### Test 2: Private Window Test (For Other Users)
1. Open private/incognito window
2. Go to signup page
3. Try to create account
4. Should succeed

### Test 3: Multiple Browser Tabs
1. Login in tab 1 as gwelz@jjay.cuny.edu
2. Open tab 2 in private window
3. Login as gary.welz@me.com
4. Each tab should show correct account

## What Should Happen:
- ✅ Sign Out button immediately shows logged out state
- ✅ Google account chooser always appears
- ✅ No account "stickiness" between different emails
- ✅ localStorage is properly cleared on logout

## Files Changed:
- `app/api/auth/[...nextauth]/route.ts` - Added prompt: 'select_account'
- `app/auth/signup/page.tsx` - Removed hardcoded email
- `public/subscriber-login.html` - Clear localStorage on load
- `public/subscriber-dashboard.html` - Better signOut, clear on init/login
- `lib/auth.ts` - Already had demo mode handling


