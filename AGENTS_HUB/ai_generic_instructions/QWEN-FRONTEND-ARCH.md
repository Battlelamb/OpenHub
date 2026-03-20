# I'Masonic Social Platform - Complete Frontend Architecture

**Tech Stack:** Next.js 14 App Router + shadcn/ui + Tailwind CSS + Zustand + React Query  
**Deployment:** Netlify Free Tier  
**Theme:** Masonic aesthetic with geometric patterns, deep navy + gold/amber + marble white

---

## 🎨 Design System

### Color Palette

#### Deep Navy (Primary Brand Color)
```
navy-50:  #f0f4f8
navy-100: #d9e2ec
navy-200: #bcccdc
navy-300: #9fb3c8
navy-400: #8299b3
navy-500: #668099
navy-600: #4d667a
navy-700: #334d5c
navy-800: #1a2332  ← Primary navy
navy-900: #0f172a  ← Deep background
navy-950: #020617  ← Darkest
```

#### Gold/Amber (Accent & CTAs)
```
gold-50:  #fffbeb
gold-100: #fef3c7
gold-200: #fde68a
gold-300: #fcd34d
gold-400: #fbbf24
gold-500: #d4a843  ← Primary gold
gold-600: #b48811  ← Hover state
gold-700: #946909
gold-800: #75530b
gold-900: #614714
```

#### Marble White (Content Surfaces)
```
marble-50:  #fafafa  ← Light mode cards
marble-100: #f5f5f5
marble-200: #e5e5e5
marble-300: #d4d4d4
marble-400: #a3a3a3
marble-500: #737373
marble-600: #525252
marble-700: #404040
marble-800: #262626
marble-900: #171717
```

#### Semantic Colors
```
success: #10b981  (Emerald)
error:   #dc2626  (Ruby)
warning: #f59e0b
info:    #3b82f6
```

---

### Typography

#### Headings - Elegant Serif
- **Font:** Playfair Display
- **Weights:** 400 (regular), 500 (medium), 600 (semibold), 700 (bold)
- **Sizes:**
  - xs: 0.75rem (12px)
  - sm: 0.875rem (14px)
  - base: 1rem (16px)
  - lg: 1.125rem (18px)
  - xl: 1.25rem (20px)
  - 2xl: 1.5rem (24px)
  - 3xl: 1.875rem (30px)
  - 4xl: 2.25rem (36px)

#### Body - Clean Sans-Serif
- **Font:** Inter
- **Weights:** 400 (regular), 500 (medium), 600 (semibold), 700 (bold)

#### Monospace - Code & Metadata
- **Font:** JetBrains Mono

---

### Visual Elements

#### Borders
```typescript
subtle:  '1px solid rgba(212, 168, 67, 0.2)'
default: '1px solid rgba(212, 168, 67, 0.4)'
accent:  '2px solid #d4a843'
thick:   '3px solid #d4a843'
```

#### Shadows
```typescript
gold:   '0 4px 14px rgba(212, 168, 67, 0.3)'
navy:   '0 4px 14px rgba(15, 23, 42, 0.4)'
subtle: '0 1px 3px rgba(0, 0, 0, 0.1)'
card:   '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
glow:   '0 0 20px rgba(212, 168, 67, 0.5)'
```

#### Background Patterns
```
geometric: /patterns/compass-square.svg
marble:    /textures/marble-light.png
grid:      /patterns/golden-grid.svg
```

#### Border Radius
```
sm:    0.25rem
default: 0.5rem
md:    0.75rem
lg:    1rem
xl:    1.5rem
full:  9999px
```

#### Spacing (Golden Ratio Inspired)
```
xs:   0.5rem   (8px)
sm:   0.75rem  (12px)
base: 1rem     (16px)
md:   1.5rem   (24px)
lg:   2rem     (32px)
xl:   3rem     (48px)
2xl:  4rem     (64px)
```

---

## 📁 Complete Folder Structure

