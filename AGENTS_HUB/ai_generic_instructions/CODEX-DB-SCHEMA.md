# Generic: Complete Database Schema and Backend Architecture

## 1. Goals
Generic is a Twitter-like social platform with:
- a public feed
- replies, reposts, quotes, likes, bookmarks, follows
- category-based posts for:
  - real estate
  - cars
  - rentals
  - services
  - looking-for-connections
- detailed user profiles
- OTP + OAuth authentication
- paid/sponsored ad delivery
- time-limited posts
- Supabase as the backend on the free tier

This design aims to:
- keep the client simple
- use Supabase Auth + Postgres + Storage directly
- enforce access through Row Level Security
- support both social posts and listing-style posts
- avoid expensive patterns that do not fit the free tier

## 2. Architectural Principles
1. Keep identity in `auth.users`; keep application data in `public`.
2. Use normalized tables for high-value data; use `jsonb` only for optional payloads.
3. Use a single central `posts` table plus category-specific detail tables.
4. Treat expiration as a first-class field in the schema.
5. Use soft-delete and status fields for moderation instead of hard deletes.
6. Push most CRUD directly from the client to Supabase under RLS.
7. Use SQL functions for feed queries and Edge Functions only for trusted workflows.
8. Keep analytics aggregated to fit storage and performance limits.

## 3. Schemas
- `auth`
  - Supabase-managed identity schema
- `public`
  - all application tables exposed via PostgREST/Supabase API under RLS
- `private`
  - internal operational tables not exposed to client access

## 4. Extensions
Enable:

```sql
create extension if not exists pgcrypto;
create extension if not exists citext;
create extension if not exists pg_trgm;
create extension if not exists btree_gin;
create extension if not exists pg_cron;
```

## 5. Shared Conventions
- Primary keys: `uuid`
- Timestamps: `created_at timestamptz not null default now()`
- Mutable tables also get `updated_at timestamptz not null default now()`
- Use `on delete cascade` for child rows that should disappear with their parent
- Use `status` instead of hard delete for moderation-sensitive content
- Use `citext` for usernames and case-insensitive unique text fields

## 6. Enum Types

```sql
create type public.user_visibility as enum (
  'public',
  'private'
);

create type public.account_status as enum (
  'active',
  'suspended',
  'deactivated'
);

create type public.verification_status as enum (
  'none',
  'pending',
  'verified',
  'rejected'
);

create type public.role_name as enum (
  'user',
  'moderator',
  'admin'
);

create type public.follow_status as enum (
  'requested',
  'accepted'
);

create type public.post_category as enum (
  'real_estate',
  'cars',
  'rentals',
  'services',
  'looking_for_connections'
);

create type public.post_kind as enum (
  'post',
  'reply',
  'repost',
  'quote'
);

create type public.post_visibility as enum (
  'public',
  'followers_only'
);

create type public.post_status as enum (
  'draft',
  'published',
  'expired',
  'hidden',
  'deleted',
  'rejected'
);

create type public.media_type as enum (
  'image',
  'video'
);

create type public.report_reason as enum (
  'spam',
  'scam',
  'harassment',
  'nudity',
  'violence',
  'misinformation',
  'illegal_goods',
  'impersonation',
  'other'
);

create type public.report_status as enum (
  'open',
  'reviewing',
  'resolved',
  'dismissed'
);

create type public.moderation_action as enum (
  'warn_user',
  'hide_post',
  'reject_post',
  'delete_post',
  'suspend_user',
  'restore_post'
);

create type public.ad_account_status as enum (
  'active',
  'paused',
  'suspended'
);

create type public.ad_objective as enum (
  'traffic',
  'messages',
  'profile_visits',
  'promoted_post'
);

create type public.ad_entity_status as enum (
  'draft',
  'active',
  'paused',
  'completed',
  'rejected'
);
```

## 7. Identity and User Schema

### 7.1 `auth.users`
Supabase Auth owns this table. Do not duplicate core authentication fields in `public`.

Use it for:
- email OTP/passwordless login
- OAuth providers such as Google and Apple
- session lifecycle
- JWT issuance

### 7.2 `public.profiles`
One row per application user.

```sql
create table public.profiles (
  user_id uuid primary key references auth.users(id) on delete cascade,
  username citext not null unique,
  display_name text not null,
  bio text,
  avatar_path text,
  banner_path text,
  city text,
  region text,
  country_code char(2),
  visibility public.user_visibility not null default 'public',
  is_business boolean not null default false,
  verification_status public.verification_status not null default 'none',
  status public.account_status not null default 'active',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
```

