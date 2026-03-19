# Clay Webhook OS — Dark Retro Mac UI Redesign Prompt

You are redesigning the Clay Webhook OS dashboard with a **Dark Retro Apple** aesthetic. Think: the soul of classic Macintosh (System 7, Mac OS 9, early Aqua) — but rendered in a modern dark mode. Not a literal recreation. An *evocation*. The feeling of discovering a beautiful piece of software on a late-90s Power Mac G3, but built with today's tools.

---

## Design Philosophy

### The Vibe
- **Dark, warm, tactile** — not the cold blue-gray of corporate dark modes
- **Classic Mac DNA**: window chrome, beveled edges, pixel-crisp borders, inset panels
- **CRT warmth**: subtle scanline texture overlays, slight glow on active elements, phosphor-green or amber accents on a near-black background
- **Skeuomorphic whispers**: not full skeuomorphism, but *hints* — subtle inner shadows on input fields (like they're carved into the surface), raised buttons that look pressable, window title bars with texture
- **Software as craft**: every pixel considered, nothing feels "default"

### Reference Points
- **System 7 / Mac OS 9**: Chicago font energy, platinum appearance, window widgets (close/zoom/collapse), striped title bars
- **Early Aqua (Mac OS X 10.0-10.2)**: brushed metal, translucent panels, pinstripe backgrounds, pulsing default buttons, genie effects
- **NeXTSTEP**: dark chrome, sophisticated developer-tool aesthetic, the terminal as art
- **HyperCard**: warm, creative, hand-crafted interface energy
- **After Dark screensavers**: that mysterious, playful dark-screen aesthetic
- **Modern retro-Mac apps**: Panic's apps (Transmit, Nova), Rogue Amoeba's tools — they capture the spirit without being kitsch

### What This Is NOT
- Not vaporwave or synthwave (no neon pink/purple gradients)
- Not pixel art or 8-bit
- Not a literal System 7 skin (no actual Chicago bitmap font)
- Not dark mode Bootstrap — this should feel *distinctive* and *crafted*

---

## Color System

### Base Palette — "Dark Platinum"
```
--bg-deep:        #0a0a0b     /* deepest background, like a CRT off-state */
--bg-surface:     #141416     /* card/panel backgrounds */
--bg-raised:      #1c1c1f     /* elevated surfaces, sidebars */
--bg-overlay:     #232327     /* modals, dropdowns, popovers */
--bg-inset:       #0e0e10     /* inset fields, code blocks — darker than surface */

--border-subtle:  #2a2a2e     /* subtle dividers */
--border-default: #3a3a40     /* card borders, input borders */
--border-strong:  #4a4a52     /* focused/active borders */

--text-primary:   #e8e6e3     /* warm off-white, not pure white */
--text-secondary: #9a9892     /* muted text, labels */
--text-tertiary:  #6a6862     /* disabled, placeholder */
--text-inverse:   #0a0a0b     /* text on light backgrounds */
```

### Accent Colors — "Retro Mac"
```
--accent-primary:     #4a9ead    /* muted teal — your kiln-teal, but softer for dark bg */
--accent-primary-hover: #5cb8c8  /* lighter on hover */
--accent-primary-glow: #4a9ead33 /* 20% glow for focus rings, active states */

--accent-warm:        #c4a083    /* warm rose/clay — secondary, like brushed metal highlight */
--accent-amber:       #d4a843    /* warm amber — warnings, info badges */
--accent-green:       #5a9a6a    /* muted sage — success states, health indicators */
--accent-red:         #c45a4a    /* warm brick red — errors, destructive — not alarming, dignified */

--accent-phosphor:    #7acea0    /* phosphor green — for terminal/log output, mono text accents */
```

### Special Effects
```
--glow-teal:    0 0 12px #4a9ead44    /* subtle glow on focused/active elements */
--glow-amber:   0 0 8px #d4a84333     /* warning glow */
--inset-shadow:  inset 0 1px 3px #00000066  /* carved-in feel for inputs */
--raised-shadow: 0 1px 0 #ffffff0a, 0 2px 8px #00000044  /* raised button: top highlight + drop shadow */
--window-shadow: 0 8px 32px #00000066, 0 1px 0 #ffffff08 inset  /* window/card shadow with top inner highlight */
```

---

## Typography

### Font Stack
- **Headings**: `"SF Pro Display", "Helvetica Neue", system-ui` — the Apple bloodline
- **Body**: `"SF Pro Text", "Helvetica Neue", system-ui` — crisp readability
- **Monospace**: `"SF Mono", "Fragment Mono", "Berkeley Mono", "JetBrains Mono", monospace` — for data, code, technical readouts
- **Accent/Retro** (sparingly, for branding): `"Chicago", "Geneva", system-ui` — only for the logo or special decorative elements. Don't actually load Chicago; use a pixel-style web font alternative like "Silkscreen" or just use SF Pro in uppercase with letter-spacing.

### Type Scale
- Use the existing scale but increase letter-spacing slightly on uppercase labels (+0.05em)
- Monospace numbers in data displays (tabular-nums)
- Title bars: 13px, medium weight, slightly tracked

---

## Component Design Language

### Windows / Cards
Every card should feel like a **classic Mac window**:
- **Title bar**: 28-32px height, `--bg-raised` background, subtle bottom border
  - Optional: very subtle horizontal stripe texture (1px alternating lines at 3% opacity)
  - Window title: centered, `--text-secondary`, 13px medium
  - Optional: traffic light dots (close/minimize/zoom) as pure decoration — 8px circles, `--accent-red`, `--accent-amber`, `--accent-green` at 60% opacity
- **Body**: `--bg-surface` with `--border-default` border, rounded corners (8px — not too round)
- **Shadow**: `--window-shadow` — substantial but not overwhelming
- **Inner content padding**: 16-20px

### Buttons
- **Primary**: `--accent-primary` background, `--text-inverse` text, subtle top inner highlight (`inset 0 1px 0 #ffffff15`), bottom shadow. On hover: lighten + gentle glow. On press: remove top highlight, add `inset 0 1px 2px #00000033` (pressed-in feel)
- **Secondary/Outline**: transparent bg, `--border-default` border, `--text-primary` text. Hover: `--bg-raised` background
- **Ghost**: no border, `--text-secondary`. Hover: `--bg-overlay` background
- **Destructive**: `--accent-red` but muted — not screaming. Same raised/pressed behavior as primary
- **Default button pulse**: the primary action button on a dialog can have a very subtle pulse animation (opacity 0.8 → 1.0, 2s ease) — classic Aqua homage

### Inputs & Text Areas
- `--bg-inset` background (darker than the surface — feels carved in)
- `--border-default` border, `--border-strong` on focus
- `--inset-shadow` for that recessed feel
- Focus: `--accent-primary` border + `--glow-teal` box-shadow
- Placeholder text: `--text-tertiary`
- No background change on focus — the glow is enough

### Sidebar / Navigation
- `--bg-raised` background, right border `--border-subtle`
- Nav items: ghost button style, `--text-secondary`
- Active item: `--accent-primary` text, `--accent-primary-glow` background, left accent bar (2px, `--accent-primary`)
- Section headers: uppercase, `--text-tertiary`, 11px, tracked +0.1em
- Keyboard shortcut badges: `--bg-inset` background, `--text-tertiary`, monospace, 10px — look like tiny keycaps
- Logo area: minimal — "Webhook OS" in the retro accent style, or a small monochrome apple-era-inspired icon

### Tables
- No zebra striping — too modern
- Instead: subtle bottom borders on rows (`--border-subtle`)
- Header row: `--bg-raised`, uppercase labels, 11px, tracked, `--text-tertiary`
- Hover row: `--bg-overlay` with smooth transition (150ms)
- Selected row: `--accent-primary-glow` background

### Badges / Status Indicators
- Rounded-full pills
- Background: accent color at 15% opacity
- Text: accent color at full
- Optional: 1px border in accent color at 25%
- Tiny status dots (6px): solid accent color with subtle glow

### Tabs
- Underline style, not boxed — cleaner in dark UI
- Inactive: `--text-tertiary`, no underline
- Active: `--text-primary`, 2px bottom border in `--accent-primary`
- Hover: `--text-secondary`

### Dialogs / Modals
- `--bg-overlay` background
- Window chrome treatment (title bar with optional traffic lights)
- Backdrop: `#000000` at 60% with backdrop-blur (8px)
- Shadow: large and dramatic — `0 24px 64px #00000088`

### Tooltips
- `--bg-overlay` with `--border-default` border
- Small, 12px, `--text-secondary`
- Subtle shadow, no arrow (or very small arrow)

### Toast Notifications
- Window-chrome style with title bar
- Slide in from top-right (classic Mac notification position)
- Success: `--accent-green` left border accent
- Error: `--accent-red` left border accent
- Info: `--accent-amber` left border accent

### Empty States
- Centered, generous whitespace
- Muted icon (32px, `--text-tertiary`)
- Brief copy in `--text-secondary`
- Single CTA button

### Loading / Skeleton States
- Subtle pulse animation on `--bg-raised` → `--bg-overlay` → `--bg-raised`
- Duration: 1.5s ease-in-out
- Not shimmer — pulse feels more organic, more retro

---

## Texture & Effects

### Subtle Noise/Grain
- Apply a very subtle noise texture overlay (2-3% opacity) to the `--bg-deep` background
- Creates that CRT/analog warmth — kills the "flat digital" feel
- Implementation: CSS `background-image` with a tiny noise PNG tiled, or a CSS gradient trick

### Scanline Hint (Optional — Very Subtle)
- On the deepest background only: repeating horizontal lines (1px `#ffffff` at 1-2% opacity, every 3px)
- Should be barely perceptible — more of a feeling than a visual
- Skip this if it feels gimmicky after implementation

### Inner Glow on Active Panels
- The currently active/focused panel gets a very subtle inner glow: `inset 0 0 20px #4a9ead08`
- Almost invisible but creates a sense of "this is alive"

### Transitions
- All color/background transitions: 150ms ease
- Transform transitions (hover scale, etc.): 200ms ease-out
- No bouncy/spring animations — Mac classic was crisp and immediate
- Exception: the Aqua button pulse (slow, gentle)

---

## Page-Specific Notes

### Dashboard (Home)
- Stat cards: window-chrome style, each with a title bar showing the metric name
- Charts (Recharts): dark theme — `--bg-surface` chart background, `--accent-primary` for primary data line, `--accent-warm` for secondary, `--border-subtle` for grid lines, `--text-tertiary` for axis labels
- Recent activity feed: compact list with monospace timestamps, left-aligned status dots

### Run (Playground)
- Skill selector: dropdown with window-chrome styling
- Input form: inset textarea with the carved-in shadow
- Output: monospace, `--accent-phosphor` text on `--bg-inset` — like a terminal readout
- Split panel feel: input on left, output on right, with a subtle draggable divider

### Context (File Explorer)
- File tree: classic Mac Finder column view energy
- File icons: monochrome, simple — folder, document, markdown
- Preview panel: inset panel with file content
- Breadcrumbs: path-style with `/` separators, monospace

### Status
- System health: green/amber/red status dots with glow
- Metrics: monospace numbers, right-aligned
- Terminal-style log viewer for recent events

### Settings
- Form sections with window-chrome headers
- Toggle switches: pill-shaped, `--accent-primary` when on, `--bg-inset` when off

---

## Implementation Notes

### Files to Modify
1. `dashboard/src/app/globals.css` — Replace the entire color system with dark retro palette + add texture/effect utilities
2. `dashboard/tailwind.config.ts` — Update color tokens and extend theme
3. `dashboard/src/components/ui/*.tsx` — Update shadcn components: card (add title bar), button (add raised/pressed states), input (add inset shadow), badge, table, tabs, dialog, skeleton, sonner
4. `dashboard/src/components/layout/sidebar.tsx` — Dark sidebar with accent bar active states and keycap shortcut badges
5. `dashboard/src/components/layout/header.tsx` — Dark header with updated health badges
6. All page components — Update any hardcoded colors or classes
7. `dashboard/src/app/layout.tsx` — Update font imports if switching to SF Pro stack

### Fonts
- SF Pro is available as a system font on macOS — use `font-family: -apple-system, "SF Pro Display"` for zero-cost loading
- For non-Mac users, falls back to system-ui which is still clean
- Keep Fragment Mono or switch to SF Mono for monospace

### shadcn Theme Variables
Update the CSS custom properties that shadcn references:
```css
:root {
  --background: 240 6% 4%;        /* --bg-deep */
  --foreground: 30 5% 90%;        /* --text-primary */
  --card: 240 5% 8%;              /* --bg-surface */
  --card-foreground: 30 5% 90%;
  --primary: 190 40% 49%;         /* --accent-primary */
  --primary-foreground: 240 6% 4%;
  --secondary: 240 5% 12%;        /* --bg-raised */
  --secondary-foreground: 30 5% 90%;
  --muted: 240 5% 12%;
  --muted-foreground: 35 5% 58%;  /* --text-secondary */
  --accent: 190 40% 49%;
  --accent-foreground: 240 6% 4%;
  --destructive: 5 50% 53%;       /* --accent-red */
  --border: 240 5% 24%;           /* --border-default */
  --input: 240 5% 24%;
  --ring: 190 40% 49%;
  --radius: 0.5rem;
}
```

### Preserve Functionality
- All existing interactions, keyboard shortcuts (⌘1-⌘8), responsive breakpoints, and data flows remain identical
- This is a **visual reskin only** — no logic changes
- Keep all Framer Motion animations but adjust them to feel crisper (reduce duration by ~20%)
- Maintain accessibility: ensure contrast ratios meet WCAG AA on the dark palette

---

## Quality Checklist
- [ ] No pure white (#ffffff) or pure black (#000000) text — always warm off-whites and near-blacks
- [ ] Every interactive element has a visible focus state (glow ring, not just outline)
- [ ] Cards feel like windows, not floating rectangles
- [ ] Inputs feel carved into the surface
- [ ] Buttons feel physically pressable (raised → pressed state change)
- [ ] The overall impression is: "Someone who loves classic Mac software made this"
- [ ] It doesn't feel like a theme — it feels like *this is how it was always meant to look*