```
src/
├── app/                          # Next.js App Router
│   ├── (auth)/                   # Auth route group (no sidebar)
│   │   ├── login/
│   │   │   └── page.tsx
│   │   ├── register/
│   │   │   └── page.tsx
│   │   ├── reset-password/
│   │   │   └── page.tsx
│   │   ├── verify-email/
│   │   │   └── page.tsx
│   │   └── layout.tsx            # Centered auth layout
│   │
│   ├── (main)/                   # Main app (requires auth)
│   │   ├── layout.tsx            # Sidebar + content layout
│   │   ├── page.tsx              # Home feed
│   │   ├── explore/
│   │   │   └── page.tsx
│   │   ├── notifications/
│   │   │   └── page.tsx
│   │   ├── messages/
│   │   │   └── page.tsx
│   │   ├── bookmarks/
│   │   │   └── page.tsx
│   │   ├── search/
│   │   │   └── page.tsx
│   │   ├── compose/
│   │   │   └── page.tsx          # Compose modal route
│   │   ├── profile/
│   │   │   ├── [username]/
│   │   │   │   ├── page.tsx
│   │   │   │   ├── [postId]/
│   │   │   │   │   └── page.tsx
│   │   │   │   ├── followers/
│   │   │   │   │   └── page.tsx
│   │   │   │   └── following/
│   │   │   │       └── page.tsx
│   │   │   └── edit/
│   │   │       └── page.tsx
│   │   └── settings/
│   │       ├── account/
│   │       │   └── page.tsx
│   │       ├── profile/
│   │       │   └── page.tsx
│   │       ├── security/
│   │       │   └── page.tsx
│   │       ├── privacy/
│   │       │   └── page.tsx
│   │       └── appearance/
│   │           └── page.tsx
│   │
│   ├── (marketing)/              # Marketing pages
│   │   ├── about/
│   │   │   └── page.tsx
│   │   ├── privacy/
│   │   │   └── page.tsx
│   │   ├── terms/
│   │   │   └── page.tsx
│   │   └── layout.tsx
│   │
│   ├── api/                      # API Routes
│   │   ├── auth/
│   │   │   ├── [...nextauth]/
│   │   │   │   └── route.ts
│   │   │   ├── register/
│   │   │   │   └── route.ts
│   │   │   └── logout/
│   │   │       └── route.ts
│   │   ├── posts/
│   │   │   ├── route.ts          # GET (feed), POST (create)
│   │   │   ├── [id]/
│   │   │   │   └── route.ts      # GET, DELETE
│   │   │   └── [id]/
│   │   │       ├── like/
│   │   │       │   └── route.ts
│   │   │       ├── repost/
│   │   │       │   └── route.ts
│   │   │       └── bookmark/
│   │   │           └── route.ts
│   │   ├── users/
│   │   │   ├── [username]/
│   │   │   │   └── route.ts
│   │   │   ├── search/
│   │   │   │   └── route.ts
│   │   │   └── suggestions/
│   │   │       └── route.ts
│   │   ├── uploads/
│   │   │   └── route.ts
│   │   └── webhooks/
│   │       └── stripe/
│   │           └── route.ts
│   │
│   ├── globals.css
│   ├── layout.tsx                # Root layout
│   ├── providers.tsx             # Context providers (React Query, Theme)
│   └── robots.ts
│
├── components/
│   ├── ui/                       # shadcn/ui components
│   │   ├── accordion.tsx
│   │   ├── alert-dialog.tsx
│   │   ├── alert.tsx
│   │   ├── avatar.tsx
│   │   ├── badge.tsx
│   │   ├── button.tsx
│   │   ├── card.tsx
│   │   ├── dialog.tsx
│   │   ├── dropdown-menu.tsx
│   │   ├── form.tsx
│   │   ├── input.tsx
│   │   ├── label.tsx
│   │   ├── scroll-area.tsx
│   │   ├── separator.tsx
│   │   ├── skeleton.tsx
│   │   ├── switch.tsx
│   │   ├── tabs.tsx
│   │   ├── textarea.tsx
│   │   ├── toast.tsx
│   │   ├── toaster.tsx
│   │   └── tooltip.tsx
│   │
│   ├── layout/                   # Layout components
│   │   ├── app-sidebar.tsx       # Left sidebar (logo, nav, user)
│   │   ├── mobile-nav.tsx        # Bottom nav for mobile
│   │   ├── right-sidebar.tsx     # Trending, suggestions (desktop)
│   │   ├── header.tsx            # Page header with breadcrumbs
│   │   └── nav-item.tsx          # Sidebar navigation item
│   │
│   ├── feed/                     # Feed components
│   │   ├── feed.tsx              # Main feed container (infinite scroll)
│   │   ├── feed-tabs.tsx         # For You / Following tabs
│   │   ├── post-card.tsx         # Individual post card
│   │   ├── post-actions.tsx      # Reply, repost, like, share, bookmark
│   │   ├── post-media.tsx        # Images/video carousel
│   │   ├── post-header.tsx       # Author info, timestamp, menu
│   │   ├── post-body.tsx         # Content, mentions, hashtags
│   │   ├── reply-thread.tsx      # Nested replies
│   │   ├── repost-card.tsx       # Repost indicator
│   │   └── feed-skeleton.tsx     # Loading skeleton
│   │
│   ├── compose/                  # Compose components
│   │   ├── compose-box.tsx       # Main compose textarea
│   │   ├── compose-modal.tsx     # Full compose modal
│   │   ├── compose-actions.tsx   # Media, emoji, poll, schedule
│   │   ├── media-uploader.tsx    # Image/video upload
│   │   ├── media-preview.tsx     # Upload preview with remove
│   │   └── poll-creator.tsx      # Poll creation UI
│   │
│   ├── profile/                  # Profile components
│   │   ├── profile-header.tsx    # Banner, avatar, stats, bio
│   │   ├── profile-tabs.tsx      # Posts, replies, media, likes
│   │   ├── profile-stats.tsx     # Following/followers count
│   │   ├── profile-bio.tsx       # Bio, location, website, join date
│   │   ├── follow-button.tsx     # Follow/unfollow states
│   │   ├── edit-profile-modal.tsx
│   │   └── profile-skeleton.tsx
│   │
│   ├── search/                   # Search components
│   │   ├── search-input.tsx      # Main search bar
│   │   ├── search-results.tsx    # Search results page
│   │   ├── search-suggestions.tsx# Autocomplete dropdown
│   │   └── search-filters.tsx    # Type filters (posts, users, media)
│   │
│   ├── notifications/            # Notification components
│   │   ├── notification-list.tsx
│   │   ├── notification-item.tsx
│   │   └── notification-tabs.tsx
│   │
│   ├── messages/                 # DM components
│   │   ├── message-list.tsx
│   │   ├── message-input.tsx
│   │   └── conversation-card.tsx
│   │
│   └── shared/                   # Shared components
│       ├── avatar.tsx            # Avatar with online indicator
│       ├── verified-badge.tsx    # Gold checkmark badge
│       ├── trend-card.tsx        # Trending topics card
│       ├── who-to-follow.tsx     # User suggestions card
│       ├── loading-spinner.tsx   # Gold animated spinner
│       ├── error-boundary.tsx
│       ├── theme-toggle.tsx      # Dark/light mode toggle
│       └── masonic-logo.tsx      # Masonic logo component
│
├── lib/
│   ├── db.ts                     # Database client (Prisma/Drizzle)
│   ├── auth.ts                   # Auth utilities (NextAuth)
│   ├── uploads.ts                # File upload (Uploadthing)
│   ├── utils.ts                  # General utilities (cn, formatters)
│   ├── constants.ts              # App constants
│   └── validations.ts            # Zod schemas
│
├── hooks/                        # Custom React hooks
│   ├── use-posts.ts              # Post-related hooks
│   ├── use-users.ts              # User-related hooks
│   ├── use-search.ts             # Search hooks
│   ├── use-notifications.ts
│   ├── use-messages.ts
│   ├── use-follow.ts             # Follow/unfollow
│   ├── use-like.ts               # Like/unlike
│   ├── use-bookmark.ts
│   ├── use-media-upload.ts
│   ├── use-debounce.ts
│   └── use-intersection-observer.ts
│
├── stores/                       # Zustand stores
│   ├── use-post-store.ts         # Posts, likes, bookmarks
│   ├── use-user-store.ts         # Current user, following
│   ├── use-ui-store.ts           # UI state (modals, theme)
│   └── use-compose-store.ts      # Compose draft state
│
├── types/                        # TypeScript types
│   ├── post.ts
│   ├── user.ts
│   ├── notification.ts
│   ├── message.ts
│   └── index.ts
│
├── config/                       # App configuration
│   ├── site.ts                   # Site metadata
│   ├── navigation.ts             # Nav items & links
│   └── socials.ts                # Social media links
│
└── public/
    ├── patterns/
    │   ├── compass-square.svg
    │   ├── golden-grid.svg
    │   └── geometric-border.svg
    ├── textures/
    │   ├── marble-light.png
    │   └── marble-dark.png
    ├── images/
    │   ├── logo.svg
    │   ├── logo-mark.svg
    │   └── og-image.png
    └── fonts/                    # Self-hosted fonts (optional)
```

