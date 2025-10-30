# Copernicus AI Architecture Recommendations
**Date:** October 30, 2025  
**Status:** Strategic Planning Document  
**Goal:** Scale Copernicus AI as a community-driven knowledge engine

---

## 🎯 **Mission Alignment**

Copernicus AI aims to be a **Reddit-like community platform** where users can:
- Generate AI-powered research podcasts
- Share and discover content
- Link podcasts to GLMP flowcharts and research papers
- Engage with a knowledge graph of scientific concepts
- Build reputation through contributions

---

## 🏗️ **Current Architecture (As-Is)**

### **Frontend**
- **Next.js App** (`/app`): Modern React-based, OAuth with NextAuth
- **Static HTML** (`/public`): Alpine.js-based subscriber dashboard
- **Hosting**: Vercel (Next.js), GCS (static assets)

### **Backend**
- **Cloud Run (FastAPI)**: Podcast generation, research pipeline
- **Firestore**: User profiles, podcast metadata
- **GCS**: Audio files, transcripts, descriptions, thumbnails
- **PostgreSQL**: GLMP process database

### **Authentication**
- **Dual System**: NextAuth (OAuth) + Custom email/password
- **State Storage**: localStorage + Firestore + NextAuth sessions
- **Problem**: No unified session management

---

## ⚠️ **Critical Issues Identified**

### **1. Authentication Fragmentation**
- Two competing auth systems cause account stickiness and login loops
- State management across localStorage, Firestore, NextAuth is inconsistent
- No single source of truth for user identity

### **2. File Duplication**
- `subscriber-dashboard.html` exists in both `/public` and root
- Causes deployment confusion (which version is served?)
- API URLs out of sync between versions

### **3. Frontend Technology Mix**
- Next.js (modern, React-based) for main site
- Alpine.js + vanilla HTML for dashboard
- Inconsistent UX, harder to maintain

### **4. Data Layer Silos**
- Podcasts in Firestore + GCS
- GLMP flowcharts in PostgreSQL + Hugging Face
- No unified graph structure linking concepts

---

## 🚀 **Recommended Architecture (To-Be)**

### **Phase 1: Immediate Fixes (Current Week)**
✅ **COMPLETED**
- [x] Fix Alpine.js form binding issues
- [x] Consolidate API URLs to production endpoint
- [x] Remove duplicate `subscriber-dashboard.html` files
- [x] Add Alpine.js `$watch` for debugging reactive state

### **Phase 2: Authentication Consolidation (Week 2-3)**
**Goal:** Single, unified authentication system

#### **Option A: NextAuth Only (Recommended)**
```typescript
// Extend NextAuth to support email/password
providers: [
  GoogleProvider({...}),
  CredentialsProvider({
    name: 'Credentials',
    credentials: {
      email: { label: "Email", type: "email" },
      password: { label: "Password", type: "password" }
    },
    async authorize(credentials) {
      // Call Cloud Run backend to verify credentials
      const res = await fetch(`${API_BASE}/api/subscribers/login`, {
        method: 'POST',
        body: JSON.stringify(credentials),
        headers: { "Content-Type": "application/json" }
      })
      const user = await res.json()
      if (res.ok && user) {
        return user
      }
      return null
    }
  })
]
```

**Benefits:**
- Single source of truth for sessions
- Server-side session validation
- CSRF protection built-in
- Middleware for protected routes

**Migration Steps:**
1. Add `CredentialsProvider` to NextAuth config
2. Migrate subscriber-dashboard.html to React component (`/app/dashboard`)
3. Use `useSession()` hook for auth state
4. Deprecate localStorage-based auth

#### **Option B: Custom JWT + HTTP-Only Cookies (Alternative)**
If you need more control:
- Implement JWT tokens issued by Cloud Run backend
- Store in HTTP-only cookies (prevent XSS)
- Validate on every request via middleware
- Use React Context for client-side state

**Cons:** More work to implement secure session management

---

### **Phase 3: Frontend Consolidation (Week 4-6)**
**Goal:** Migrate all HTML pages to Next.js React components

#### **Dashboard Migration**
```
public/subscriber-dashboard.html (Alpine.js)
  ↓ MIGRATE TO ↓
app/dashboard/page.tsx (React + NextAuth)
```

