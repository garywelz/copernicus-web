# CopernicusAI User Database Schema

**Purpose:** Track user accounts, contributions, and community activity for the knowledge engine platform.

---

## 📋 **Current User Metadata** (Existing in Firestore `subscribers` collection)

### **Core Identity Fields**
```json
{
  "subscriber_id": "hex_id",           // Unique identifier (generated from email hash)
  "email": "user@example.com",          // Primary email (also username)
  "name": "User Name",                  // Display name
  "google_id": "google_123456",         // For Google OAuth users (optional)
  "password_hash": "hashed_password",   // For email/password users (optional)
  "created_at": "2025-10-27T...",      // Account creation timestamp
  "last_login": "2025-10-29T..."       // Last successful login
}
```

### **Subscription & Usage**
```json
{
  "subscription_tier": "free|premium|research",  // Current plan
  "subscription_status": "active|suspended|cancelled",
  "podcasts_generated": 0,                       // Total podcasts created
  "podcasts_submitted_to_rss": 0                 // Published to RSS feed
}
```

---

## 🆕 **Recommended Additions** (For Phase 2 Community Features)

### **1. Attribution & Privacy** ⭐ Important for Community
```json
{
  "display_name": "QuantumPhysicist",     // Public screen name (optional)
  "initials": "GW",                        // Abbreviation for attribution
  "show_attribution": false,               // Opt-in to show attribution on published content
  "bio": "",                               // User bio for profile
  "avatar_url": "",                        // Profile picture URL
  "profile_visibility": "public|private"   // Control profile visibility
}
```

### **2. Community Engagement** 📊 For Reddit-like Features
```json
{
  "reputation": 0,                         // Community karma/points
  "posts_count": 0,                        // Total posts published
  "comments_count": 0,                     // Total comments made
  "upvotes_received": 0,                   // Votes on their content
  "followers": [],                         // Array of user IDs following them
  "following": []                          // Array of user IDs they follow
}
```

### **3. Content Preferences** 🎯 Personalization
```json
{
  "favorite_categories": ["Biology", "Physics"],      // From UserPreferences
  "preferred_expertise_levels": ["intermediate"],    // From UserPreferences
  "notification_settings": {
    "email_on_completion": true,
    "email_on_failure": false,
    "weekly_digest": false,
    "comments_on_posts": true,                        // NEW: Notify on comments
    "new_follower": true                              // NEW: Notify on follows
  },
  "content_subscriptions": [],                        // Topics/categories user follows
  "blocked_users": []                                 // Privacy/abuse prevention
}
```

### **4. Usage Analytics** 📈 Track Activity
```json
{
  "total_listens": 0,                      // From UsageAnalytics
  "favorite_categories": [],               // Most listened categories
  "average_session_duration": 0.0,        // Minutes spent per session
  "last_activity": null,                   // Last meaningful action timestamp
  "devices": [],                           // Array of device fingerprints
  "preferred_playback_speed": 1.0,         // Custom playback speed
  "listening_habits": {                    // Aggregate stats
    "peak_hours": [],                      // Most active hours (0-23)
    "preferred_duration": "5-10 minutes",  // Favorite podcast length
    "format_preference": "interview"       // interview|monologue|debate
  }
}
```

### **5. Research & GLMP Integration** 🔬 For Knowledge Engine
```json
{
  "papers_uploaded": 0,                    // Research papers they've contributed
  "glmp_models_created": 0,                // GLMP flowcharts created
  "research_areas": ["Synthetic Biology", "Quantum Computing"],  // Their expertise
  "linked_papers": [],                     // Array of paper_ids they've linked to podcasts
  "glmp_workflows": [],                    // Array of GLMP process IDs they've created
  "citation_count": 0                      // Total citations of their content
}
```

### **6. Moderation & Safety** 🛡️ Community Quality Control
```json
{
  "moderation_status": "active|flagged|banned",
  "reported_content_count": 0,
  "strikes": 0,                            // Warning level (3 = ban)
  "can_publish": true,                     // Can publish to RSS
  "verified_status": false,                // Verified researcher/credentialed
  "verification_level": "none|email|research|institutional"  // Verification tier
}
```