---

## 🧩 Key Components Details

### Layout Components

#### AppSidebar (`app-sidebar.tsx`)
- **Position:** Fixed left sidebar (desktop)
- **Contents:**
  - Masonic logo (top)
  - Navigation: Home, Explore, Notifications, Messages, Bookmarks
  - Gold CTA Compose button
  - User profile card (bottom)
  - Theme toggle
- **Responsive:** Hidden on mobile, visible ≥768px

#### MobileNav (`mobile-nav.tsx`)
- **Position:** Fixed bottom (mobile only)
- **Contents:** 5 items (Home, Search, Compose, Notifications, Messages)
- **Active State:** Gold indicator bar
- **iOS:** Safe area insets support

#### RightSidebar (`right-sidebar.tsx`)
- **Position:** Fixed right sidebar (desktop only)
- **Contents:**
  - Search bar
  - Trending topics card ( Masonic geometric pattern background)
  - Who to follow suggestions
  - Footer links (privacy, terms)
- **Sticky:** Maintains position on scroll

---

### Feed Components

#### Feed (`feed.tsx`)
```typescript
Props: { type: 'for-you' | 'following' | 'tag' }
Features:
  - Infinite scroll (React Query useInfiniteQuery)
  - Pull to refresh (mobile)
  - Tab switching (For You / Following)
  - Empty state with CTA
  - Error state with retry button
  - Optimistic updates for likes/reposts
```

#### PostCard (`post-card.tsx`)
```typescript
Structure:
  1. PostHeader
     - Avatar (with gold border if verified)
     - Display name + verified badge
     - Username (@handle)
     - Timestamp
     - Menu dropdown
  2. PostBody
     - Text content (with mentions/hashtags linked)
     - Link previews
  3. PostMedia
     - Single image (full width)
     - Multiple images (masonry grid 2x2)
     - Video player (custom controls with gold accents)
     - GIF player
  4. PostActions
     - Reply (blue)
     - Repost (green)
     - Like (gold fill on active)
     - Bookmark (gold outline on active)
     - Share (copy link, native share)
  5. PostStats
     - Reply count, repost count, like count, view count
  6. Hover Effect
     - Gold border glow animation
```

#### PostActions (`post-actions.tsx`)
```typescript
Actions:
  - Reply: Opens compose modal with reply context
  - Repost: Toggle with confirmation modal
  - Like: Heart animation, gold fill on active
  - Bookmark: Toggle with folder selection
  - Share: Copy link, share native dialog
```

---

### Compose Components

#### ComposeBox (`compose-box.tsx`)
```typescript
Features:
  - Character counter (warning at 260 chars, red at 280)
  - Mention autocomplete (@username with avatar)
  - Hashtag autocomplete (#topic with post count)
  - Emoji picker (custom Masonic-themed categories)
  - Media upload (4 images max, 1 video, or GIF)
  - Poll creator (2-4 options, duration 5min-7days)
  - Schedule post (calendar + time picker)
  - Draft autosave (localStorage, 7-day retention)
  - Reply to context display (collapsible)
  - Gold progress ring for character limit
```

---

### Profile Components

#### ProfileHeader (`profile-header.tsx`)
```typescript
Elements:
  - Banner image (editable, 1500x500px recommended)
  - Avatar (400x400px, gold border if verified)
  - Name with verified badge (gold checkmark)
  - Username (@handle) & join date
  - Bio with link (auto-linkify URLs)
  - Location & website
  - Following/followers stats (clickable)
  - Edit Profile button (own profile)
  - Follow/Following/Requested button (others)
  - Masonic geometric pattern overlay (subtle)
```

---

## 🛣️ Pages & Routing

### Route Groups

| Group | Layout | Purpose | Protected |
|-------|--------|---------|-----------|
| `(auth)` | Centered, no sidebar | Login, register, reset | No |
| `(main)` | Sidebar + content | Main app | Yes |
| `(marketing)` | Clean marketing | About, privacy, terms | No |

### Route Protection (middleware.ts)
```typescript
export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl
  const session = getSession(request)
  
  // Redirect to login if accessing protected routes
  if (pathname.startsWith('/home') && !session) {
    return NextResponse.redirect(new URL('/login', request.url))
  }
  
  // Redirect to home if accessing auth routes while logged in
  if (pathname.startsWith('/login') && session) {
    return NextResponse.redirect(new URL('/home', request.url))
  }
}

export const config = {
  matcher: ['/home/:path*', '/profile/:path*', '/login', '/register'],
}
```

### Key Pages

#### Home Feed (`/home`)
```typescript
// Server Component (initial data fetch)
- Fetch initial 20 posts
- Pass to client Feed component
- Tabs: For You (algorithmic) / Following (chronological)
- Infinite scroll with cursor pagination
- ISR: revalidate = 60 seconds
```

#### Profile (`/profile/[username]`)
```typescript
// Mixed Server/Client
Server:
  - Fetch user profile data
  - Generate metadata (SEO: title, description, OG image)
  - ISR: revalidate = 60 seconds

Client:
  - Profile tabs (Posts, Replies, Media, Likes)
  - Follow/unfollow functionality
  - Edit profile modal
  - Infinite scroll for posts
  - Block/unblock user
```