Purpose:
- public-facing profile identity
- display and discovery metadata
- moderation and visibility state

Indexes:
- unique on `username`
- trigram index on `username`
- trigram index on `display_name`
- btree index on `(status, visibility)`

### 7.3 `public.profile_details`
Optional extended profile information, separated from the hot path.

```sql
create table public.profile_details (
  user_id uuid primary key references public.profiles(user_id) on delete cascade,
  occupation text,
  company text,
  website_url text,
  about_long text,
  languages text[] not null default '{}',
  interests text[] not null default '{}',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
```

### 7.4 `public.account_settings`
Private per-user behavior and notification settings.

```sql
create table public.account_settings (
  user_id uuid primary key references public.profiles(user_id) on delete cascade,
  default_post_ttl_hours integer,
  allow_dm boolean not null default true,
  discoverable boolean not null default true,
  email_notifications boolean not null default true,
  push_notifications boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
```

### 7.5 `public.profile_stats`
Cached counters to avoid expensive aggregate queries in the app.

```sql
create table public.profile_stats (
  user_id uuid primary key references public.profiles(user_id) on delete cascade,
  follower_count integer not null default 0,
  following_count integer not null default 0,
  post_count integer not null default 0,
  active_listing_count integer not null default 0,
  updated_at timestamptz not null default now()
);
```

### 7.6 `public.user_roles`
Simple RBAC table for admin and moderator capabilities.

```sql
create table public.user_roles (
  user_id uuid not null references public.profiles(user_id) on delete cascade,
  role public.role_name not null,
  created_at timestamptz not null default now(),
  primary key (user_id, role)
);
```

Rules:
- every user gets `user`
- moderators and admins are assigned manually
- optionally mirror roles into JWT claims using a Supabase Auth hook

## 8. Social Graph Schema

### 8.1 `public.follows`

```sql
create table public.follows (
  follower_id uuid not null references public.profiles(user_id) on delete cascade,
  following_id uuid not null references public.profiles(user_id) on delete cascade,
  status public.follow_status not null,
  created_at timestamptz not null default now(),
  primary key (follower_id, following_id),
  check (follower_id <> following_id)
);
```

Behavior:
- public accounts can auto-accept follows
- private accounts create `requested` rows
- accepted follow rows drive follower-only profile/post access

Indexes:
- `(following_id, status, created_at desc)`
- `(follower_id, status, created_at desc)`

### 8.2 `public.blocks`

```sql
create table public.blocks (
  blocker_id uuid not null references public.profiles(user_id) on delete cascade,
  blocked_id uuid not null references public.profiles(user_id) on delete cascade,
  created_at timestamptz not null default now(),
  primary key (blocker_id, blocked_id),
  check (blocker_id <> blocked_id)
);
```

Blocking effects:
- blocked users cannot view each other’s profiles or posts
- blocked users cannot follow, message, or engage
- feed queries exclude blocked relationships in both directions

## 9. Content Schema

### 9.1 `public.posts`
This is the core content table. It supports standard posts, replies, reposts, quotes, and listing-style category posts.

```sql
create table public.posts (
  id uuid primary key default gen_random_uuid(),
  author_id uuid not null references public.profiles(user_id) on delete cascade,
  category public.post_category,
  kind public.post_kind not null default 'post',
  parent_post_id uuid references public.posts(id) on delete cascade,
  root_post_id uuid references public.posts(id) on delete cascade,
  quoted_post_id uuid references public.posts(id) on delete set null,
  reposted_post_id uuid references public.posts(id) on delete cascade,
  title text,
  body text not null,
  visibility public.post_visibility not null default 'public',
  status public.post_status not null default 'draft',
  allow_comments boolean not null default true,
  city text,
  region text,
  country_code char(2),
  expires_at timestamptz,
  published_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (
    (kind <> 'reply' or parent_post_id is not null) and
    (kind <> 'repost' or reposted_post_id is not null) and
    (kind <> 'quote' or quoted_post_id is not null)
  ),
  check (expires_at is null or expires_at > created_at)
);
```

Column intent:
- `category`
  - only set for category/listing posts
- `kind`
  - determines reply/repost/quote behavior
- `parent_post_id`
  - direct parent for replies
- `root_post_id`
  - thread root for quick thread loading
- `visibility`
  - supports public and follower-only content
- `status`
  - controls lifecycle and moderation visibility
- `expires_at`
  - used for time-limited posts and listing expiry

