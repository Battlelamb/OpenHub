# Generic - Architecture & Implementation Roadmap

## System Architecture

```
                    ┌─────────────┐
                    │   Netlify   │
                    │  (CDN/Edge) │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  Next.js 14 │
                    │  App Router │
                    │  (SSR/SSG)  │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
       ┌──────▼──┐  ┌──────▼──┐  ┌─────▼────┐
       │Supabase │  │Supabase │  │Supabase  │
       │  Auth   │  │Database │  │ Storage  │
       │(OTP+OAuth)│ │(Postgres)│ │ (Media)  │
       └─────────┘  └─────────┘  └──────────┘
              │            │
       ┌──────▼──┐  ┌──────▼──┐
       │Supabase │  │  Edge   │
       │Realtime │  │Functions│
       └─────────┘  └─────────┘
```

## Project Structure

```
generic/
├── app/
│   ├── (auth)/
│   │   ├── login/page.tsx          # OTP + OAuth login
│   │   ├── signup/page.tsx         # Registration
│   │   └── callback/route.ts      # OAuth callback
│   ├── (main)/
│   │   ├── layout.tsx              # Main layout with sidebar
│   │   ├── page.tsx                # Feed / Timeline
│   │   ├── explore/page.tsx        # Discover & Search
│   │   ├── categories/
│   │   │   ├── [slug]/page.tsx     # Category feed
│   │   │   └── page.tsx            # All categories
│   │   ├── post/
│   │   │   ├── [id]/page.tsx       # Single post view
│   │   │   └── create/page.tsx     # Create post
│   │   ├── profile/
│   │   │   ├── [username]/page.tsx # Public profile
│   │   │   └── edit/page.tsx       # Edit profile
│   │   ├── messages/page.tsx       # DMs (future)
│   │   └── notifications/page.tsx  # Notifications
│   ├── admin/
│   │   ├── ads/page.tsx            # Ad management
│   │   └── moderation/page.tsx     # Content moderation
│   ├── api/
│   │   ├── posts/route.ts
│   │   ├── upload/route.ts
│   │   └── webhooks/route.ts
│   ├── layout.tsx                  # Root layout
│   └── globals.css                 # Global styles + Masonic theme
├── components/
│   ├── ui/                         # shadcn components
│   ├── post/
│   │   ├── PostCard.tsx            # Post display card
│   │   ├── PostForm.tsx            # Create/edit post
│   │   ├── PostFeed.tsx            # Masonry feed
│   │   └── PostFilters.tsx         # Category/location filters
│   ├── profile/
│   │   ├── ProfileCard.tsx
│   │   ├── ProfileHeader.tsx
│   │   └── TrustBadge.tsx
│   ├── layout/
│   │   ├── Sidebar.tsx
│   │   ├── TopBar.tsx
│   │   ├── MobileNav.tsx
│   │   └── MasonicPattern.tsx      # Background geometric patterns
│   ├── auth/
│   │   ├── OTPInput.tsx
│   │   ├── SocialLogin.tsx
│   │   └── AuthGuard.tsx
│   └── ads/
│       ├── AdBanner.tsx
│       └── SponsoredPost.tsx
├── lib/
│   ├── supabase/
│   │   ├── client.ts               # Browser client
│   │   ├── server.ts               # Server client
│   │   ├── middleware.ts            # Auth middleware
│   │   └── types.ts                # Generated types
│   ├── utils.ts
│   ├── constants.ts
│   └── hooks/
│       ├── useUser.ts
│       ├── usePosts.ts
│       ├── useRealtime.ts
│       └── useInfiniteScroll.ts
├── public/
│   ├── patterns/                    # Masonic SVG patterns
│   └── icons/
├── supabase/
│   ├── migrations/                  # SQL migrations
│   ├── seed.sql                     # Seed data
│   └── config.toml
├── tailwind.config.ts
├── next.config.js
├── netlify.toml
└── package.json
```

## Design System - Masonic Theme

### Color Palette
```css
:root {
  /* Primary - Deep Navy */
  --navy-50: #f0f3f9;
  --navy-100: #d9e0ef;
  --navy-500: #1e3a5f;
  --navy-700: #0f2744;
  --navy-900: #071829;

  /* Accent - Gold/Amber */
  --gold-50: #fff9eb;
  --gold-100: #fef0c7;
  --gold-400: #f6ad55;
  --gold-500: #d4941c;
  --gold-600: #b7791f;

  /* Neutral - Marble */
  --marble-50: #fafaf9;
  --marble-100: #f5f5f4;
  --marble-200: #e7e5e4;
  --marble-800: #292524;
  --marble-900: #1c1917;

  /* Semantic */
  --success: #10b981;
  --warning: #f59e0b;
  --error: #ef4444;
  --info: #3b82f6;
}
```

### Typography
- **Headings**: Playfair Display (serif, authoritative)
- **Body**: Inter (sans-serif, clean)
- **Mono**: JetBrains Mono (code/numbers)

### Components Style
- Cards with subtle gold borders
- Geometric corner accents (masonic symbols)
- Grid-based masonry layout for feeds
- Glassmorphism on overlays
- Subtle shadow hierarchy

## Implementation Phases

### Phase 1 - Foundation (Week 1-2)
- [ ] Next.js project setup + Tailwind + shadcn
- [ ] Supabase project setup
- [ ] Auth system (OTP + Google + Apple)
- [ ] Database schema + migrations
- [ ] Basic layout + Masonic theme
- [ ] User registration & profiles

### Phase 2 - Core Features (Week 3-4)
- [ ] Post creation (all categories)
- [ ] Feed with masonry layout
- [ ] Category filtering
- [ ] Search & discovery
- [ ] Image upload + optimization
- [ ] Post expiration system

### Phase 3 - Social Features (Week 5-6)
- [ ] Like / save / share
- [ ] Comments
- [ ] Follow system
- [ ] Notifications (realtime)
- [ ] User trust/reputation

### Phase 4 - Monetization (Week 7-8)
- [ ] Ad system
- [ ] Sponsored posts
- [ ] Premium features
- [ ] Analytics dashboard

### Phase 5 - Polish (Week 9-10)
- [ ] Performance optimization
- [ ] SEO
- [ ] PWA support
- [ ] Mobile responsive
- [ ] A11y compliance
- [ ] Netlify deployment + CI/CD