#### Search (`/search?q=query&type=posts`)
```typescript
// Client Component
- Debounced search input (300ms)
- Real-time suggestions dropdown
- Filter by type: posts, users, media, likes
- Recent searches (localStorage)
- Trending searches
- Search history with clear option
```

---

## 🗄️ State Management

### Client State (Zustand)

#### use-post-store.ts
```typescript
interface PostState {
  // Data
  posts: Map<string, Post>           // All cached posts
  likes: Map<string, boolean>         // Liked post IDs
  bookmarks: Set<string>              // Bookmarked post IDs
  
  // Compose
  composeDraft: string
  replyTo: Post | null
  
  // Actions
  addPost: (post: Post) => void
  updatePost: (id: string, updates: Partial<Post>) => void
  deletePost: (id: string) => void
  toggleLike: (id: string) => void
  toggleBookmark: (id: string) => void
  saveDraft: (text: string, replyTo?: Post) => void
  clearDraft: () => void
  getDraft: () => { text: string, replyTo: Post | null }
}

export const usePostStore = create<PostState>((set, get) => ({
  posts: new Map(),
  likes: new Map(),
  bookmarks: new Set(),
  composeDraft: '',
  replyTo: null,
  
  addPost: (post) => set((state) => {
    const newPosts = new Map(state.posts)
    newPosts.set(post.id, post)
    return { posts: newPosts }
  }),
  
  updatePost: (id, updates) => set((state) => {
    const newPosts = new Map(state.posts)
    const post = newPosts.get(id)
    if (post) {
      newPosts.set(id, { ...post, ...updates })
    }
    return { posts: newPosts }
  }),
  
  toggleLike: (id) => set((state) => {
    const newLikes = new Map(state.likes)
    newLikes.set(id, !newLikes.get(id))
    return { likes: newLikes }
  }),
  
  toggleBookmark: (id) => set((state) => {
    const newBookmarks = new Set(state.bookmarks)
    if (newBookmarks.has(id)) {
      newBookmarks.delete(id)
    } else {
      newBookmarks.add(id)
    }
    return { bookmarks: newBookmarks }
  }),
  
  saveDraft: (text, replyTo) => set({ composeDraft: text, replyTo: replyTo || null }),
  clearDraft: () => set({ composeDraft: '', replyTo: null }),
  getDraft: () => ({ text: get().composeDraft, replyTo: get().replyTo }),
}))
```

#### use-ui-store.ts
```typescript
interface UIState {
  // Layout
  sidebarOpen: boolean
  rightSidebarOpen: boolean
  
  // Modals
  composeModalOpen: boolean
  editProfileModalOpen: boolean
  
  // Theme
  theme: 'dark' | 'light' | 'system'
  
  // Feed
  currentFeed: 'for-you' | 'following'
  
  // Actions
  toggleSidebar: () => void
  openCompose: () => void
  closeCompose: () => void
  setTheme: (theme: 'dark' | 'light' | 'system') => void
  setFeed: (feed: 'for-you' | 'following') => void
}
```

#### use-user-store.ts
```typescript
interface UserState {
  currentUser: User | null
  following: Set<string>              // Following user IDs
  
  // Actions
  setCurrentUser: (user: User) => void
  followUser: (userId: string) => void
  unfollowUser: (userId: string) => void
  updateProfile: (updates: Partial<User>) => void
}
```

---

### Server State (React Query / TanStack Query)

#### hooks/use-posts.ts
```typescript
import { useInfiniteQuery, useMutation, useQueryClient } from '@tanstack/react-query'

// Infinite feed query
export function useInfiniteFeed(type: 'for-you' | 'following') {
  return useInfiniteQuery({
    queryKey: ['feed', type],
    queryFn: async ({ pageParam }) => {
      const res = await fetch(`/api/posts?cursor=${pageParam}&type=${type}`)
      return res.json()
    },
    initialPageParam: null,
    getNextPageParam: (lastPage) => lastPage.nextCursor,
    staleTime: 1000 * 60 * 5,  // 5 minutes
  })
}

// Create post mutation
export function useCreatePost() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: async (data: CreatePostInput) => {
      const res = await fetch('/api/posts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      })
      return res.json()
    },
    onSuccess: (newPost) => {
      // Invalidate feed queries to refetch
      queryClient.invalidateQueries({ queryKey: ['feed'] })
      // Add to local Zustand store
      usePostStore.getState().addPost(newPost)
      // Clear compose draft
      usePostStore.getState().clearDraft()
    },
  })
}

// Like post mutation (optimistic)
export function useLikePost(postId: string) {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: async () => {
      await fetch(`/api/posts/${postId}/like`, { method: 'POST' })
    },
    onMutate: async () => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: ['post', postId] })
      
      // Snapshot previous value
      const previousLike = queryClient.getQueryData(['post', postId])
      
      // Optimistic update in Zustand
      usePostStore.getState().toggleLike(postId)
      
      return { previousLike }
    },
    onError: (err, variables, context) => {
      // Rollback on error
      if (context?.previousLike) {
        queryClient.setQueryData(['post', postId], context.previousLike)
      }
    },
    onSettled: () => {
      // Always refetch after error/success
      queryClient.invalidateQueries({ queryKey: ['post', postId] })
    },
  })
}

// Delete post mutation
export function useDeletePost() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: async (postId: string) => {
      await fetch(`/api/posts/${postId}`, { method: 'DELETE' })
    },
    onSuccess: (_, postId) => {
      // Remove from local store
      usePostStore.getState().deletePost(postId)
      // Invalidate feed
      queryClient.invalidateQueries({ queryKey: ['feed'] })
    },
  })
}
```

