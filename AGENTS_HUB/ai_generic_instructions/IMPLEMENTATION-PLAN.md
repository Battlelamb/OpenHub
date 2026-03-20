# Generic - Social Platform Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a Twitter-like social platform where users post needs/wants, list properties/vehicles, and find connections — powered by Supabase free tier and deployed on Netlify.

**Architecture:** Next.js 14+ App Router with server components for SEO/performance, Supabase for auth/DB/storage/realtime, shadcn/ui for UI. All data flows through Supabase client SDK (no custom API layer needed for MVP). RLS policies enforce authorization at the database level.

**Tech Stack:** Next.js 14+ (App Router), TypeScript, Supabase (PostgreSQL + Auth + Storage + Realtime), shadcn/ui, Tailwind CSS, Netlify

---

## Table of Contents

1. [Database Schema (Supabase SQL)](#1-database-schema)
2. [Auth Flow Diagrams](#2-auth-flow-diagrams)
3. [API Route Design](#3-api-route-design)
4. [Component Hierarchy](#4-component-hierarchy)
5. [Phase Breakdown & Tasks](#5-phase-breakdown--tasks)
6. [Free Tier Optimization Notes](#6-free-tier-optimization)

---

## 1. Database Schema

### Design Principles
- All tables have `id` as UUID primary key (auto-generated)
- All tables have `created_at` and `updated_at` timestamps
- RLS enabled on every table — no exceptions
- Foreign keys reference `auth.users(id)` for user ownership
- Soft deletes where appropriate (`deleted_at` column)
- Indexes on frequently queried columns (category, location, user_id)

### 1.1 Complete SQL Migration

```sql
-- ============================================================
-- GENERIC SOCIAL PLATFORM - COMPLETE DATABASE SCHEMA
-- Run this in Supabase SQL Editor (in order)
-- ============================================================

-- ============================================================
-- ENUMS
-- ============================================================

CREATE TYPE post_category AS ENUM (
  'genel',        -- General
  'emlak',        -- Real Estate
  'arac',         -- Vehicle
  'hizmet',       -- Service
  'tanidik_arama' -- Finding People
);

CREATE TYPE post_status AS ENUM (
  'active',
  'expired',
  'closed',
  'draft'
);

CREATE TYPE notification_type AS ENUM (
  'like',
  'comment',
  'follow',
  'mention',
  'system'
);

CREATE TYPE ad_status AS ENUM (
  'pending',
  'active',
  'paused',
  'expired',
  'rejected'
);

CREATE TYPE report_reason AS ENUM (
  'spam',
  'harassment',
  'inappropriate',
  'fraud',
  'other'
);

-- ============================================================
-- TABLE: profiles
-- Extends Supabase auth.users with app-specific data
-- ============================================================

CREATE TABLE profiles (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  username TEXT UNIQUE NOT NULL,
  display_name TEXT,
  avatar_url TEXT,
  bio TEXT,
  location TEXT,
  latitude DOUBLE PRECISION,
  longitude DOUBLE PRECISION,
  occupation TEXT,
  interests TEXT[],           -- Array of interest tags
  website TEXT,
  trust_score INTEGER DEFAULT 0 CHECK (trust_score >= 0 AND trust_score <= 100),
  is_verified BOOLEAN DEFAULT FALSE,
  portfolio_urls TEXT[],
  followers_count INTEGER DEFAULT 0,
  following_count INTEGER DEFAULT 0,
  posts_count INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_profiles_username ON profiles(username);
CREATE INDEX idx_profiles_location ON profiles(location);

-- ============================================================
-- TABLE: posts
-- Core content table
-- ============================================================

CREATE TABLE posts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
  content TEXT NOT NULL CHECK (char_length(content) <= 2000),
  category post_category NOT NULL DEFAULT 'genel',
  status post_status NOT NULL DEFAULT 'active',
  tags TEXT[],                -- Hashtags
  location TEXT,
  latitude DOUBLE PRECISION,
  longitude DOUBLE PRECISION,
  expires_at TIMESTAMPTZ,    -- NULL = never expires
  is_pinned BOOLEAN DEFAULT FALSE,
  likes_count INTEGER DEFAULT 0,
  comments_count INTEGER DEFAULT 0,
  shares_count INTEGER DEFAULT 0,
  views_count INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  deleted_at TIMESTAMPTZ      -- Soft delete
);

CREATE INDEX idx_posts_user_id ON posts(user_id);
CREATE INDEX idx_posts_category ON posts(category);
CREATE INDEX idx_posts_status ON posts(status);
CREATE INDEX idx_posts_created_at ON posts(created_at DESC);
CREATE INDEX idx_posts_tags ON posts USING GIN(tags);
CREATE INDEX idx_posts_location ON posts(location);

-- ============================================================
-- TABLE: post_media
-- Media attachments for posts (images, videos)
-- ============================================================

CREATE TABLE post_media (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  post_id UUID NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
  url TEXT NOT NULL,
  media_type TEXT NOT NULL CHECK (media_type IN ('image', 'video')),
  width INTEGER,
  height INTEGER,
  size_bytes INTEGER,
  sort_order INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_post_media_post_id ON post_media(post_id);

-- ============================================================
-- TABLE: likes
-- ============================================================

CREATE TABLE likes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
  post_id UUID NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(user_id, post_id)
);

CREATE INDEX idx_likes_post_id ON likes(post_id);
CREATE INDEX idx_likes_user_id ON likes(user_id);

-- ============================================================
-- TABLE: comments
-- ============================================================

CREATE TABLE comments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  post_id UUID NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
  parent_id UUID REFERENCES comments(id) ON DELETE CASCADE, -- Nested comments
  content TEXT NOT NULL CHECK (char_length(content) <= 1000),
  likes_count INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_comments_post_id ON comments(post_id);
CREATE INDEX idx_comments_user_id ON comments(user_id);
CREATE INDEX idx_comments_parent_id ON comments(parent_id);

-- ============================================================
-- TABLE: follows
-- ============================================================

CREATE TABLE follows (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  follower_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
  following_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(follower_id, following_id),
  CHECK (follower_id != following_id)
);

CREATE INDEX idx_follows_follower_id ON follows(follower_id);
CREATE INDEX idx_follows_following_id ON follows(following_id);

-- ============================================================
-- TABLE: bookmarks
-- ============================================================

CREATE TABLE bookmarks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
  post_id UUID NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(user_id, post_id)
);

CREATE INDEX idx_bookmarks_user_id ON bookmarks(user_id);

-- ============================================================
-- TABLE: notifications
-- ============================================================

CREATE TABLE notifications (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
  actor_id UUID REFERENCES profiles(id) ON DELETE SET NULL,
  type notification_type NOT NULL,
  post_id UUID REFERENCES posts(id) ON DELETE CASCADE,
  comment_id UUID REFERENCES comments(id) ON DELETE CASCADE,
  message TEXT,
  is_read BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_notifications_user_id ON notifications(user_id);
CREATE INDEX idx_notifications_is_read ON notifications(user_id, is_read);
CREATE INDEX idx_notifications_created_at ON notifications(created_at DESC);

-- ============================================================
-- TABLE: ads
-- Sponsored posts / advertisement system
-- ============================================================

CREATE TABLE ads (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  advertiser_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  content TEXT NOT NULL,
  image_url TEXT,
  target_url TEXT,
  category post_category,          -- Target category (NULL = all)
  target_location TEXT,             -- Target location (NULL = all)
  status ad_status NOT NULL DEFAULT 'pending',
  impressions INTEGER DEFAULT 0,
  clicks INTEGER DEFAULT 0,
  budget_cents INTEGER DEFAULT 0,   -- Budget in cents
  spent_cents INTEGER DEFAULT 0,
  starts_at TIMESTAMPTZ,
  ends_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_ads_advertiser_id ON ads(advertiser_id);
CREATE INDEX idx_ads_status ON ads(status);
CREATE INDEX idx_ads_category ON ads(category);

-- ============================================================
-- TABLE: reports
-- Content moderation
-- ============================================================

CREATE TABLE reports (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  reporter_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
  post_id UUID REFERENCES posts(id) ON DELETE CASCADE,
  comment_id UUID REFERENCES comments(id) ON DELETE CASCADE,
  reported_user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
  reason report_reason NOT NULL,
  description TEXT,
  is_resolved BOOLEAN DEFAULT FALSE,
  resolved_by UUID REFERENCES profiles(id),
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_reports_is_resolved ON reports(is_resolved);

-- ============================================================
-- TABLE: hashtags (for trending / discovery)
-- ============================================================

CREATE TABLE hashtags (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT UNIQUE NOT NULL,
  usage_count INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_hashtags_name ON hashtags(name);
CREATE INDEX idx_hashtags_usage_count ON hashtags(usage_count DESC);

-- ============================================================
-- FUNCTIONS: Auto-update updated_at
-- ============================================================

CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER profiles_updated_at
  BEFORE UPDATE ON profiles
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER posts_updated_at
  BEFORE UPDATE ON posts
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER comments_updated_at
  BEFORE UPDATE ON comments
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER ads_updated_at
  BEFORE UPDATE ON ads
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ============================================================
-- FUNCTIONS: Counter cache triggers
-- ============================================================

-- Likes count on posts
CREATE OR REPLACE FUNCTION update_post_likes_count()
RETURNS TRIGGER AS $$
BEGIN
  IF TG_OP = 'INSERT' THEN
    UPDATE posts SET likes_count = likes_count + 1 WHERE id = NEW.post_id;
    RETURN NEW;
  ELSIF TG_OP = 'DELETE' THEN
    UPDATE posts SET likes_count = likes_count - 1 WHERE id = OLD.post_id;
    RETURN OLD;
  END IF;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER trigger_post_likes_count
  AFTER INSERT OR DELETE ON likes
  FOR EACH ROW EXECUTE FUNCTION update_post_likes_count();

-- Comments count on posts
CREATE OR REPLACE FUNCTION update_post_comments_count()
RETURNS TRIGGER AS $$
BEGIN
  IF TG_OP = 'INSERT' THEN
    UPDATE posts SET comments_count = comments_count + 1 WHERE id = NEW.post_id;
    RETURN NEW;
  ELSIF TG_OP = 'DELETE' THEN
    UPDATE posts SET comments_count = comments_count - 1 WHERE id = OLD.post_id;
    RETURN OLD;
  END IF;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER trigger_post_comments_count
  AFTER INSERT OR DELETE ON comments
  FOR EACH ROW EXECUTE FUNCTION update_post_comments_count();

-- Followers/following count
CREATE OR REPLACE FUNCTION update_follow_counts()
RETURNS TRIGGER AS $$
BEGIN
  IF TG_OP = 'INSERT' THEN
    UPDATE profiles SET following_count = following_count + 1 WHERE id = NEW.follower_id;
    UPDATE profiles SET followers_count = followers_count + 1 WHERE id = NEW.following_id;
    RETURN NEW;
  ELSIF TG_OP = 'DELETE' THEN
    UPDATE profiles SET following_count = following_count - 1 WHERE id = OLD.follower_id;
    UPDATE profiles SET followers_count = followers_count - 1 WHERE id = OLD.following_id;
    RETURN OLD;
  END IF;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER trigger_follow_counts
  AFTER INSERT OR DELETE ON follows
  FOR EACH ROW EXECUTE FUNCTION update_follow_counts();

-- Posts count on profiles
CREATE OR REPLACE FUNCTION update_profile_posts_count()
RETURNS TRIGGER AS $$
BEGIN
  IF TG_OP = 'INSERT' THEN
    UPDATE profiles SET posts_count = posts_count + 1 WHERE id = NEW.user_id;
    RETURN NEW;
  ELSIF TG_OP = 'DELETE' THEN
    UPDATE profiles SET posts_count = posts_count - 1 WHERE id = OLD.user_id;
    RETURN OLD;
  END IF;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER trigger_profile_posts_count
  AFTER INSERT OR DELETE ON posts
  FOR EACH ROW EXECUTE FUNCTION update_profile_posts_count();

-- ============================================================
-- FUNCTION: Auto-create profile on signup
-- ============================================================

CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO profiles (id, username, display_name, avatar_url)
  VALUES (
    NEW.id,
    COALESCE(NEW.raw_user_meta_data->>'username', 'user_' || substr(NEW.id::text, 1, 8)),
    COALESCE(NEW.raw_user_meta_data->>'full_name', NEW.raw_user_meta_data->>'name', ''),
    COALESCE(NEW.raw_user_meta_data->>'avatar_url', '')
  );
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION handle_new_user();

-- ============================================================
-- FUNCTION: Expire old posts (call via pg_cron or edge function)
-- ============================================================

CREATE OR REPLACE FUNCTION expire_old_posts()
RETURNS void AS $$
BEGIN
  UPDATE posts
  SET status = 'expired'
  WHERE status = 'active'
    AND expires_at IS NOT NULL
    AND expires_at < now();
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================================
-- RLS POLICIES
-- ============================================================

-- Enable RLS on all tables
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE posts ENABLE ROW LEVEL SECURITY;
ALTER TABLE post_media ENABLE ROW LEVEL SECURITY;
ALTER TABLE likes ENABLE ROW LEVEL SECURITY;
ALTER TABLE comments ENABLE ROW LEVEL SECURITY;
ALTER TABLE follows ENABLE ROW LEVEL SECURITY;
ALTER TABLE bookmarks ENABLE ROW LEVEL SECURITY;
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE ads ENABLE ROW LEVEL SECURITY;
ALTER TABLE reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE hashtags ENABLE ROW LEVEL SECURITY;

-- ---------------------
-- PROFILES
-- ---------------------
CREATE POLICY "Profiles are viewable by everyone"
  ON profiles FOR SELECT
  USING (true);

CREATE POLICY "Users can update own profile"
  ON profiles FOR UPDATE
  USING (auth.uid() = id)
  WITH CHECK (auth.uid() = id);

-- No INSERT policy needed: handle_new_user() runs as SECURITY DEFINER

-- ---------------------
-- POSTS
-- ---------------------
CREATE POLICY "Active posts are viewable by everyone"
  ON posts FOR SELECT
  USING (deleted_at IS NULL AND (status = 'active' OR user_id = auth.uid()));

CREATE POLICY "Authenticated users can create posts"
  ON posts FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own posts"
  ON posts FOR UPDATE
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can soft-delete own posts"
  ON posts FOR DELETE
  USING (auth.uid() = user_id);

-- ---------------------
-- POST_MEDIA
-- ---------------------
CREATE POLICY "Post media is viewable by everyone"
  ON post_media FOR SELECT
  USING (true);

CREATE POLICY "Users can add media to own posts"
  ON post_media FOR INSERT
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM posts WHERE posts.id = post_id AND posts.user_id = auth.uid()
    )
  );

CREATE POLICY "Users can delete media from own posts"
  ON post_media FOR DELETE
  USING (
    EXISTS (
      SELECT 1 FROM posts WHERE posts.id = post_id AND posts.user_id = auth.uid()
    )
  );

-- ---------------------
-- LIKES
-- ---------------------
CREATE POLICY "Likes are viewable by everyone"
  ON likes FOR SELECT
  USING (true);

CREATE POLICY "Authenticated users can like"
  ON likes FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can remove own likes"
  ON likes FOR DELETE
  USING (auth.uid() = user_id);

-- ---------------------
-- COMMENTS
-- ---------------------
CREATE POLICY "Comments are viewable by everyone"
  ON comments FOR SELECT
  USING (deleted_at IS NULL);

CREATE POLICY "Authenticated users can comment"
  ON comments FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own comments"
  ON comments FOR UPDATE
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own comments"
  ON comments FOR DELETE
  USING (auth.uid() = user_id);

-- ---------------------
-- FOLLOWS
-- ---------------------
CREATE POLICY "Follows are viewable by everyone"
  ON follows FOR SELECT
  USING (true);

CREATE POLICY "Authenticated users can follow"
  ON follows FOR INSERT
  WITH CHECK (auth.uid() = follower_id);

CREATE POLICY "Users can unfollow"
  ON follows FOR DELETE
  USING (auth.uid() = follower_id);

-- ---------------------
-- BOOKMARKS
-- ---------------------
CREATE POLICY "Users can view own bookmarks"
  ON bookmarks FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can create bookmarks"
  ON bookmarks FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own bookmarks"
  ON bookmarks FOR DELETE
  USING (auth.uid() = user_id);

-- ---------------------
-- NOTIFICATIONS
-- ---------------------
CREATE POLICY "Users can view own notifications"
  ON notifications FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "System can create notifications"
  ON notifications FOR INSERT
  WITH CHECK (true);  -- Created by triggers/functions running as SECURITY DEFINER

CREATE POLICY "Users can mark own notifications read"
  ON notifications FOR UPDATE
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

-- ---------------------
-- ADS
-- ---------------------
CREATE POLICY "Active ads are viewable by everyone"
  ON ads FOR SELECT
  USING (status = 'active' OR advertiser_id = auth.uid());

CREATE POLICY "Advertisers can create ads"
  ON ads FOR INSERT
  WITH CHECK (auth.uid() = advertiser_id);

CREATE POLICY "Advertisers can update own ads"
  ON ads FOR UPDATE
  USING (auth.uid() = advertiser_id)
  WITH CHECK (auth.uid() = advertiser_id);

-- ---------------------
-- REPORTS
-- ---------------------
CREATE POLICY "Users can create reports"
  ON reports FOR INSERT
  WITH CHECK (auth.uid() = reporter_id);

CREATE POLICY "Users can view own reports"
  ON reports FOR SELECT
  USING (auth.uid() = reporter_id);

-- ---------------------
-- HASHTAGS
-- ---------------------
CREATE POLICY "Hashtags are viewable by everyone"
  ON hashtags FOR SELECT
  USING (true);

-- Hashtag insert/update handled by SECURITY DEFINER functions only

-- ============================================================
-- STORAGE BUCKETS
-- ============================================================

-- Run these via Supabase Dashboard > Storage, or via SQL:
INSERT INTO storage.buckets (id, name, public)
VALUES
  ('avatars', 'avatars', true),
  ('post-media', 'post-media', true),
  ('ad-media', 'ad-media', true);

-- Storage policies
CREATE POLICY "Avatar images are publicly accessible"
  ON storage.objects FOR SELECT
  USING (bucket_id = 'avatars');

CREATE POLICY "Users can upload own avatar"
  ON storage.objects FOR INSERT
  WITH CHECK (bucket_id = 'avatars' AND auth.uid()::text = (storage.foldername(name))[1]);

CREATE POLICY "Users can update own avatar"
  ON storage.objects FOR UPDATE
  USING (bucket_id = 'avatars' AND auth.uid()::text = (storage.foldername(name))[1]);

CREATE POLICY "Post media is publicly accessible"
  ON storage.objects FOR SELECT
  USING (bucket_id = 'post-media');

CREATE POLICY "Users can upload post media"
  ON storage.objects FOR INSERT
  WITH CHECK (bucket_id = 'post-media' AND auth.uid()::text = (storage.foldername(name))[1]);

CREATE POLICY "Users can delete own post media"
  ON storage.objects FOR DELETE
  USING (bucket_id = 'post-media' AND auth.uid()::text = (storage.foldername(name))[1]);

CREATE POLICY "Ad media is publicly accessible"
  ON storage.objects FOR SELECT
  USING (bucket_id = 'ad-media');

CREATE POLICY "Advertisers can upload ad media"
  ON storage.objects FOR INSERT
  WITH CHECK (bucket_id = 'ad-media' AND auth.uid()::text = (storage.foldername(name))[1]);
```

---

## 2. Auth Flow Diagrams

### 2.1 OTP (Email) Flow

```
User                    Next.js App                 Supabase Auth
 |                          |                            |
 |-- Enter email ---------->|                            |
 |                          |-- signInWithOtp({email}) ->|
 |                          |                            |-- Send OTP email
 |                          |<-- { success } ------------|
 |                          |                            |
 |-- Enter OTP code ------->|                            |
 |                          |-- verifyOtp({             |
 |                          |     email, token,          |
 |                          |     type:'email'           |
 |                          |   }) -------------------->|
 |                          |                            |-- Validate OTP
 |                          |                            |-- Create/find user
 |                          |                            |-- Trigger handle_new_user()
 |                          |<-- { session, user } ------|
 |                          |                            |
 |                          |-- Set cookie (pkce) ------>|
 |<-- Redirect to /feed ----|                            |
```

### 2.2 OAuth (Google/Apple/GitHub) Flow

```
User                    Next.js App                 Supabase Auth          Provider
 |                          |                            |                     |
 |-- Click "Sign in with    |                            |                     |
 |   Google" -------------->|                            |                     |
 |                          |-- signInWithOAuth({        |                     |
 |                          |     provider: 'google',    |                     |
 |                          |     redirectTo: callback   |                     |
 |                          |   }) -------------------->|                     |
 |                          |                            |-- Generate auth URL |
 |<-- Redirect to Google ---|<-- { url } ---------------|                     |
 |                          |                            |                     |
 |-- Authenticate --------->|                            |                     |
 |                          |                            |<-- Auth code -------|
 |                          |                            |-- Exchange for token|
 |                          |                            |-- Create/find user  |
 |                          |                            |-- Trigger           |
 |                          |                            |   handle_new_user() |
 |                          |                            |                     |
 |-- Redirect to callback ->|                            |                     |
 |                          |-- Exchange code for session|                     |
 |                          |   GET /auth/callback ------+                     |
 |                          |<-- { session, user } ------|                     |
 |<-- Redirect to /feed ----|                            |                     |
```

### 2.3 Session Management Flow

```
                       Next.js Middleware
Request ──────────────> ┌─────────────────────────┐
                        │ 1. Read supabase cookies │
                        │ 2. Refresh if expired    │
                        │ 3. Check route protection │
                        └───────┬─────────────────┘
                                │
                   ┌────────────┼────────────────┐
                   │            │                 │
              Protected     Public           Auth pages
              (no session)  (pass through)   (has session)
                   │                              │
              Redirect to                    Redirect to
              /auth/login                    /feed
```

### 2.4 Auth Callback Route (`/auth/callback`)

```
Browser redirect with code ──> /auth/callback (Route Handler)
                                      │
                                      ├── Extract `code` from URL params
                                      ├── supabase.auth.exchangeCodeForSession(code)
                                      ├── Success? Redirect to /feed
                                      └── Failure? Redirect to /auth/login?error=...
```

---

## 3. API Route Design

### 3.1 Architecture Decision

**Primary data access:** Supabase JS client SDK (direct DB queries with RLS) — no REST API layer needed for most operations.

**Next.js Route Handlers (`app/api/`):** Only for operations that need server-side logic:

| Route | Method | Purpose |
|-------|--------|---------|
| `/auth/callback` | `GET` | OAuth callback, exchange code for session |
| `/api/posts/expire` | `POST` | Cron job to expire old posts (called by Netlify scheduled function or Supabase pg_cron) |
| `/api/upload/avatar` | `POST` | Upload avatar with server-side validation (resize, format check) |
| `/api/upload/media` | `POST` | Upload post media with server-side validation |
| `/api/ads/impression` | `POST` | Track ad impression (prevents client-side manipulation) |
| `/api/ads/click` | `POST` | Track ad click |
| `/api/notifications/push` | `POST` | Send push notification (future: web push subscription) |
| `/api/search` | `GET` | Full-text search with Supabase `textSearch()` |
| `/api/feed` | `GET` | Personalized feed algorithm (optional, can start with chronological) |

### 3.2 Supabase Client SDK Operations (No API Route Needed)

These run directly from React Server Components or client components via the Supabase client:

```
POSTS
  supabase.from('posts').select('*, profiles(*), post_media(*)').order('created_at', { ascending: false })
  supabase.from('posts').insert({ ... })
  supabase.from('posts').update({ ... }).eq('id', postId)
  supabase.from('posts').delete().eq('id', postId)

LIKES
  supabase.from('likes').insert({ user_id, post_id })
  supabase.from('likes').delete().match({ user_id, post_id })

COMMENTS
  supabase.from('comments').select('*, profiles(*)').eq('post_id', postId)
  supabase.from('comments').insert({ ... })

FOLLOWS
  supabase.from('follows').insert({ follower_id, following_id })
  supabase.from('follows').delete().match({ follower_id, following_id })

PROFILES
  supabase.from('profiles').select('*').eq('username', username).single()
  supabase.from('profiles').update({ ... }).eq('id', userId)

BOOKMARKS
  supabase.from('bookmarks').select('*, posts(*, profiles(*))').eq('user_id', userId)
  supabase.from('bookmarks').insert({ user_id, post_id })
  supabase.from('bookmarks').delete().match({ user_id, post_id })

NOTIFICATIONS
  supabase.from('notifications').select('*, profiles:actor_id(*)').eq('user_id', userId)
  supabase.from('notifications').update({ is_read: true }).eq('id', notifId)

SEARCH (simple category/tag filter)
  supabase.from('posts').select('*').eq('category', category).contains('tags', [tag])
```

### 3.3 Realtime Subscriptions

```typescript
// New posts in feed
supabase.channel('public:posts').on('postgres_changes',
  { event: 'INSERT', schema: 'public', table: 'posts' },
  (payload) => { /* prepend to feed */ }
).subscribe()

// Notifications for current user
supabase.channel(`notifications:${userId}`).on('postgres_changes',
  { event: 'INSERT', schema: 'public', table: 'notifications', filter: `user_id=eq.${userId}` },
  (payload) => { /* show notification */ }
).subscribe()
```

---

## 4. Component Hierarchy

```
app/
├── layout.tsx                          # Root layout (ThemeProvider, Supabase provider, fonts)
│   ├── (auth)/                         # Auth group (no main nav)
│   │   ├── layout.tsx                  # Centered card layout
│   │   ├── login/page.tsx              # Login form (OTP + OAuth buttons)
│   │   ├── verify/page.tsx             # OTP verification
│   │   └── callback/route.ts           # OAuth callback handler
│   │
│   ├── (main)/                         # Main app group (with nav)
│   │   ├── layout.tsx                  # Sidebar + Header + Main content
│   │   │   ├── <Sidebar />             # Left sidebar navigation
│   │   │   │   ├── <Logo />
│   │   │   │   ├── <NavLinks />        # Feed, Explore, Bookmarks, Profile, etc.
│   │   │   │   └── <CreatePostButton />
│   │   │   ├── <Header />              # Top bar (search, notifications, user menu)
│   │   │   │   ├── <SearchBar />
│   │   │   │   ├── <NotificationBell />
│   │   │   │   └── <UserMenu />
│   │   │   └── <RightPanel />          # Right sidebar (trends, ads, suggestions)
│   │   │       ├── <TrendingTags />
│   │   │       ├── <SuggestedUsers />
│   │   │       └── <AdBanner />
│   │   │
│   │   ├── feed/page.tsx               # Home feed
│   │   │   ├── <FeedTabs />            # All, Following, Category tabs
│   │   │   ├── <CreatePostInline />    # Quick post composer
│   │   │   └── <PostList />            # Infinite scroll post list
│   │   │       └── <PostCard />        # Individual post
│   │   │           ├── <PostHeader />  # Avatar, name, time, category badge
│   │   │           ├── <PostContent /> # Text + media
│   │   │           ├── <PostMedia />   # Image/video gallery
│   │   │           ├── <PostActions /> # Like, Comment, Share, Bookmark
│   │   │           └── <PostStats />   # Counts
│   │   │
│   │   ├── post/[id]/page.tsx          # Single post detail
│   │   │   ├── <PostCard />            # Full post
│   │   │   ├── <CommentComposer />     # Write comment
│   │   │   └── <CommentList />         # Threaded comments
│   │   │       └── <CommentItem />
│   │   │
│   │   ├── explore/page.tsx            # Discover / search
│   │   │   ├── <CategoryGrid />        # Category cards (Emlak, Arac, etc.)
│   │   │   ├── <SearchResults />
│   │   │   └── <TrendingPosts />
│   │   │
│   │   ├── profile/[username]/page.tsx # User profile
│   │   │   ├── <ProfileHeader />       # Avatar, bio, stats, follow button
│   │   │   │   ├── <TrustBadge />      # Verification / trust score
│   │   │   │   └── <FollowButton />
│   │   │   ├── <ProfileTabs />         # Posts, Likes, Media
│   │   │   └── <PostList />            # User's posts
│   │   │
│   │   ├── settings/page.tsx           # User settings
│   │   │   ├── <ProfileEditForm />
│   │   │   ├── <NotificationSettings />
│   │   │   └── <AccountSettings />
│   │   │
│   │   ├── bookmarks/page.tsx          # Saved posts
│   │   │   └── <PostList />
│   │   │
│   │   └── notifications/page.tsx      # All notifications
│   │       └── <NotificationList />
│   │           └── <NotificationItem />
│   │
│   └── (admin)/                        # Admin/advertiser area (future)
│       └── ads/page.tsx
│           ├── <AdCreateForm />
│           └── <AdDashboard />

components/                             # Shared components
├── ui/                                 # shadcn/ui components (auto-generated)
│   ├── button.tsx
│   ├── card.tsx
│   ├── dialog.tsx
│   ├── input.tsx
│   ├── avatar.tsx
│   ├── badge.tsx
│   ├── tabs.tsx
│   ├── dropdown-menu.tsx
│   ├── skeleton.tsx
│   └── toast.tsx
├── post/
│   ├── post-card.tsx
│   ├── post-composer.tsx
│   ├── post-actions.tsx
│   ├── post-media-gallery.tsx
│   └── post-category-badge.tsx
├── profile/
│   ├── profile-header.tsx
│   ├── trust-badge.tsx
│   └── follow-button.tsx
├── layout/
│   ├── sidebar.tsx
│   ├── header.tsx
│   ├── right-panel.tsx
│   └── mobile-nav.tsx
├── feed/
│   ├── feed-tabs.tsx
│   └── infinite-scroll.tsx
├── comment/
│   ├── comment-item.tsx
│   └── comment-composer.tsx
├── notification/
│   ├── notification-bell.tsx
│   └── notification-item.tsx
├── search/
│   ├── search-bar.tsx
│   └── search-results.tsx
├── ad/
│   └── ad-banner.tsx
└── shared/
    ├── loading-skeleton.tsx
    ├── empty-state.tsx
    ├── error-boundary.tsx
    ├── masonic-pattern.tsx              # Decorative geometric SVG patterns
    └── category-icon.tsx

lib/
├── supabase/
│   ├── client.ts                       # Browser Supabase client
│   ├── server.ts                       # Server Component Supabase client
│   ├── middleware.ts                    # Middleware Supabase client
│   └── admin.ts                        # Service role client (server only)
├── hooks/
│   ├── use-auth.ts                     # Auth state hook
│   ├── use-posts.ts                    # Posts query/mutation hooks
│   ├── use-likes.ts
│   ├── use-comments.ts
│   ├── use-follow.ts
│   ├── use-notifications.ts
│   ├── use-bookmarks.ts
│   └── use-infinite-scroll.ts
├── utils/
│   ├── cn.ts                           # className merge utility
│   ├── format-date.ts                  # Relative time formatting
│   └── constants.ts                    # Category labels, colors, etc.
└── types/
    └── database.ts                     # Generated Supabase types
```

---

## 5. Phase Breakdown & Tasks

### Phase 0: Project Setup (Foundation)

#### Task 0.1: Initialize Next.js Project

**Files:**
- Create: `package.json`, `tsconfig.json`, `next.config.mjs`, `tailwind.config.ts`, `app/layout.tsx`, `app/page.tsx`

**Step 1: Create Next.js app**
```bash
npx create-next-app@latest generic --typescript --tailwind --eslint --app --src-dir=false --import-alias="@/*"
cd generic
```

**Step 2: Install core dependencies**
```bash
npm install @supabase/supabase-js @supabase/ssr
npm install -D supabase
```

**Step 3: Initialize shadcn/ui**
```bash
npx shadcn@latest init
# Choose: New York style, Slate base color, CSS variables: yes
```

**Step 4: Add essential shadcn components**
```bash
npx shadcn@latest add button card input avatar badge tabs dialog dropdown-menu toast skeleton separator sheet form label textarea select
```

**Step 5: Commit**
```bash
git add .
git commit -m "chore: initialize Next.js project with shadcn/ui and Supabase deps"
```

---

#### Task 0.2: Supabase Project Setup

**Files:**
- Create: `.env.local`
- Create: `lib/supabase/client.ts`
- Create: `lib/supabase/server.ts`
- Create: `lib/supabase/middleware.ts`

**Step 1: Create `.env.local`**
```env
NEXT_PUBLIC_SUPABASE_URL=https://YOUR_PROJECT.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=YOUR_ANON_KEY
```

**Step 2: Create browser client** (`lib/supabase/client.ts`)
```typescript
import { createBrowserClient } from "@supabase/ssr";

export function createClient() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  );
}
```

**Step 3: Create server client** (`lib/supabase/server.ts`)
```typescript
import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";

export async function createClient() {
  const cookieStore = await cookies();

  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return cookieStore.getAll();
        },
        setAll(cookiesToSet) {
          try {
            cookiesToSet.forEach(({ name, value, options }) =>
              cookieStore.set(name, value, options)
            );
          } catch {
            // Called from Server Component — ignore
          }
        },
      },
    }
  );
}
```

**Step 4: Create middleware client** (`lib/supabase/middleware.ts`)
```typescript
import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";

export async function updateSession(request: NextRequest) {
  let supabaseResponse = NextResponse.next({ request });

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return request.cookies.getAll();
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value }) =>
            request.cookies.set(name, value)
          );
          supabaseResponse = NextResponse.next({ request });
          cookiesToSet.forEach(({ name, value, options }) =>
            supabaseResponse.cookies.set(name, value, options)
          );
        },
      },
    }
  );

  const {
    data: { user },
  } = await supabase.auth.getUser();

  // Protect routes
  const isAuthPage = request.nextUrl.pathname.startsWith("/auth") ||
                     request.nextUrl.pathname.startsWith("/login");
  const isProtectedRoute = request.nextUrl.pathname.startsWith("/feed") ||
                           request.nextUrl.pathname.startsWith("/settings") ||
                           request.nextUrl.pathname.startsWith("/bookmarks") ||
                           request.nextUrl.pathname.startsWith("/notifications");

  if (!user && isProtectedRoute) {
    const url = request.nextUrl.clone();
    url.pathname = "/login";
    return NextResponse.redirect(url);
  }

  if (user && isAuthPage) {
    const url = request.nextUrl.clone();
    url.pathname = "/feed";
    return NextResponse.redirect(url);
  }

  return supabaseResponse;
}
```

**Step 5: Create middleware** (`middleware.ts` at project root)
```typescript
import { type NextRequest } from "next/server";
import { updateSession } from "@/lib/supabase/middleware";

export async function middleware(request: NextRequest) {
  return await updateSession(request);
}

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
};
```

**Step 6: Commit**
```bash
git add lib/supabase/ .env.local middleware.ts
git commit -m "feat: configure Supabase client for browser, server, and middleware"
```

---

#### Task 0.3: Run Database Migration

**Step 1: Open Supabase Dashboard > SQL Editor**

**Step 2: Paste and run the complete SQL from Section 1 of this plan**

**Step 3: Generate TypeScript types**
```bash
npx supabase gen types typescript --project-id YOUR_PROJECT_ID > lib/types/database.ts
```

**Step 4: Commit**
```bash
git add lib/types/database.ts
git commit -m "feat: add Supabase database types"
```

---

#### Task 0.4: Configure Design System (Masonic Theme)

**Files:**
- Modify: `tailwind.config.ts`
- Modify: `app/globals.css`
- Create: `lib/utils/cn.ts`
- Create: `lib/utils/constants.ts`

**Step 1: Update Tailwind config for Masonic colors**
```typescript
// tailwind.config.ts
import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: ["./components/**/*.{ts,tsx}", "./app/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Masonic palette
        navy: {
          50: "#eef2f7",
          100: "#d4dde8",
          200: "#a9bad1",
          300: "#7e98ba",
          400: "#5375a3",
          500: "#2d4a6f",
          600: "#1e3554",
          700: "#152a45",
          800: "#0d1f36",
          900: "#061427",
          950: "#030a14",
        },
        gold: {
          50: "#fdf9ef",
          100: "#faf0d5",
          200: "#f4deaa",
          300: "#edc974",
          400: "#e5b043",
          500: "#d4952a",
          600: "#b87520",
          700: "#98581d",
          800: "#7c461e",
          900: "#673b1c",
          950: "#3a1d0c",
        },
        marble: {
          50: "#fafaf9",
          100: "#f5f5f4",
          200: "#e7e5e4",
          300: "#d6d3d1",
        },
        slate: {
          850: "#1a2332",
        },
      },
      fontFamily: {
        serif: ["Georgia", "Cambria", "Times New Roman", "serif"],
        sans: ["Inter", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};

export default config;
```

**Step 2: Update globals.css with CSS variables**
```css
/* app/globals.css - add Masonic theme variables alongside shadcn defaults */
@layer base {
  :root {
    --background: 40 6% 97%;       /* marble-50 */
    --foreground: 210 40% 10%;     /* navy-900 */
    --card: 0 0% 100%;
    --card-foreground: 210 40% 10%;
    --primary: 210 42% 31%;        /* navy-600 */
    --primary-foreground: 40 6% 97%;
    --secondary: 37 71% 50%;       /* gold-500 */
    --secondary-foreground: 210 40% 10%;
    --accent: 37 71% 50%;          /* gold-500 */
    --accent-foreground: 210 40% 10%;
    --muted: 40 6% 93%;
    --muted-foreground: 210 20% 40%;
    --border: 30 10% 85%;
    --ring: 210 42% 31%;
    --radius: 0.5rem;
  }

  .dark {
    --background: 210 50% 8%;      /* navy-950 */
    --foreground: 40 6% 95%;
    --card: 210 45% 12%;
    --card-foreground: 40 6% 95%;
    --primary: 37 71% 50%;         /* gold-500 */
    --primary-foreground: 210 50% 8%;
    --secondary: 210 42% 31%;
    --secondary-foreground: 40 6% 95%;
    --accent: 37 71% 50%;
    --accent-foreground: 210 50% 8%;
    --muted: 210 45% 15%;
    --muted-foreground: 210 20% 60%;
    --border: 210 40% 20%;
    --ring: 37 71% 50%;
  }
}
```

**Step 3: Create constants** (`lib/utils/constants.ts`)
```typescript
export const CATEGORIES = {
  genel: { label: "Genel", icon: "Globe", color: "bg-navy-500" },
  emlak: { label: "Emlak", icon: "Home", color: "bg-emerald-600" },
  arac: { label: "Arac", icon: "Car", color: "bg-blue-600" },
  hizmet: { label: "Hizmet", icon: "Wrench", color: "bg-amber-600" },
  tanidik_arama: { label: "Tanidik Arama", icon: "Users", color: "bg-purple-600" },
} as const;

export const POST_MAX_LENGTH = 2000;
export const COMMENT_MAX_LENGTH = 1000;
export const MAX_MEDIA_PER_POST = 4;
export const MAX_MEDIA_SIZE_MB = 5;
export const POSTS_PER_PAGE = 20;
```

**Step 4: Commit**
```bash
git add tailwind.config.ts app/globals.css lib/utils/
git commit -m "feat: configure Masonic design system with navy/gold theme"
```

---

### Phase 1: Authentication

#### Task 1.1: Login Page

**Files:**
- Create: `app/(auth)/layout.tsx`
- Create: `app/(auth)/login/page.tsx`

**Step 1: Write auth layout** (`app/(auth)/layout.tsx`)
```typescript
export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen flex items-center justify-center bg-navy-950 p-4">
      <div className="w-full max-w-md">{children}</div>
    </div>
  );
}
```

**Step 2: Write login page** (`app/(auth)/login/page.tsx`)
```typescript
"use client";

import { useState } from "react";
import { createClient } from "@/lib/supabase/client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const supabase = createClient();

  async function handleOtpLogin(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    const { error } = await supabase.auth.signInWithOtp({
      email,
      options: { emailRedirectTo: `${window.location.origin}/auth/callback` },
    });
    setLoading(false);
    if (!error) setSent(true);
  }

  async function handleOAuthLogin(provider: "google" | "apple" | "github") {
    await supabase.auth.signInWithOAuth({
      provider,
      options: { redirectTo: `${window.location.origin}/auth/callback` },
    });
  }

  if (sent) {
    return (
      <Card className="border-gold-500/20">
        <CardHeader>
          <CardTitle className="text-center font-serif">E-posta Gonderildi</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-center text-muted-foreground">
            <strong>{email}</strong> adresine giris linki gonderdik. Lutfen e-postanizi kontrol edin.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-gold-500/20">
      <CardHeader>
        <CardTitle className="text-center font-serif text-2xl">Generic</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <form onSubmit={handleOtpLogin} className="space-y-3">
          <Input
            type="email"
            placeholder="E-posta adresiniz"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? "Gonderiliyor..." : "E-posta ile Giris"}
          </Button>
        </form>

        <div className="relative">
          <div className="absolute inset-0 flex items-center">
            <span className="w-full border-t" />
          </div>
          <div className="relative flex justify-center text-xs uppercase">
            <span className="bg-card px-2 text-muted-foreground">veya</span>
          </div>
        </div>

        <div className="space-y-2">
          <Button variant="outline" className="w-full" onClick={() => handleOAuthLogin("google")}>
            Google ile Giris
          </Button>
          <Button variant="outline" className="w-full" onClick={() => handleOAuthLogin("github")}>
            GitHub ile Giris
          </Button>
          <Button variant="outline" className="w-full" onClick={() => handleOAuthLogin("apple")}>
            Apple ile Giris
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
```

**Step 3: Commit**
```bash
git add app/(auth)/
git commit -m "feat: add login page with OTP and OAuth providers"
```

---

#### Task 1.2: Auth Callback Route

**Files:**
- Create: `app/auth/callback/route.ts`

**Step 1: Write callback handler**
```typescript
// app/auth/callback/route.ts
import { createClient } from "@/lib/supabase/server";
import { NextResponse } from "next/server";

export async function GET(request: Request) {
  const { searchParams, origin } = new URL(request.url);
  const code = searchParams.get("code");
  const next = searchParams.get("next") ?? "/feed";

  if (code) {
    const supabase = await createClient();
    const { error } = await supabase.auth.exchangeCodeForSession(code);
    if (!error) {
      return NextResponse.redirect(`${origin}${next}`);
    }
  }

  return NextResponse.redirect(`${origin}/login?error=auth_failed`);
}
```

**Step 2: Commit**
```bash
git add app/auth/callback/route.ts
git commit -m "feat: add OAuth callback route handler"
```

---

#### Task 1.3: Auth Hook

**Files:**
- Create: `lib/hooks/use-auth.ts`

**Step 1: Write auth hook**
```typescript
"use client";

import { useEffect, useState } from "react";
import { createClient } from "@/lib/supabase/client";
import type { User } from "@supabase/supabase-js";

export function useAuth() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const supabase = createClient();

  useEffect(() => {
    supabase.auth.getUser().then(({ data: { user } }) => {
      setUser(user);
      setLoading(false);
    });

    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (_event, session) => {
        setUser(session?.user ?? null);
      }
    );

    return () => subscription.unsubscribe();
  }, []);

  const signOut = async () => {
    await supabase.auth.signOut();
  };

  return { user, loading, signOut };
}
```

**Step 2: Commit**
```bash
git add lib/hooks/use-auth.ts
git commit -m "feat: add useAuth hook for client-side auth state"
```

---

### Phase 2: Core Layout & Navigation

#### Task 2.1: Main Layout with Sidebar

**Files:**
- Create: `app/(main)/layout.tsx`
- Create: `components/layout/sidebar.tsx`
- Create: `components/layout/header.tsx`
- Create: `components/layout/right-panel.tsx`
- Create: `components/layout/mobile-nav.tsx`

**Step 1: Write Sidebar** (`components/layout/sidebar.tsx`)
```typescript
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

const navItems = [
  { href: "/feed", label: "Akis", icon: "Home" },
  { href: "/explore", label: "Kesfet", icon: "Search" },
  { href: "/notifications", label: "Bildirimler", icon: "Bell" },
  { href: "/bookmarks", label: "Kaydedilenler", icon: "Bookmark" },
  { href: "/profile", label: "Profil", icon: "User" },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="hidden md:flex flex-col w-64 border-r border-border p-4 h-screen sticky top-0">
      <Link href="/feed" className="font-serif text-2xl font-bold text-gold-500 mb-8 px-3">
        Generic
      </Link>
      <nav className="space-y-1 flex-1">
        {navItems.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={cn(
              "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors",
              pathname.startsWith(item.href)
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:bg-muted"
            )}
          >
            {item.label}
          </Link>
        ))}
      </nav>
      <Button className="w-full bg-gold-500 hover:bg-gold-600 text-navy-950 font-semibold">
        Paylas
      </Button>
    </aside>
  );
}
```

**Step 2: Write main layout** (`app/(main)/layout.tsx`)
```typescript
import { Sidebar } from "@/components/layout/sidebar";
import { Header } from "@/components/layout/header";
import { RightPanel } from "@/components/layout/right-panel";

export default function MainLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="flex-1 flex flex-col">
        <Header />
        <main className="flex-1 flex">
          <div className="flex-1 max-w-2xl border-r border-border">
            {children}
          </div>
          <RightPanel />
        </main>
      </div>
    </div>
  );
}
```

**Step 3: Create stub Header and RightPanel** (minimal implementations, fleshed out later)

**Step 4: Commit**
```bash
git add app/(main)/ components/layout/
git commit -m "feat: add main layout with sidebar, header, and right panel"
```

---

### Phase 3: Post System (Core Feature)

#### Task 3.1: Post Card Component

**Files:**
- Create: `components/post/post-card.tsx`
- Create: `components/post/post-header.tsx`
- Create: `components/post/post-actions.tsx`
- Create: `components/post/post-media-gallery.tsx`
- Create: `components/post/post-category-badge.tsx`

**Step 1: Write PostCard**
```typescript
// components/post/post-card.tsx
import { Card } from "@/components/ui/card";
import { PostHeader } from "./post-header";
import { PostActions } from "./post-actions";
import { PostMediaGallery } from "./post-media-gallery";
import { PostCategoryBadge } from "./post-category-badge";
import type { Database } from "@/lib/types/database";

type Post = Database["public"]["Tables"]["posts"]["Row"] & {
  profiles: Database["public"]["Tables"]["profiles"]["Row"];
  post_media: Database["public"]["Tables"]["post_media"]["Row"][];
};

export function PostCard({ post }: { post: Post }) {
  return (
    <Card className="p-4 border-b rounded-none hover:bg-muted/30 transition-colors">
      <PostHeader profile={post.profiles} createdAt={post.created_at} />
      <PostCategoryBadge category={post.category} />
      <p className="mt-2 text-sm leading-relaxed whitespace-pre-wrap">{post.content}</p>
      {post.post_media.length > 0 && <PostMediaGallery media={post.post_media} />}
      <PostActions post={post} />
    </Card>
  );
}
```

**Step 2: Implement supporting sub-components (PostHeader, PostActions, PostMediaGallery, PostCategoryBadge)**

**Step 3: Commit**
```bash
git add components/post/
git commit -m "feat: add PostCard component with header, actions, media gallery"
```

---

#### Task 3.2: Post Composer

**Files:**
- Create: `components/post/post-composer.tsx`

**Step 1: Write composer with category selection and media upload**

Key features:
- Text area with character count (max 2000)
- Category dropdown (genel, emlak, arac, hizmet, tanidik_arama)
- Media upload button (max 4 images)
- Expiration toggle (7 days / 30 days / never)
- Tag/hashtag extraction from content
- Submit button that calls `supabase.from('posts').insert()`
- Upload media to `post-media` bucket, insert URLs into `post_media` table

**Step 2: Commit**
```bash
git add components/post/post-composer.tsx
git commit -m "feat: add post composer with category selection and media upload"
```

---

#### Task 3.3: Feed Page with Infinite Scroll

**Files:**
- Create: `app/(main)/feed/page.tsx`
- Create: `components/feed/feed-tabs.tsx`
- Create: `components/feed/infinite-scroll.tsx`
- Create: `lib/hooks/use-posts.ts`

**Step 1: Write `use-posts` hook with cursor-based pagination**
```typescript
// lib/hooks/use-posts.ts
"use client";

import { useState, useCallback } from "react";
import { createClient } from "@/lib/supabase/client";
import { POSTS_PER_PAGE } from "@/lib/utils/constants";

export function usePosts(category?: string) {
  const [posts, setPosts] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const supabase = createClient();

  const fetchPosts = useCallback(async (cursor?: string) => {
    setLoading(true);
    let query = supabase
      .from("posts")
      .select("*, profiles(*), post_media(*)")
      .eq("status", "active")
      .is("deleted_at", null)
      .order("created_at", { ascending: false })
      .limit(POSTS_PER_PAGE);

    if (category && category !== "all") {
      query = query.eq("category", category);
    }
    if (cursor) {
      query = query.lt("created_at", cursor);
    }

    const { data, error } = await query;
    setLoading(false);

    if (data) {
      setPosts((prev) => cursor ? [...prev, ...data] : data);
      setHasMore(data.length === POSTS_PER_PAGE);
    }
  }, [category]);

  return { posts, loading, hasMore, fetchPosts };
}
```

**Step 2: Write feed page and FeedTabs (All / Following / per-category tabs)**

**Step 3: Write infinite scroll wrapper using `IntersectionObserver`**

**Step 4: Commit**
```bash
git add app/(main)/feed/ components/feed/ lib/hooks/use-posts.ts
git commit -m "feat: add feed page with infinite scroll and category tabs"
```

---

#### Task 3.4: Single Post Page with Comments

**Files:**
- Create: `app/(main)/post/[id]/page.tsx`
- Create: `components/comment/comment-item.tsx`
- Create: `components/comment/comment-composer.tsx`
- Create: `lib/hooks/use-comments.ts`

**Step 1: Write post detail page fetching post + comments**

**Step 2: Write CommentComposer and CommentItem (with nested reply support via `parent_id`)**

**Step 3: Commit**
```bash
git add app/(main)/post/ components/comment/ lib/hooks/use-comments.ts
git commit -m "feat: add single post page with threaded comments"
```

---

#### Task 3.5: Like, Bookmark, Share Actions

**Files:**
- Create: `lib/hooks/use-likes.ts`
- Create: `lib/hooks/use-bookmarks.ts`
- Modify: `components/post/post-actions.tsx`

**Step 1: Write `use-likes` hook (optimistic toggle)**
```typescript
// lib/hooks/use-likes.ts
"use client";

import { useState } from "react";
import { createClient } from "@/lib/supabase/client";

export function useLike(postId: string, userId: string | undefined, initialLiked: boolean, initialCount: number) {
  const [liked, setLiked] = useState(initialLiked);
  const [count, setCount] = useState(initialCount);
  const supabase = createClient();

  async function toggleLike() {
    if (!userId) return;

    // Optimistic update
    setLiked(!liked);
    setCount(liked ? count - 1 : count + 1);

    if (liked) {
      await supabase.from("likes").delete().match({ user_id: userId, post_id: postId });
    } else {
      await supabase.from("likes").insert({ user_id: userId, post_id: postId });
    }
  }

  return { liked, count, toggleLike };
}
```

**Step 2: Write `use-bookmarks` hook (same pattern)**

**Step 3: Wire into PostActions component**

**Step 4: Commit**
```bash
git add lib/hooks/use-likes.ts lib/hooks/use-bookmarks.ts components/post/post-actions.tsx
git commit -m "feat: add like and bookmark toggle with optimistic updates"
```

---

### Phase 4: User Profiles

#### Task 4.1: Profile Page

**Files:**
- Create: `app/(main)/profile/[username]/page.tsx`
- Create: `components/profile/profile-header.tsx`
- Create: `components/profile/trust-badge.tsx`
- Create: `components/profile/follow-button.tsx`

**Step 1: Write profile page (server component fetching profile + posts)**
```typescript
// app/(main)/profile/[username]/page.tsx
import { createClient } from "@/lib/supabase/server";
import { notFound } from "next/navigation";
import { ProfileHeader } from "@/components/profile/profile-header";
import { PostCard } from "@/components/post/post-card";

export default async function ProfilePage({ params }: { params: { username: string } }) {
  const supabase = await createClient();
  const { data: profile } = await supabase
    .from("profiles")
    .select("*")
    .eq("username", params.username)
    .single();

  if (!profile) notFound();

  const { data: posts } = await supabase
    .from("posts")
    .select("*, profiles(*), post_media(*)")
    .eq("user_id", profile.id)
    .is("deleted_at", null)
    .order("created_at", { ascending: false })
    .limit(20);

  return (
    <div>
      <ProfileHeader profile={profile} />
      <div>
        {posts?.map((post) => <PostCard key={post.id} post={post} />)}
      </div>
    </div>
  );
}
```

**Step 2: Write ProfileHeader with avatar, bio, stats, follow button, trust badge**

**Step 3: Write FollowButton with `use-follow` hook**

**Step 4: Commit**
```bash
git add app/(main)/profile/ components/profile/ lib/hooks/use-follow.ts
git commit -m "feat: add user profile page with follow functionality"
```

---

#### Task 4.2: Profile Settings / Edit

**Files:**
- Create: `app/(main)/settings/page.tsx`
- Create: `components/profile/profile-edit-form.tsx`

**Step 1: Write settings page with form fields for: display_name, bio, location, occupation, interests, avatar upload**

**Step 2: Avatar upload flow: upload to `avatars` bucket → get public URL → update profile**

**Step 3: Commit**
```bash
git add app/(main)/settings/ components/profile/profile-edit-form.tsx
git commit -m "feat: add profile settings page with avatar upload"
```

---

### Phase 5: Search & Discovery

#### Task 5.1: Explore Page

**Files:**
- Create: `app/(main)/explore/page.tsx`
- Create: `components/search/search-bar.tsx`
- Create: `components/search/search-results.tsx`

**Step 1: Write explore page with category grid and search**

**Step 2: Implement search using Supabase full-text search**
```typescript
// Search query
const { data } = await supabase
  .from("posts")
  .select("*, profiles(*), post_media(*)")
  .textSearch("content", query, { type: "websearch" })
  .eq("status", "active")
  .limit(20);
```

**Step 3: Add category cards linking to filtered views**

**Step 4: Commit**
```bash
git add app/(main)/explore/ components/search/
git commit -m "feat: add explore page with search and category filters"
```

---

#### Task 5.2: Trending Tags

**Files:**
- Modify: `components/layout/right-panel.tsx`
- Create: `components/shared/trending-tags.tsx`

**Step 1: Query hashtags table ordered by usage_count**

**Step 2: Display as clickable tag list in right panel**

**Step 3: Commit**
```bash
git add components/layout/right-panel.tsx components/shared/trending-tags.tsx
git commit -m "feat: add trending hashtags to right panel"
```

---

### Phase 6: Notifications

#### Task 6.1: Notification System

**Files:**
- Create: `app/(main)/notifications/page.tsx`
- Create: `components/notification/notification-item.tsx`
- Create: `components/notification/notification-bell.tsx`
- Create: `lib/hooks/use-notifications.ts`

**Step 1: Write notification page listing all notifications for current user**

**Step 2: Write NotificationBell with unread count badge and dropdown**

**Step 3: Add Supabase Realtime subscription for new notifications**
```typescript
// In NotificationBell component
useEffect(() => {
  if (!user) return;
  const channel = supabase
    .channel(`notifications:${user.id}`)
    .on("postgres_changes", {
      event: "INSERT",
      schema: "public",
      table: "notifications",
      filter: `user_id=eq.${user.id}`,
    }, (payload) => {
      setUnreadCount((c) => c + 1);
    })
    .subscribe();

  return () => { supabase.removeChannel(channel); };
}, [user]);
```

**Step 4: Commit**
```bash
git add app/(main)/notifications/ components/notification/ lib/hooks/use-notifications.ts
git commit -m "feat: add notification system with realtime updates"
```

---

### Phase 7: Ad System (Basic)

#### Task 7.1: Ad Banner Component

**Files:**
- Create: `components/ad/ad-banner.tsx`
- Create: `app/api/ads/impression/route.ts`
- Create: `app/api/ads/click/route.ts`

**Step 1: Write AdBanner that fetches a random active ad and displays it**

**Step 2: Write impression tracking route (increments `impressions` count)**

**Step 3: Write click tracking route (increments `clicks` count, redirects to target_url)**

**Step 4: Place AdBanner in RightPanel and between posts in feed (every 5th position)**

**Step 5: Commit**
```bash
git add components/ad/ app/api/ads/
git commit -m "feat: add basic ad banner with impression and click tracking"
```

---

### Phase 8: Polish & Deployment

#### Task 8.1: Masonic Visual Polish

**Files:**
- Create: `components/shared/masonic-pattern.tsx`
- Modify: Various layout components

**Step 1: Add geometric SVG background patterns (subtle triangles, columns, compass motifs)**

**Step 2: Add gold accent borders on cards, serif headers, structured grid alignment**

**Step 3: Ensure dark mode works with navy-950 background**

**Step 4: Commit**
```bash
git add components/shared/masonic-pattern.tsx
git commit -m "feat: add Masonic visual theme with geometric patterns"
```

---

#### Task 8.2: Responsive Design & Mobile Nav

**Files:**
- Create: `components/layout/mobile-nav.tsx`
- Modify: All layout components

**Step 1: Add bottom tab navigation for mobile**

**Step 2: Hide sidebar on mobile, show sheet drawer**

**Step 3: Test all pages at 375px, 768px, 1024px, 1440px**

**Step 4: Commit**
```bash
git add components/layout/mobile-nav.tsx
git commit -m "feat: add responsive mobile navigation"
```

---

#### Task 8.3: Netlify Deployment

**Files:**
- Create: `netlify.toml`

**Step 1: Create Netlify config**
```toml
[build]
  command = "npm run build"
  publish = ".next"

[[plugins]]
  package = "@netlify/plugin-nextjs"
```

**Step 2: Install Netlify adapter**
```bash
npm install -D @netlify/plugin-nextjs
```

**Step 3: Set environment variables in Netlify dashboard:**
- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`

**Step 4: Deploy**
```bash
netlify deploy --prod
```

**Step 5: Commit**
```bash
git add netlify.toml
git commit -m "chore: add Netlify deployment configuration"
```

---

#### Task 8.4: Performance Optimization

**Step 1: Enable Next.js Image Optimization**
- Use `next/image` for all images (avatars, post media, ads)
- Configure `remotePatterns` in `next.config.mjs` for Supabase Storage URLs

**Step 2: Implement ISR for public pages**
```typescript
// In explore page or public profile page
export const revalidate = 60; // Revalidate every 60 seconds
```

**Step 3: Add lazy loading for below-the-fold content**
```typescript
import dynamic from "next/dynamic";
const RightPanel = dynamic(() => import("@/components/layout/right-panel"), { ssr: false });
```

**Step 4: Bundle size check**
```bash
npx next build
npx @next/bundle-analyzer
```

**Step 5: Commit**
```bash
git commit -m "perf: add image optimization, ISR, and lazy loading"
```

---

## 6. Free Tier Optimization

### Supabase Free Tier Limits (as of 2025)
| Resource | Limit | Mitigation |
|----------|-------|------------|
| Database | 500 MB | Soft deletes instead of keeping history; periodic cleanup of expired posts |
| Storage | 1 GB | Compress images client-side before upload (max 500KB); limit 4 images per post |
| Auth | 50,000 MAU | More than sufficient for launch |
| Realtime | 200 concurrent connections | Limit realtime to notifications only; use polling for feed updates |
| Edge Functions | 500K invocations/month | Use sparingly; prefer client-side SDK calls |
| Bandwidth | 5 GB | Use CDN caching; serve optimized images |

### Netlify Free Tier Limits
| Resource | Limit | Mitigation |
|----------|-------|------------|
| Bandwidth | 100 GB/month | ISR/SSG for public pages; aggressive caching |
| Build minutes | 300/month | Avoid unnecessary deploys; use preview deploys sparingly |
| Serverless functions | 125K invocations/month | Minimize API routes; use Supabase SDK directly |

### Key Optimization Strategies

1. **Client-side image compression** before upload (use `browser-image-compression` library)
2. **Cursor-based pagination** (not offset) for efficient queries
3. **Counter caches** via triggers (avoid COUNT queries on large tables)
4. **ISR (Incremental Static Regeneration)** for explore page, trending tags
5. **Realtime subscriptions only for notifications** (not feed — use pull-to-refresh)
6. **Lazy load** RightPanel, media galleries, below-fold content
7. **Supabase connection pooling** via PgBouncer (enabled by default on free tier)
8. **Index all filter columns** (category, status, user_id, created_at)

---

## Phase Summary

| Phase | Description | Est. Tasks | Dependencies |
|-------|-------------|------------|--------------|
| **0** | Project Setup (Next.js, Supabase, Theme) | 4 | None |
| **1** | Authentication (OTP, OAuth, Session) | 3 | Phase 0 |
| **2** | Core Layout & Navigation | 1 | Phase 0 |
| **3** | Post System (CRUD, Feed, Comments, Likes) | 5 | Phase 1, 2 |
| **4** | User Profiles (View, Edit, Follow) | 2 | Phase 1, 2 |
| **5** | Search & Discovery | 2 | Phase 3 |
| **6** | Notifications (Realtime) | 1 | Phase 3 |
| **7** | Ad System (Basic) | 1 | Phase 3 |
| **8** | Polish & Deployment | 4 | All above |

---

> **Plan complete and saved to `IMPLEMENTATION-PLAN.md`.**
>
> **Two execution options:**
>
> **1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration
>
> **2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints
>
> **Which approach?**