Indexes:
- `(author_id, created_at desc)`
- `(status, visibility, created_at desc)`
- `(category, created_at desc)`
- `(root_post_id, created_at asc)`
- `(parent_post_id, created_at asc)`
- partial index on `(expires_at)` where `status = 'published' and expires_at is not null`
- trigram GIN on `title`
- trigram GIN on `body`

### 9.2 `public.post_listing`
Shared commercial/listing fields across all category posts.

```sql
create table public.post_listing (
  post_id uuid primary key references public.posts(id) on delete cascade,
  price_amount numeric(12,2),
  currency_code char(3),
  price_unit text,
  is_negotiable boolean not null default false,
  condition text,
  contact_email text,
  contact_phone text,
  contact_url text,
  availability_start date,
  availability_end date,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
```

Use this for:
- listing price metadata
- contact methods
- common structured fields shared by real estate, cars, rentals, and services

### 9.3 Category Detail Tables
Exactly one detail table should exist for a given category post.

#### `public.real_estate_details`

```sql
create table public.real_estate_details (
  post_id uuid primary key references public.posts(id) on delete cascade,
  property_type text,
  listing_intent text,
  bedrooms numeric(4,1),
  bathrooms numeric(4,1),
  area_value numeric(12,2),
  area_unit text,
  lot_size_value numeric(12,2),
  furnished boolean,
  parking_spaces integer
);
```

#### `public.car_details`

```sql
create table public.car_details (
  post_id uuid primary key references public.posts(id) on delete cascade,
  make text,
  model text,
  year integer,
  mileage integer,
  fuel_type text,
  transmission text,
  body_style text,
  condition text
);
```

#### `public.rental_details`

```sql
create table public.rental_details (
  post_id uuid primary key references public.posts(id) on delete cascade,
  rental_type text,
  deposit_amount numeric(12,2),
  rental_period_unit text,
  min_rental_period integer,
  max_rental_period integer,
  pickup_required boolean
);
```

#### `public.service_details`

```sql
create table public.service_details (
  post_id uuid primary key references public.posts(id) on delete cascade,
  service_type text,
  delivery_mode text,
  rate_min numeric(12,2),
  rate_max numeric(12,2),
  rate_unit text,
  availability_text text
);
```

#### `public.connection_details`

```sql
create table public.connection_details (
  post_id uuid primary key references public.posts(id) on delete cascade,
  connection_type text,
  age_min integer,
  age_max integer,
  meetup_mode text,
  intent_summary text
);
```

Validation rule:
- if `posts.category = 'cars'`, there must be a row in `car_details` and no row in any other detail table
- apply the same rule to every category
- enforce via a deferred trigger function to keep client writes manageable

### 9.4 `public.post_media`

```sql
create table public.post_media (
  id uuid primary key default gen_random_uuid(),
  post_id uuid not null references public.posts(id) on delete cascade,
  bucket_id text not null,
  storage_path text not null,
  media_type public.media_type not null,
  sort_order integer not null default 0,
  width integer,
  height integer,
  duration_ms integer,
  blurhash text,
  created_at timestamptz not null default now()
);
```

Indexes:
- `(post_id, sort_order)`

### 9.5 `public.post_stats`
Cached per-post engagement counts.

```sql
create table public.post_stats (
  post_id uuid primary key references public.posts(id) on delete cascade,
  like_count integer not null default 0,
  reply_count integer not null default 0,
  repost_count integer not null default 0,
  quote_count integer not null default 0,
  bookmark_count integer not null default 0,
  last_engagement_at timestamptz,
  updated_at timestamptz not null default now()
);
```

### 9.6 `public.post_daily_stats`
Daily rollups only. Avoid per-view permanent rows on the free tier.

```sql
create table public.post_daily_stats (
  post_id uuid not null references public.posts(id) on delete cascade,
  stat_date date not null,
  impressions integer not null default 0,
  detail_views integer not null default 0,
  contact_clicks integer not null default 0,
  saves integer not null default 0,
  primary key (post_id, stat_date)
);
```

### 9.7 `public.post_likes`

```sql
create table public.post_likes (
  user_id uuid not null references public.profiles(user_id) on delete cascade,
  post_id uuid not null references public.posts(id) on delete cascade,
  created_at timestamptz not null default now(),
  primary key (user_id, post_id)
);
```

### 9.8 `public.bookmarks`

```sql
create table public.bookmarks (
  user_id uuid not null references public.profiles(user_id) on delete cascade,
  post_id uuid not null references public.posts(id) on delete cascade,
  created_at timestamptz not null default now(),
  primary key (user_id, post_id)
);
```

### 9.9 `public.notifications`
Generic recipient inbox for app notifications.