**Component Structure:**
```typescript
// app/dashboard/page.tsx
import { getServerSession } from "next-auth/next"
import { authOptions } from "@/app/api/auth/[...nextauth]/route"
import { DashboardLayout } from "@/components/dashboard/Layout"
import { PodcastGenerator } from "@/components/dashboard/PodcastGenerator"
import { PodcastList } from "@/components/dashboard/PodcastList"
import { ProfileSettings } from "@/components/dashboard/ProfileSettings"

export default async function DashboardPage() {
  const session = await getServerSession(authOptions)
  
  if (!session) {
    redirect('/auth/signin')
  }
  
  // Fetch user data server-side (no loading states!)
  const userProfile = await fetchUserProfile(session.user.email)
  const podcasts = await fetchUserPodcasts(userProfile.subscriber_id)
  
  return (
    <DashboardLayout user={userProfile}>
      <StatsCards stats={userProfile.stats} />
      <PodcastGenerator subscriberId={userProfile.subscriber_id} />
      <PodcastList podcasts={podcasts} />
      <ProfileSettings profile={userProfile} />
    </DashboardLayout>
  )
}
```

**Benefits:**
- Server-side rendering (no auth flicker)
- Type safety with TypeScript
- Reusable components
- Better SEO
- Consistent UI framework

---

### **Phase 4: Community Features (Week 7-10)**
**Goal:** Reddit-like engagement system

#### **4.1 Podcast Discovery Feed**
```
app/discover/page.tsx
├── Trending podcasts (by upvotes/listens)
├── Search by topic, category, author
├── Filter by expertise level, duration
└── "Collections" (user-curated playlists)
```

#### **4.2 Comments & Discussions**
```
Firestore Structure:
podcasts/{podcast_id}/comments/{comment_id}
├── author_id
├── text
├── created_at
├── upvotes
└── replies (subcollection)
```

#### **4.3 User Profiles & Reputation**
```
subscribers/{subscriber_id}
├── display_name
├── bio
├── avatar_url
├── reputation (karma)
├── badges (["Early Adopter", "Top Contributor"])
├── expertise_areas ["Biology", "Physics"]
└── followers_count
```

**Reputation Algorithm:**
- +10 for podcast published to RSS
- +5 for upvote on your podcast
- +2 for helpful comment (upvoted)
- +50 for linking a verified research paper
- +100 for creating a GLMP flowchart used by others

#### **4.4 Following & Notifications**
```
subscribers/{subscriber_id}/following/{target_user_id}
subscribers/{subscriber_id}/notifications/{notification_id}
├── type: "new_podcast" | "comment_reply" | "upvote" | "mention"
├── from_user_id
├── content_link
└── read: boolean
```

---

### **Phase 5: Knowledge Graph Integration (Week 11-14)**
**Goal:** Link podcasts, GLMP flowcharts, and research papers

#### **5.1 Unified Metadata Schema**
```json
{
  "content_id": "uuid",
  "content_type": "podcast|glmp_flowchart|research_paper",
  "title": "CRISPR Gene Editing Overview",
  "authors": ["subscriber_id_1", "subscriber_id_2"],
  "tags": ["CRISPR", "Gene Editing", "Synthetic Biology"],
  "linked_content": [
    {"type": "glmp_flowchart", "id": "proc_0001_crispr_pathway"},
    {"type": "research_paper", "doi": "10.1038/s41586-024-xxxxx"},
    {"type": "podcast", "id": "podcast_xyz123"}
  ],
  "citation_count": 12,
  "upvotes": 145,
  "created_at": "2025-10-30T..."
}
```

#### **5.2 Graph Database (Optional)**
Consider **Neo4j** or **Dgraph** for complex queries:
- "Show me all podcasts about quantum computing that reference Nature papers"
- "Find GLMP flowcharts linked to podcasts by top Biology contributors"
- "What concepts bridge synthetic biology and nanotechnology?"

#### **5.3 Hugging Face Integration**
```
huggingface.co/spaces/garywelz/copernicusai
├── /podcasts (searchable database, current plan)
├── /glmp (existing GLMP viewer)
├── /papers (research paper index)
└── /graph (interactive knowledge graph visualization)
```

