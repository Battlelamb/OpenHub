# Generic - Social Platform Project Spec

## Vision
Twitter benzeri bir sosyal platform. Kullanicilar isteklerini, ihtiyaclarini post edebilir; ev, araba, kiralama, satis ilanlari verebilir; belirli konularda tanidik arayisinda bulunabilir.

## Core Features

### 1. Post System
- Kullanicilarin istek ve ihtiyaclarini post edebilmesi
- Kategoriler: Genel, Emlak (ev arasi), Arac (satis/kiralama), Hizmet, Tanidik Arama
- Post suresi: Belirli sure aktif veya surekli aktif secenegi
- Medya destegi (resim, video)
- Like, yorum, paylasim

### 2. User Profiles
- Detayli profil bilgileri
- Konum, meslek, ilgi alanlari
- Guvenilirlik skoru / dogrulama
- Portfolyo / referanslar

### 3. Authentication
- OTP destekli giris (SMS/Email)
- Third-party providers: Google (Gmail), Apple, GitHub
- Guvenli oturum yonetimi

### 4. Search & Discovery
- Kategori bazli filtreleme
- Konum bazli arama
- Akilli oneri sistemi
- Hashtag / etiket sistemi

### 5. Ad System
- Reklam alanlari
- Sponsorlu postlar
- Reklam veren paneli

### 6. Notifications
- Push notifications
- Email notifications
- In-app bildirimler

## Tech Stack

### Frontend
- **Framework**: Next.js 14+ (App Router)
- **UI**: shadcn/ui + Tailwind CSS
- **Design**: Masonic (geometric, structured, symbolic) visual theme
- **Deployment**: Netlify

### Backend
- **Database**: Supabase (PostgreSQL) veya Neon veya Convex
- **Auth**: Supabase Auth (OTP + OAuth providers)
- **Storage**: Supabase Storage (medya dosyalari)
- **Realtime**: Supabase Realtime (canli bildirimler)

### Optimization
- Tum bedava tier'lar kullanilacak (Supabase free, Netlify free, Neon free)
- Edge functions
- ISR/SSG where possible
- Image optimization
- Lazy loading
- Bundle size optimization

## Design Language
- **Masonic aesthetic**: Geometric patterns, structured layouts, symbolic elements
- **Colors**: Deep navy, gold/amber accents, marble white, dark slate
- **Typography**: Clean, authoritative serif + modern sans-serif
- **Layout**: Grid-based, card system, masonry layout for posts
- **Icons**: Geometric, minimal, symbolic

## Future Extensibility
- Marketplace modulu
- Mesajlasma sistemi
- API for third-party integrations
- Mobile app (React Native)
- AI-powered content moderation
- Payment integration