```sql
create table public.notifications (
  id uuid primary key default gen_random_uuid(),
  recipient_id uuid not null references public.profiles(user_id) on delete cascade,
  actor_id uuid references public.profiles(user_id) on delete set null,
  type text not null,
  entity_type text not null,
  entity_id uuid,
  payload jsonb not null default '{}'::jsonb,
  read_at timestamptz,
  created_at timestamptz not null default now()
);
```

Indexes:
- `(recipient_id, created_at desc)`
- `(recipient_id, read_at)`

## 10. Moderation and Trust & Safety Schema

### 10.1 `public.post_reports`

```sql
create table public.post_reports (
  id uuid primary key default gen_random_uuid(),
  reporter_id uuid not null references public.profiles(user_id) on delete cascade,
  post_id uuid references public.posts(id) on delete cascade,
  reported_user_id uuid references public.profiles(user_id) on delete cascade,
  reason public.report_reason not null,
  details text,
  status public.report_status not null default 'open',
  created_at timestamptz not null default now(),
  resolved_at timestamptz,
  check (
    (post_id is not null and reported_user_id is null) or
    (post_id is null and reported_user_id is not null)
  )
);
```

### 10.2 `public.moderation_actions`

```sql
create table public.moderation_actions (
  id uuid primary key default gen_random_uuid(),
  report_id uuid references public.post_reports(id) on delete set null,
  target_type text not null,
  target_id uuid not null,
  action public.moderation_action not null,
  notes text,
  actor_id uuid not null references public.profiles(user_id) on delete restrict,
  created_at timestamptz not null default now()
);
```

Use this for:
- auditable moderator decisions
- reversible actions
- later dashboards and internal reporting

## 11. Ads Schema

### 11.1 `public.ad_accounts`

```sql
create table public.ad_accounts (
  id uuid primary key default gen_random_uuid(),
  owner_user_id uuid not null references public.profiles(user_id) on delete cascade,
  name text not null,
  billing_email text,
  status public.ad_account_status not null default 'active',
  spend_limit numeric(12,2),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
```

### 11.2 `public.ad_campaigns`

```sql
create table public.ad_campaigns (
  id uuid primary key default gen_random_uuid(),
  ad_account_id uuid not null references public.ad_accounts(id) on delete cascade,
  name text not null,
  objective public.ad_objective not null,
  status public.ad_entity_status not null default 'draft',
  budget_total numeric(12,2),
  budget_daily numeric(12,2),
  start_at timestamptz,
  end_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
```

### 11.3 `public.ad_sets`

```sql
create table public.ad_sets (
  id uuid primary key default gen_random_uuid(),
  campaign_id uuid not null references public.ad_campaigns(id) on delete cascade,
  name text not null,
  status public.ad_entity_status not null default 'draft',
  bid_type text,
  bid_amount numeric(12,2),
  target_categories public.post_category[] not null default '{}',
  target_countries text[] not null default '{}',
  target_regions text[] not null default '{}',
  target_min_age integer,
  target_max_age integer,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
```

### 11.4 `public.ad_creatives`

```sql
create table public.ad_creatives (
  id uuid primary key default gen_random_uuid(),
  ad_set_id uuid not null references public.ad_sets(id) on delete cascade,
  promoted_post_id uuid references public.posts(id) on delete set null,
  headline text,
  body text,
  cta_label text,
  destination_url text,
  media_path text,
  status public.ad_entity_status not null default 'draft',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
```

### 11.5 `public.ad_daily_stats`

```sql
create table public.ad_daily_stats (
  ad_creative_id uuid not null references public.ad_creatives(id) on delete cascade,
  stat_date date not null,
  impressions integer not null default 0,
  clicks integer not null default 0,
  spent_amount numeric(12,2) not null default 0,
  primary key (ad_creative_id, stat_date)
);
```

## 12. Private/Internal Tables

### 12.1 `private.ad_click_events`
Raw click-level tracking for fraud review and debugging. Keep retention short.

```sql
create table private.ad_click_events (
  id uuid primary key default gen_random_uuid(),
  ad_creative_id uuid not null,
  viewer_user_id uuid,
  session_id text,
  ip_hash text,
  user_agent_hash text,
  created_at timestamptz not null default now()
);
```

### 12.2 `private.audit_log`
Internal privileged audit trail.

```sql
create table private.audit_log (
  id uuid primary key default gen_random_uuid(),
  actor_user_id uuid,
  action text not null,
  target_type text,
  target_id uuid,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
```

Do not expose the `private` schema via the Supabase API.