---

## 🏗️ **Data Structure for Firestore**

### **Collection: `subscribers`**
```
Document ID: subscriber_id (hex hash of email)
├── Basic Info (existing)
├── Subscription (existing)
├── Attribution & Privacy (NEW - Phase 2.2)
├── Community Engagement (NEW - Phase 2.3)
├── Preferences (existing + extensions)
├── Analytics (existing + extensions)
├── Research Integration (NEW - Phase 2.4)
└── Moderation (NEW - Phase 2.5)
```

### **Sub-Collections (Optional)**
```
subscribers/{subscriber_id}/
├── podcasts/              # User's generated podcasts
├── comments/              # Comments they've made
├── followers/             # Who follows them
├── notifications/         # Notification history
└── activity_log/          # Action history for analytics
```

---

## 🎯 **Phase 2 Implementation Priority**

### **Phase 2.1 - Core Community (Week 1-2)** ⭐ Highest Priority
- [ ] `display_name`, `initials`, `show_attribution`
- [ ] `reputation`, `posts_count`, `upvotes_received`
- [ ] `profile_visibility`

### **Phase 2.2 - Content & Discovery (Week 3-4)**
- [ ] `content_subscriptions`, `preferred_categories`
- [ ] `total_listens`, `listening_habits`
- [ ] Search and filtering

### **Phase 2.3 - Research Integration (Week 5-6)**
- [ ] `papers_uploaded`, `glmp_models_created`
- [ ] `research_areas`, `citation_count`
- [ ] Link users to GLMP database

### **Phase 2.4 - Moderation (Ongoing)**
- [ ] `moderation_status`, `can_publish`
- [ ] `verified_status`, `strikes`
- [ ] Reporting and flagging system

---

## 💡 **Key Design Decisions**

### **Privacy-First Approach**
- ✅ Default: Attribution is OPT-IN (`show_attribution: false`)
- ✅ Users can use display names (not real names)
- ✅ Profile visibility controls
- ✅ Private by default, public by choice

### **Community-Driven**
- ✅ Reputation system encourages quality contributions
- ✅ Followers/following enables social discovery
- ✅ Comments and engagement track community impact
- ✅ Research integration links to GLMP knowledge base

### **Moderation-Ready**
- ✅ Verification levels for trusted researchers
- ✅ Strikes system for content policy violations
- ✅ Reporting mechanisms for abuse
- ✅ Can disable publishing for problematic accounts

---

## 📊 **Example User Document** (Full Schema)

```json
{
  "subscriber_id": "2ba148605cbe5df7",
  "email": "gary.welz@me.com",
  "name": "Gary Welz",
  
  // Attribution
  "display_name": "BioResearcher",
  "initials": "GW",
  "show_attribution": true,
  "bio": "Synthetic biologist exploring gene regulation",
  "profile_visibility": "public",
  
  // Subscription
  "subscription_tier": "free",
  "subscription_status": "active",
  "created_at": "2025-10-27T14:23:00Z",
  "last_login": "2025-10-29T15:01:00Z",
  
  // Community
  "reputation": 145,
  "posts_count": 15,
  "comments_count": 42,
  "upvotes_received": 189,
  "followers": ["abc123", "def456"],
  "following": ["ghi789"],
  
  // Content
  "podcasts_generated": 15,
  "podcasts_submitted_to_rss": 5,
  "favorite_categories": ["Biology", "Synthetic Biology"],
  "preferred_expertise_levels": ["intermediate", "advanced"],
  
  // Research Integration
  "papers_uploaded": 3,
  "glmp_models_created": 1,
  "research_areas": ["Gene Regulation", "Operon Dynamics"],
  "citation_count": 12,
  
  // Moderation
  "moderation_status": "active",
  "can_publish": true,
  "verified_status": false,
  "verification_level": "email",
  
  // Auth
  "google_id": "google_123456",
  "password_hash": null
}
```

---

**Status:** Schema ready for implementation  
**Next Steps:** Start with Phase 2.1 (attribution and basic community features)