#### hooks/use-users.ts
```typescript
// Profile query
export function useProfile(username: string) {
  return useQuery({
    queryKey: ['profile', username],
    queryFn: async () => {
      const res = await fetch(`/api/users/${username}`)
      return res.json()
    },
    staleTime: 1000 * 60 * 10,  // 10 minutes
  })
}

// Current user query
export function useCurrentUser() {
  return useQuery({
    queryKey: ['user', 'current'],
    queryFn: async () => {
      const res = await fetch('/api/auth/me')
      return res.json()
    },
    staleTime: 1000 * 60 * 30,  // 30 minutes
  })
}

// Follow mutation
export function useFollow() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: async (userId: string) => {
      await fetch(`/api/users/${userId}/follow`, { method: 'POST' })
    },
    onSuccess: (_, userId) => {
      useUserStore.getState().followUser(userId)
      queryClient.invalidateQueries({ queryKey: ['profile'] })
    },
  })
}

// Unfollow mutation
export function useUnfollow() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: async (userId: string) => {
      await fetch(`/api/users/${userId}/follow`, { method: 'DELETE' })
    },
    onSuccess: (_, userId) => {
      useUserStore.getState().unfollowUser(userId)
      queryClient.invalidateQueries({ queryKey: ['profile'] })
    },
  })
}
```

#### hooks/use-search.ts
```typescript
// Search query with debounce
export function useSearch(query: string, type: 'posts' | 'users' | 'media') {
  return useQuery({
    queryKey: ['search', query, type],
    queryFn: async () => {
      const res = await fetch(`/api/search?q=${encodeURIComponent(query)}&type=${type}`)
      return res.json()
    },
    enabled: query.length >= 2,  // Only search if 2+ chars
    staleTime: 1000 * 60 * 5,
  })
}

// Trending topics
export function useTrending() {
  return useQuery({
    queryKey: ['trending'],
    queryFn: async () => {
      const res = await fetch('/api/trending')
      return res.json()
    },
    staleTime: 1000 * 60 * 15,  // 15 minutes
  })
}

// User suggestions
export function useUserSuggestions() {
  return useQuery({
    queryKey: ['user-suggestions'],
    queryFn: async () => {
      const res = await fetch('/api/users/suggestions')
      return res.json()
    },
    staleTime: 1000 * 60 * 30,
  })
}
```

---

### URL State (Next.js Search Params)

```typescript
// Feed filters
/home?tab=for-you
/home?tab=following&cursor=abc123

// Search
/search?q=react&type=posts
/search?q=john&type=users

// Profile
/profile/username?tab=posts
/profile/username?tab=media

// Modal routes (parallel routes)
/compose              → Opens compose modal
/settings/profile     → Opens profile settings modal
/profile/john/123     → Single post view

// Using useSearchParams hook
const searchParams = useSearchParams()
const tab = searchParams.get('tab') || 'for-you'
const cursor = searchParams.get('cursor')
const query = searchParams.get('q')

// Using useRouter for navigation
const router = useRouter()
router.push('/home?tab=following')
router.replace(`/profile/${username}?tab=media`)
```

---

## ⚙️ Configuration Files

### tailwind.config.ts
```typescript
import type { Config } from 'tailwindcss'

const config: Config = {
  darkMode: ['class'],
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        border: 'hsl(var(--border))',
        input: 'hsl(var(--input))',
        ring: 'hsl(var(--ring))',
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        
        // Masonic theme colors
        masonic: {
          navy: {
            DEFAULT: '#1a2332',
            50: '#f0f4f8',
            100: '#d9e2ec',
            200: '#bcccdc',
            300: '#9fb3c8',
            400: '#8299b3',
            500: '#668099',
            600: '#4d667a',
            700: '#334d5c',
            800: '#1a2332',
            900: '#0f172a',
            950: '#020617',
          },
          gold: {
            DEFAULT: '#d4a843',
            50: '#fffbeb',
            100: '#fef3c7',
            200: '#fde68a',
            300: '#fcd34d',
            400: '#fbbf24',
            500: '#d4a843',
            600: '#b48811',
            700: '#946909',
            800: '#75530b',
            900: '#614714',
          },
          marble: {
            50: '#fafafa',
            100: '#f5f5f5',
            200: '#e5e5e5',
            300: '#d4d4d4',
            400: '#a3a3a3',
            500: '#737373',
            600: '#525252',
            700: '#404040',
            800: '#262626',
            900: '#171717',
          },
        },
        
        // shadcn/ui semantic colors
        primary: {
          DEFAULT: 'hsl(var(--primary))',
          foreground: 'hsl(var(--primary-foreground))',
        },
        secondary: {
          DEFAULT: 'hsl(var(--secondary))',
          foreground: 'hsl(var(--secondary-foreground))',
        },
        destructive: {
          DEFAULT: 'hsl(var(--destructive))',
          foreground: 'hsl(var(--destructive-foreground))',
        },
        muted: {
          DEFAULT: 'hsl(var(--muted))',
          foreground: 'hsl(var(--muted-foreground))',
        },
        accent: {
          DEFAULT: 'hsl(var(--accent))',
          foreground: 'hsl(var(--accent-foreground))',
        },
        popover: {
          DEFAULT: 'hsl(var(--popover))',
          foreground: 'hsl(var(--popover-foreground))',
        },
        card: {
          DEFAULT: 'hsl(var(--card))',
          foreground: 'hsl(var(--card-foreground))',
        },
      },
      fontFamily: {
        heading: ['var(--font-playfair)', 'serif'],
        body: ['var(--font-inter)', 'sans-serif'],
        mono: ['var(--font-jetbrains-mono)', 'monospace'],
      },
      backgroundImage: {
        'geometric-pattern': "url('/patterns/compass-square.svg')",
        'marble-texture': "url('/textures/marble-light.png')",
        'golden-gradient': 'linear-gradient(135deg, #d4a843 0%, #fbbf24 100%)',
        'navy-gradient': 'linear-gradient(135deg, #1a2332 0%, #0f172a 100%)',
      },
      boxShadow: {
        'gold': '0 4px 14px rgba(212, 168, 67, 0.3)',
        'navy': '0 4px 14px rgba(15, 23, 42, 0.4)',
        'glow': '0 0 20px rgba(212, 168, 67, 0.5)',
        'inner-gold': 'inset 0 2px 4px rgba(212, 168, 67, 0.2)',
      },
      animation: {
        'spin-slow': 'spin 3s linear infinite',
        'pulse-gold': 'pulse-gold 2s ease-in-out infinite',
        'fade-in': 'fade-in 0.3s ease-out',
        'slide-up': 'slide-up 0.4s ease-out',
        'slide-down': 'slide-down 0.4s ease-out',
        'scale-in': 'scale-in 0.3s ease-out',
        'border-glow': 'border-glow 2s ease-in-out infinite',
      },
      keyframes: {
        'pulse-gold': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.7' },
        },
        'fade-in': {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        'slide-up': {
          '0%': { transform: 'translateY(10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        'slide-down': {
          '0%': { transform: 'translateY(-10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        'scale-in': {
          '0%': { transform: 'scale(0.95)', opacity: '0' },
          '100%': { transform: 'scale(1)', opacity: '1' },
        },
        'border-glow': {
          '0%, 100%': {
            boxShadow: '0 0 5px rgba(212, 168, 67, 0.3)',
          },
          '50%': {
            boxShadow: '0 0 15px rgba(212, 168, 67, 0.6)',
          },
        },
      },
      spacing: {
        '18': '4.5rem',
        '88': '22rem',
        '128': '32rem',
      },
      zIndex: {
        '60': '60',
        '70': '70',
        '80': '80',
        '90': '90',
        '100': '100',
      },
    },
  },
  plugins: [require('tailwindcss-animate'), require('@tailwindcss/typography')],
}

export default config
```