**Public API Endpoints:**
```
GET /api/public/podcasts?category=Biology&sort=trending
GET /api/public/glmp-processes?tag=Lac+Operon
GET /api/public/knowledge-graph?concept=CRISPR&depth=2
```

---

## 📊 **Data Flow (Recommended)**

```
┌─────────────────────────────────────────────────────┐
│         User Browser                                │
│  - Next.js App (React)                              │
│  - NextAuth session management                      │
│  - Server-side rendering for auth pages             │
└──────────────────┬──────────────────────────────────┘
                   │
                   │ HTTPS + Session Cookies
                   ▼
┌─────────────────────────────────────────────────────┐
│         Next.js API Routes (/app/api/*)            │
│  - /api/auth/[...nextauth] (authentication)        │
│  - /api/user/profile (user settings)               │
│  - /api/dashboard/podcasts (podcast CRUD)          │
│  - Validates NextAuth session                      │
│  - Proxies to Cloud Run backend                    │
└──────────────────┬──────────────────────────────────┘
                   │
                   │ Backend API calls (authenticated)
                   ▼
┌─────────────────────────────────────────────────────┐
│    Cloud Run Backend (FastAPI)                      │
│  - Podcast generation (research + TTS)             │
│  - File uploads to GCS                              │
│  - Firestore operations                             │
│  - Public RSS feed                                  │
│  - Public API for Hugging Face                     │
└──────────────────┬──────────────────────────────────┘
                   │
                   │ Data persistence
                   ▼
┌─────────────────────────────────────────────────────┐
│           Data Layer                                │
│  - Firestore: Users, podcasts, comments, follows   │
│  - GCS: Audio, transcripts, metadata.json          │
│  - PostgreSQL: GLMP flowcharts (read-only from HF) │
└─────────────────────────────────────────────────────┘
```

---

## 🔐 **Security Improvements**

### **Current Risks:**
- ❌ Passwords stored as simple hex encoding (not bcrypt)
- ❌ Authentication state in localStorage (XSS vulnerable)
- ❌ No CSRF protection on custom auth endpoints
- ❌ No rate limiting on login attempts

### **Recommended Fixes:**

#### **1. Password Hashing (URGENT)**
```python
# cloud-run-backend/main.py
import bcrypt

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
```

#### **2. HTTP-Only Cookies (Phase 2)**
```typescript
// app/api/auth/[...nextauth]/route.ts
cookies: {
  sessionToken: {
    name: `__Secure-next-auth.session-token`,
    options: {
      httpOnly: true,
      sameSite: 'lax',
      path: '/',
      secure: true // HTTPS only
    }
  }
}
```

#### **3. Rate Limiting (Cloud Run Backend)**
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/api/subscribers/login")
@limiter.limit("5/minute")  # Max 5 login attempts per minute per IP
async def login_subscriber(request: Request, login: SubscriberLogin):
    ...
```

#### **4. Input Validation**
```python
from pydantic import EmailStr, constr

class SubscriberLogin(BaseModel):
    email: EmailStr  # Validates email format
    password: constr(min_length=8, max_length=100)  # Length constraints
```

---

## 📈 **Scaling Considerations**

### **Current Limits:**
- Cloud Run: 1000 concurrent requests (sufficient for now)
- Firestore: 10K writes/sec per database (sufficient)
- GCS: Unlimited (pay per GB)
- ElevenLabs API: Rate limited (need to monitor)

### **Future Optimizations:**

#### **1. Caching Layer (Redis)**
```
Cache Strategy:
├── User sessions (5 min TTL)
├── Podcast metadata (1 hour TTL)
├── Public RSS feed (15 min TTL)
└── GLMP flowchart data (1 day TTL)
```

#### **2. CDN for Audio (Cloud CDN)**
- Cache audio files at edge locations
- Reduce GCS egress costs
- Faster playback for global users

#### **3. Background Jobs (Cloud Tasks)**
```
Async Job Queue:
├── Podcast generation (long-running)
├── Email notifications (non-blocking)
├── Thumbnail generation (batched)
└── Analytics aggregation (scheduled)
```

#### **4. Database Optimization**
```
Firestore Indexes:
├── subscribers: email (unique)
├── podcasts: subscriber_id, created_at (compound)
├── podcasts: status, created_at (compound)
├── comments: podcast_id, created_at (compound)
└── followers: target_user_id, created_at (compound)
```

---

## 🎨 **UX Enhancements**

### **Dashboard Improvements:**
1. **Podcast Generation Progress Bar**
   - Real-time updates via WebSocket or SSE
   - Show research phase, audio generation, upload status
   
2. **Preview Before Publish**
   - Play audio
   - Edit description/hashtags
   - Choose thumbnail from generated options

3. **Batch Operations**
   - Select multiple podcasts
   - Bulk delete, bulk publish to RSS

4. **Analytics Dashboard**
   - Listen counts (integrate with RSS reader analytics)
   - Top podcasts by engagement
   - Follower growth chart

---

## 🧪 **Testing Strategy**

### **Unit Tests:**
```bash
# Backend (pytest)
cd cloud-run-backend
pytest tests/ -v

