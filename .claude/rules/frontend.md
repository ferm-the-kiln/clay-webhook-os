---
description: Next.js/TypeScript dashboard conventions
globs: dashboard/**
---

# Frontend Conventions

## Framework
- Next.js 15 with App Router (all pages in `src/app/`)
- Turbopack for dev (`npm run dev` uses `next dev --turbopack`)
- TypeScript strict mode

## UI Stack
- Tailwind CSS 4 for styling
- shadcn/ui components in `src/components/ui/`
- Radix UI primitives (via shadcn)
- Framer Motion for animations
- Recharts for data visualization
- Sonner for toast notifications
- cmdk for command palette
- dnd-kit for drag-and-drop (pipeline builder)
- PapaParse for CSV parsing

## Code Patterns

### Pages
- Each route is a directory in `src/app/` with a `page.tsx`
- Pages are client components (`"use client"`) that compose feature components
- No server components or server actions currently in use

### Components
- Organized by feature in `src/components/{feature}/`
- Base UI components in `src/components/ui/` (shadcn — don't modify directly)
- Layout components (sidebar, header) in `src/components/layout/`

### API Client
- All API calls go through `src/lib/api.ts`
- `apiFetch<T>()` is the typed wrapper — handles auth headers and error throwing
- Export one function per endpoint (e.g., `fetchClients()`, `createCampaign()`)
- Types defined in `src/lib/types.ts`

### State Management
- Local state with `useState`/`useEffect` — no global state library
- Data fetching in components via `useEffect` + api functions
- No React Query or SWR currently

### Styling
- Use Tailwind utility classes, not CSS modules
- Use `cn()` from `src/lib/utils.ts` for conditional classes
- Follow existing color scheme and spacing patterns

## Environment
- `NEXT_PUBLIC_API_URL`: Backend API URL (default: `https://clay.nomynoms.com`)
- `NEXT_PUBLIC_API_KEY`: API key for backend auth