---

### globals.css
```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    /* Masonic Navy Theme - Dark Mode */
    --background: 222 47% 11%;      /* Navy 900 */
    --foreground: 210 40% 98%;
    
    --card: 222 47% 11%;
    --card-foreground: 210 40% 98%;
    
    --popover: 222 47% 11%;
    --popover-foreground: 210 40% 98%;
    
    --primary: 45 67% 55%;          /* Gold 500 */
    --primary-foreground: 222 47% 11%;
    
    --secondary: 217 33% 17%;       /* Navy 800 */
    --secondary-foreground: 210 40% 98%;
    
    --muted: 217 33% 17%;
    --muted-foreground: 215 20% 65%;
    
    --accent: 45 67% 55%;
    --accent-foreground: 222 47% 11%;
    
    --destructive: 0 62% 30%;
    --destructive-foreground: 210 40% 98%;
    
    --border: 45 67% 55% / 20%;
    --input: 45 67% 55% / 20%;
    --ring: 45 67% 55%;
    
    --radius: 0.5rem;
    
    /* Masonic specific */
    --masonic-gold: #d4a843;
    --masonic-navy: #1a2332;
    --masonic-marble: #fafafa;
  }
 
  .light {
    /* Light Mode */
    --background: 60 9% 98%;        /* Marble 50 */
    --foreground: 222 47% 11%;
    
    --card: 0 0% 100%;
    --card-foreground: 222 47% 11%;
    
    --popover: 0 0% 100%;
    --popover-foreground: 222 47% 11%;
    
    --primary: 45 67% 55%;
    --primary-foreground: 222 47% 11%;
    
    --secondary: 60 9% 96%;
    --secondary-foreground: 222 47% 11%;
    
    --muted: 60 9% 96%;
    --muted-foreground: 215 20% 45%;
    
    --accent: 45 67% 55%;
    --accent-foreground: 222 47% 11%;
    
    --destructive: 0 62% 30%;
    --destructive-foreground: 210 40% 98%;
    
    --border: 45 67% 55% / 30%;
    --input: 45 67% 55% / 30%;
    --ring: 45 67% 55%;
  }
}

@layer base {
  * {
    @apply border-border;
  }
  
  body {
    @apply bg-background text-foreground;
    font-feature-settings: "rlig" 1, "calt" 1;
  }
  
  h1, h2, h3, h4, h5, h6 {
    font-family: var(--font-playfair);
    font-weight: 600;
    letter-spacing: -0.02em;
  }
  
  h1 { @apply text-4xl; }
  h2 { @apply text-3xl; }
  h3 { @apply text-2xl; }
  h4 { @apply text-xl; }
  h5 { @apply text-lg; }
  h6 { @apply text-base; }
  
  a {
    @apply text-primary hover:underline;
  }
}

/* Masonic geometric pattern background */
.bg-geometric {
  background-image: url('/patterns/compass-square.svg');
  background-size: 200px 200px;
  background-position: center;
  opacity: 0.05;
  pointer-events: none;
}

/* Marble texture overlay */
.bg-marble {
  background-image: url('/textures/marble-light.png');
  background-size: 400px 400px;
  opacity: 0.1;
  pointer-events: none;
}

/* Gold border glow animation */
@keyframes border-glow {
  0%, 100% {
    box-shadow: 0 0 5px rgba(212, 168, 67, 0.3);
  }
  50% {
    box-shadow: 0 0 15px rgba(212, 168, 67, 0.6);
  }
}

.gold-border-glow {
  border: 1px solid rgba(212, 168, 67, 0.4);
  animation: border-glow 2s ease-in-out infinite;
}

/* Verified badge gold shimmer */
@keyframes shimmer {
  0% {
    background-position: -1000px 0;
  }
  100% {
    background-position: 1000px 0;
  }
}

.verified-shimmer {
  background: linear-gradient(
    90deg,
    #d4a843 0%,
    #fbbf24 50%,
    #d4a843 100%
  );
  background-size: 1000px 100%;
  animation: shimmer 3s infinite;
}

/* Loading spinner gold rotation */
@keyframes spin-gold {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.spinner-gold {
  border: 3px solid rgba(212, 168, 67, 0.2);
  border-top-color: #d4a843;
  animation: spin-gold 1s linear infinite;
}

/* Card hover effect with gold glow */
.card-masonic {
  @apply bg-card border border-border/40 rounded-lg transition-all duration-300;
}

.card-masonic:hover {
  @apply border-gold/60;
  box-shadow: 0 4px 14px rgba(212, 168, 67, 0.3);
}

/* Masonic button variant */
.btn-masonic {
  @apply bg-gradient-to-r from-gold-500 to-gold-400 
         text-navy-900 font-semibold 
         border-2 border-gold-600 
         hover:from-gold-400 hover:to-gold-300
         active:scale-95 transition-all duration-200;
}

/* Scrollbar styling */
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  @apply bg-navy-900;
}

::-webkit-scrollbar-thumb {
  @apply bg-gold-500/50 rounded-full;
}

::-webkit-scrollbar-thumb:hover {
  @apply bg-gold-500/70;
}

/* Selection color */
::selection {
  @apply bg-gold-500/30 text-foreground;
}
```

