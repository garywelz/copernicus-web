# Bypass Auth Error for Knowledge Map Testing

## Current Issue

The home page (`/`) has a next-auth error:
- Error: `useSession` must be wrapped in a `<SessionProvider />`
- This is on the home page, not the Knowledge Map page

## Solution: Navigate Directly to Knowledge Map

The Knowledge Map page (`/knowledge-engine`) should work independently. 

### Direct URL to Test:

```
http://localhost:3000/knowledge-engine
```

The Knowledge Map component doesn't use `useSession` or require authentication, so it should load fine even with the home page error.

## Test Steps

1. **Navigate directly to:** `http://localhost:3000/knowledge-engine`
2. **Skip the home page** (which has the auth error)
3. **Open Developer Console** (F12)
4. **Test the React removeChild error fix**

The home page auth error is a separate issue and shouldn't affect testing the Knowledge Map fix.