# Frontend (Jest + React Testing Library)
cd app
npm test
```

### **Integration Tests:**
```python
# Test full podcast generation pipeline
async def test_podcast_generation_end_to_end():
    # 1. Create subscriber
    # 2. Submit podcast request
    # 3. Wait for completion
    # 4. Verify GCS files exist
    # 5. Verify Firestore metadata
    # 6. Verify RSS feed updated
```

### **E2E Tests (Playwright):**
```typescript
test('user can create account, generate podcast, and publish to RSS', async ({ page }) => {
  await page.goto('/auth/signin')
  await page.click('text=Create Account')
  // ... full user journey
})
```

---

## 🚢 **Deployment Strategy**

### **Current:**
- Vercel (automatic on git push)
- Cloud Run (manual via `gcloud run deploy`)

### **Recommended CI/CD:**
```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  deploy-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - run: npm install
      - run: npm run build
      - uses: vercel/action@v1
        with:
          token: ${{ secrets.VERCEL_TOKEN }}
          
  deploy-backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: google-github-actions/auth@v1
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}
      - run: |
          gcloud run deploy copernicus-podcast-api \
            --source ./cloud-run-backend \
            --region us-central1 \
            --allow-unauthenticated
```

---

## 📝 **Implementation Priorities**

### **Must Do Now (Week 1):**
- [x] Fix Alpine.js binding issue
- [x] Remove duplicate subscriber-dashboard.html
- [ ] Implement bcrypt password hashing
- [ ] Add rate limiting to login endpoint

### **Should Do Soon (Weeks 2-4):**
- [ ] Migrate subscriber-dashboard to Next.js React
- [ ] Implement CredentialsProvider in NextAuth
- [ ] Add automated tests for auth flow
- [ ] Setup CI/CD pipeline

### **Nice to Have (Months 2-3):**
- [ ] Community features (comments, follows, reputation)
- [ ] Knowledge graph visualization
- [ ] Public API for Hugging Face integration
- [ ] Advanced analytics dashboard

---

## 🎯 **Success Metrics**

### **User Engagement:**
- Daily active users (DAU)
- Podcasts generated per user per month
- Podcast publish rate (generated → published to RSS)
- Comments per podcast
- Follow/follower ratio

### **Content Quality:**
- Average podcast listen duration
- Upvote/downvote ratio
- Research paper citation rate
- GLMP flowchart link rate

### **Platform Health:**
- P99 latency for podcast generation
- Error rate < 1%
- User retention (30-day, 90-day)
- Cost per podcast generated

---

## 📚 **Resources**

- [NextAuth.js Documentation](https://next-auth.js.org/)
- [FastAPI Best Practices](https://fastapi.tiangolo.com/tutorial/security/)
- [Firestore Data Modeling](https://firebase.google.com/docs/firestore/data-model)
- [React Server Components](https://nextjs.org/docs/app/building-your-application/rendering/server-components)
- [Community Platform Design Patterns](https://www.patterns.dev/)

---

**Next Steps:**
1. Review this document with stakeholders
2. Prioritize features based on business goals
3. Create detailed technical specs for Phase 2
4. Begin React migration of dashboard

**Questions?** Contact the development team or open a GitHub discussion.