---

### next.config.js
```typescript
/** @type {import('next').NextConfig} */
const nextConfig = {
  // Image optimization
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'utfs.io',
        port: '',
        pathname: '/**',
      },
      {
        protocol: 'https',
        hostname: 'avatars.githubusercontent.com',
      },
      {
        protocol: 'https',
        hostname: 'pbs.twimg.com',
      },
      {
        protocol: 'https',
        hostname: 'i.imgur.com',
      },
    ],
    formats: ['image/avif', 'image/webp'],
    deviceSizes: [640, 750, 828, 1080, 1200, 1920, 2048, 3840],
    imageSizes: [16, 32, 48, 64, 96, 128, 256, 384],
  },
  
  // Server actions
  experimental: {
    serverActions: {
      bodySizeLimit: '2mb',
    },
  },
  
  // Headers for security
  async headers() {
    return [
      {
        source: '/:path*',
        headers: [
          {
            key: 'X-DNS-Prefetch-Control',
            value: 'on',
          },
          {
            key: 'Strict-Transport-Security',
            value: 'max-age=63072000; includeSubDomains; preload',
          },
          {
            key: 'X-XSS-Protection',
            value: '1; mode=block',
          },
          {
            key: 'X-Frame-Options',
            value: 'SAMEORIGIN',
          },
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff',
          },
          {
            key: 'Referrer-Policy',
            value: 'strict-origin-when-cross-origin',
          },
        ],
      },
    ];
  },
  
  // Redirects
  async redirects() {
    return [
      {
        source: '/',
        has: [{ type: 'cookie', key: 'auth-token' }],
        destination: '/home',
        permanent: false,
      },
      {
        source: '/home',
        has: [{ type: 'cookie', key: 'auth-token', value: '' }],
        destination: '/login',
        permanent: false,
      },
    ];
  },
}

module.exports = nextConfig
```

---

### netlify.toml
```toml
[build]
  command = "npm run build"
  publish = ".next"

# Next.js plugin
[[plugins]]
  package = "@netlify/plugin-nextjs"

# Edge functions
[functions]
  directory = "netlify/functions"

# Security headers
[[headers]]
  for = "/*"
  [headers.values]
    X-Frame-Options = "DENY"
    X-Content-Type-Options = "nosniff"
    Referrer-Policy = "strict-origin-when-cross-origin"
    Permissions-Policy = "camera=(), microphone=(), geolocation=()"

# Image optimization
[[redirects]]
  from = "/_next/image/*"
  to = "/.netlify/images/:splat"
  status = 200

# Cache static assets
[[headers]]
  for = "/static/*"
  [headers.values]
    Cache-Control = "public, max-age=31536000, immutable"

# ISR for profile pages
[[headers]]
  for = "/profile/*"
  [headers.values]
    Cache-Control = "public, max-age=60, stale-while-revalidate=300"

# ISR for feed
[[headers]]
  for = "/api/posts"
  [headers.values]
    Cache-Control = "public, max-age=30, stale-while-revalidate=120"

# Compress responses
[[headers]]
  for = "/*"
  [headers.values]
    X-Netlify-Compress = "gzip, br"
```

---

## 🚀 Netlify Deployment Strategy

### Environment Variables
```env
# Required
DATABASE_URL=postgresql://user:password@host:5432/dbname
NEXTAUTH_SECRET=your-secret-key-min-32-chars
NEXTAUTH_URL=https://your-site.netlify.app

# File Uploads
UPLOADTHING_SECRET=sk_...
UPLOADTHING_APP_ID=...

# Optional
NEXT_PUBLIC_SITE_URL=https://your-site.netlify.app
NEXT_PUBLIC_GA_ID=G-XXXXXXXXXX
```

### Performance Optimizations

#### 1. Incremental Static Regeneration (ISR)
```typescript
// Profile pages - revalidate every 60 seconds
export const revalidate = 60

// Trending topics - revalidate every 5 minutes
export const revalidate = 300

// Home feed - revalidate every 30 seconds
export const revalidate = 30
```

#### 2. Edge Middleware
```typescript
// middleware.ts
export const config = {
  matcher: [
    '/home/:path*',
    '/profile/:path*',
    '/notifications',
    '/messages',
    '/bookmarks',
  ],
}
```

#### 3. Image Optimization
- Use Uploadthing for CDN (free tier: 3GB storage)
- Next.js Image component with proper `sizes` prop
- WebP/AVIF formats automatically
- Lazy loading below fold

#### 4. Client-side Optimizations
```typescript
// Code splitting with dynamic imports
const ComposeModal = dynamic(() => import('@/components/compose/compose-modal'), {
  ssr: false,
  loading: () => <LoadingSpinner />
})

// React Query caching
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5,  // 5 minutes
      gcTime: 1000 * 60 * 30,    // 30 minutes
      refetchOnWindowFocus: false,
    },
  },
})

// Optimistic UI updates
onMutate: async () => {
  // Update UI immediately before server response
  usePostStore.getState().toggleLike(postId)
}
```

---

## 📊 Database Schema (Prisma)

```prisma
generator client {
  provider = "prisma-client-js"
}

datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}

model User {
  id            String    @id @default(cuid())
  username      String    @unique
  email         String    @unique
  password      String
  name          String?
  bio           String?   @db.Text
  avatar        String?
  banner        String?
  location      String?
  website       String?
  verified      Boolean   @default(false)
  createdAt     DateTime  @default(now())
  updatedAt     DateTime  @updatedAt
  
  posts         Post[]
  replies       Post[]    @relation("ReplyTo")
  likes         Like[]
  bookmarks     Bookmark[]
  follows       Follow[]  @relation("following")
  followers     Follow[]  @relation("follower")
  notifications Notification[]
  sessions      Session[]
  accounts      Account[]
  
  @@index([username])
  @@index([email])
  @@map("users")
}

model Post {
  id          String    @id @default(cuid())
  content     String    @db.Text
  media       Json?     // [{type: "image"|"video"|"gif", url, width, height}]
  poll        Json?     // {options: [{text, votes}], duration, endsAt}
  replyToId   String?
  replyTo     Post?     @relation("ReplyTo", fields: [replyToId], references: [id], onDelete: Cascade)
  replies     Post[]    @relation("ReplyTo")
  authorId    String
  author      User      @relation(fields: [authorId], references: [id], onDelete: Cascade)
  createdAt   DateTime  @default(now())
  updatedAt   DateTime  @updatedAt
  views       Int       @default(0)
  
  likes       Like[]
  bookmarks   Bookmark[]
  reposts     Repost[]
  
  @@index([authorId])
  @@index([createdAt])
  @@index([replyToId])
  @@map("posts")
}

model Like {
  id        String   @id @default(cuid())
  userId    String
  user      User     @relation(fields: [userId], references: [id], onDelete: Cascade)
  postId    String
  post      Post     @relation(fields: [postId], references: [id], onDelete: Cascade)
  createdAt DateTime @default(now())
  
  @@unique([userId, postId])
  @@index([postId])
  @@map("likes")
}

model Bookmark {
  id        String   @id @default(cuid())
  userId    String
  user      User     @relation(fields: [userId], references: [id], onDelete: Cascade)
  postId    String
  post      Post     @relation(fields: [postId], references: [id], onDelete: Cascade)
  createdAt DateTime @default(now())
  
  @@unique([userId, postId])
  @@index([postId])
  @@map("bookmarks")
}

model Follow {
  id          String   @id @default(cuid())
  followerId  String
  follower    User     @relation("follower", fields: [followerId], references: [id], onDelete: Cascade)
  followingId String
  following   User     @relation("following", fields: [followingId], references: [id], onDelete: Cascade)
  createdAt   DateTime @default(now())
  
  @@unique([followerId, followingId])
  @@index([followingId])
  @@map("follows")
}

model Repost {
  id        String   @id @default(cuid())
  userId    String
  user      User     @relation(fields: [userId], references: [id], onDelete: Cascade)
  postId    String
  post      Post     @relation(fields: [postId], references: [id], onDelete: Cascade)
  createdAt DateTime @default(now())
  
  @@unique([userId, postId])
  @@index([postId])
  @@map("reposts")
}

model Notification {
  id        String   @id @default(cuid())
  userId    String
  user      User     @relation(fields: [userId], references: [id], onDelete: Cascade)
  type      String   // "like", "repost", "follow", "reply", "mention"
  postId    String?
  fromUserId String?
  read      Boolean  @default(false)
  createdAt DateTime @default(now())
  
  @@index([userId])
  @@index([createdAt])
  @@map("notifications")
}

model Session {
  id           String   @id @default(cuid())
  userId       String
  user         User     @relation(fields: [userId], references: [id], onDelete: Cascade)
  sessionToken String   @unique
  expires      DateTime
  createdAt    DateTime @default(now())
  
  @@index([userId])
  @@map("sessions")
}

model Account {
  id                String  @id @default(cuid())
  userId            String
  user              User    @relation(fields: [userId], references: [id], onDelete: Cascade)
  type              String
  provider          String
  providerAccountId String
  refresh_token     String? @db.Text
  access_token      String? @db.Text
  expires_at        Int?
  token_type        String?
  scope             String?
  id_token          String? @db.Text
  
  @@unique([provider, providerAccountId])
  @@index([userId])
  @@map("accounts")
}
```

---

## 🎯 Features Summary

### Core Social Features
- ✅ Create posts (text 280 chars, 4 images, 1 video, or GIF)
- ✅ Polls (2-4 options, 5min-7days duration)
- ✅ Reply to posts (nested threads)
- ✅ Repost with/without comment
- ✅ Like posts (with gold heart animation)
- ✅ Bookmark posts (with folder organization)
- ✅ Follow/unfollow users
- ✅ Block/mute users
- ✅ Home feed (For You algorithmic / Following chronological)
- ✅ User profiles (customizable banner, avatar, bio)
- ✅ Search (posts, users, media) with autocomplete
- ✅ Notifications (likes, reposts, follows, replies, mentions)
- ✅ Direct messages (real-time)
- ✅ Trending topics (geographic)
- ✅ Who to follow suggestions
- ✅ Verified badges (gold checkmark)

### Masonic Aesthetic Features
- ✅ Deep navy backgrounds (#1a2332, #0f172a)
- ✅ Gold/amber accents (#d4a843, #b48811)
- ✅ Marble white content cards (#fafafa)
- ✅ Geometric compass & square SVG patterns
- ✅ Golden ratio masonry grid layout
- ✅ Playfair Display serif headings
- ✅ Inter sans-serif body text
- ✅ Gold border glow animations on hover
- ✅ Verified badge with gold shimmer effect
- ✅ Gold animated loading spinner
- ✅ Masonic logo throughout app
- ✅ Custom gold gradient buttons
- ✅ Warm amber-tinted shadows

### Technical Features
- ✅ Next.js 14 App Router
- ✅ React Server Components for SEO
- ✅ ISR for profiles & trending (revalidate 60s)
- ✅ Optimistic UI updates (likes, follows)
- ✅ Infinite scroll pagination (cursor-based)
- ✅ Real-time search suggestions (debounced 300ms)
- ✅ Dark/light/system theme toggle
- ✅ Responsive design (mobile-first)
- ✅ Image optimization (WebP/AVIF)
- ✅ Draft autosave (localStorage, 7 days)
- ✅ Keyboard shortcuts (j/k navigation, n compose)
- ✅ PWA support (offline mode, install prompt)
- ✅ Accessibility (WCAG 2.1 AA compliant)
- ✅ Analytics integration (Google Analytics)

---

**Generated:** QWEN-FRONTEND-ARCH.md  
**Complete Architecture:** Ready for implementation
