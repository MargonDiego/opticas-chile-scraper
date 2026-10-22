---
name: Ópticas Chile
description: Independent price index for eyewear in Chile — a data tool, not a storefront.
colors:
  petrol-deep: "oklch(0.470 0.082 200)"
  petrol-hover: "oklch(0.420 0.078 200)"
  petrol-tint: "oklch(0.955 0.022 200)"
  petrol-tint-ink: "oklch(0.360 0.065 200)"
  savings-green: "oklch(0.460 0.100 155)"
  savings-tint: "oklch(0.955 0.030 155)"
  alert-amber: "oklch(0.500 0.115 65)"
  alert-tint: "oklch(0.960 0.032 75)"
  fault-red: "oklch(0.500 0.170 25)"
  fault-tint: "oklch(0.960 0.026 25)"
  canvas: "oklch(0.970 0.005 235)"
  surface: "oklch(1 0 0)"
  surface-sunken: "oklch(0.945 0.006 235)"
  ink: "oklch(0.235 0.016 250)"
  ink-muted: "oklch(0.480 0.014 250)"
  ink-subtle: "oklch(0.620 0.012 250)"
  hairline: "oklch(0.892 0.006 235)"
  hairline-strong: "oklch(0.820 0.008 235)"
typography:
  display:
    fontFamily: "\"Plus Jakarta Sans\", ui-sans-serif, system-ui, sans-serif"
    fontSize: "30px"
    fontWeight: 700
    lineHeight: 1.15
    letterSpacing: "-0.02em"
  headline:
    fontFamily: "\"Plus Jakarta Sans\", ui-sans-serif, system-ui, sans-serif"
    fontSize: "22px"
    fontWeight: 700
    lineHeight: 1.25
    letterSpacing: "-0.015em"
  title:
    fontFamily: "\"Plus Jakarta Sans\", ui-sans-serif, system-ui, sans-serif"
    fontSize: "16px"
    fontWeight: 600
    lineHeight: 1.35
  body:
    fontFamily: "\"Plus Jakarta Sans\", ui-sans-serif, system-ui, sans-serif"
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.6
  label:
    fontFamily: "\"Plus Jakarta Sans\", ui-sans-serif, system-ui, sans-serif"
    fontSize: "13px"
    fontWeight: 600
    lineHeight: 1.4
    letterSpacing: "0"
  price:
    fontFamily: "\"Plus Jakarta Sans\", ui-sans-serif, system-ui, sans-serif"
    fontSize: "19px"
    fontWeight: 700
    lineHeight: 1.2
    fontFeature: "\"tnum\" 1"
rounded:
  sm: "6px"
  md: "9px"
  lg: "13px"
  full: "999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "16px"
  lg: "24px"
  xl: "40px"
components:
  button-primary:
    backgroundColor: "{colors.petrol-deep}"
    textColor: "{colors.surface}"
    rounded: "{rounded.md}"
    padding: "10px 18px"
  button-primary-hover:
    backgroundColor: "{colors.petrol-hover}"
  button-secondary:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
    padding: "10px 18px"
  button-ghost:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink-muted}"
    rounded: "{rounded.sm}"
    padding: "6px 10px"
  input-search:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
    height: "44px"
  chip-selected:
    backgroundColor: "{colors.petrol-tint}"
    textColor: "{colors.petrol-tint-ink}"
    rounded: "{rounded.sm}"
    padding: "8px 14px"
  chip-unselected:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink-muted}"
    rounded: "{rounded.sm}"
    padding: "8px 14px"
  card-product:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.lg}"
    padding: "16px"
  card-product-hover:
    backgroundColor: "{colors.surface}"
  badge-savings:
    backgroundColor: "{colors.savings-tint}"
    textColor: "{colors.savings-green}"
    rounded: "{rounded.sm}"
    padding: "4px 8px"
  nav-bar:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    height: "56px"
  nav-bar-desktop:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    height: "64px"
---

<!-- Target visual system (v2). This file is the spec the redesign implements. -->

# Design System: Ópticas Chile

## Overview

**Creative North Star: "The Counter"**

Every price is stated out loud. The reference is the shop counter — the place in a Chilean óptica where you point at a frame and ask "¿cuánto cuesta esto?" and get a straight answer. Not a showroom, not a catalog, not a feed. A counter: flat, well-lit, everything visible, nothing performed.

That metaphor decides the hard things. A counter has no frosted glass, no atmospheric lighting, no floating panels — it has a surface, a hairline between the surface and the wall behind it, and objects placed on it. It is legible before it is pretty. It treats the person across from it as someone who wants a number, not an experience.

The system is flat by default. Depth is not expressed with ambient shadows scattered across a page; it is expressed with a 1px hairline and a change of surface tone. Shadows appear only when something genuinely floats above the page — a popover, a modal, a dragged sheet — because that is the only situation where a shadow carries information. The current build has six `backdrop-blur` layers and eleven elevation levels on one screen; this system has two shadow tokens.

The accent is a deep petrol teal, deliberately not the blue-500 that shadcn hands you and not the violet that a generated landing page reaches for. Petrol reads technical and calm without reading institutional, and it survives being used at 10% coverage without shouting. Warmth is carried by the semantic savings green and by the copy, never by tinting the background cream — the canvas is a cool near-white that recedes, so the data is the only thing with color on screen.

Density is a feature of this product. The user is comparing prices, and price comparison is a scanning task. Type is one family at a tight 1.2 ratio, tables and lists are allowed to run dense, and marketing sections were removed rather than restyled. There is exactly one hero, it is the search field, and it does the work of a hero by being the first thing that answers the question.

**Key Characteristics:**
- Flat surfaces, hairline separation, two shadow tokens used only for true overlays.
- One type family, sentence case throughout — no uppercase eyebrows, no display font, no monospace for brand names.
- One accent (petrol teal) at ≤10% coverage, plus semantic green / amber / red reserved strictly for savings, warnings, and errors.
- Color never carries meaning alone: category is icon + text, savings is number + label + color.
- Mobile-first geometry: 44px targets, 16px minimum body text, bottom sheets for anything that would be a dropdown on desktop.

## Colors

A cool-neutral canvas with pure-white surfaces, one petrol-teal accent, and a tightly scoped semantic set. Nothing is tinted warm.

### Primary
- **Petrol Deep** (`oklch(0.470 0.082 200)`): primary actions, selected filter state, focus rings, links. The only chromatic color allowed on screen at any size.
- **Petrol Hover** (`oklch(0.420 0.078 200)`): pressed/hover state for primary actions. A 5% darkening, never a glow.
- **Petrol Tint** (`oklch(0.955 0.022 200)`): background of a selected chip or active filter. Petrol Tint Ink (`oklch(0.360 0.065 200)`) is its text color, 5.9:1 on the tint.

### Secondary
- **Savings Green** (`oklch(0.460 0.100 155)`): discount badges, "ahorrás" figures, in-stock confirmation. On Savings Tint (`oklch(0.955 0.030 155)`), 5.5:1.
- **Alert Amber** (`oklch(0.500 0.115 65)`): low-stock, stale-price warning, price-rise notice. On Alert Tint (`oklch(0.960 0.032 75)`).
- **Fault Red** (`oklch(0.500 0.170 25)`): fetch failure, destructive confirm. On Fault Tint (`oklch(0.960 0.026 25)`). In the dark theme it is raised to `oklch(0.740 0.145 25)` — the dark Fault Tint is dark enough that the light-theme value only reached 4.14:1.

### Neutral
- **Canvas** (`oklch(0.970 0.005 235)`): the page. Cool near-white, L 0.970 with chroma 0.005 — a faint blue cast, categorically outside the cream/sand band.
- **Surface** (`oklch(1 0 0)`): cards, panels, the header, the sheet.
- **Surface Sunken** (`oklch(0.945 0.006 235)`): image wells, table header rows, skeletons, inactive track.
- **Ink** (`oklch(0.235 0.016 250)`): body text, headings. 14.8:1 on Canvas.
- **Ink Muted** (`oklch(0.480 0.014 250)`): secondary text, labels, helper copy. 8.1:1 on Canvas — it reads softer than Ink but still passes AA for body copy. Never push muted grays lighter than this.
- **Ink Subtle** (`oklch(0.540 0.012 250)`): a de-emphasised ink that still clears AA — 4.66:1 on Canvas, 5.06:1 on Surface. It is for secondary *figures* (a struck-through previous price, a secondary metric), never for running prose. In the dark theme it is `oklch(0.640 0.012 245)` — 5.09:1 on Surface.
- **Hairline** (`oklch(0.892 0.006 235)`): default borders, dividers, input strokes.
- **Hairline Strong** (`oklch(0.820 0.008 235)`): hovered card borders, active input borders.

### Named Rules

**The One Voice Rule.** Petrol appears on no more than 10% of any screen. Its scarcity is the point — when the selected chip and the primary button are the only petrol things on the page, the eye goes straight to what is actionable.

**The One Theme Rule.** Light is the default. Dark is selected by `@media (prefers-color-scheme: dark)` applied to `:root:not(.light)`, and can be forced with a `.dark` class on `<html>`. **The `dark:` Tailwind variant is not used anywhere** — `darkMode: ["class"]` is configured but no element ever receives `.dark`, so a `dark:` utility would be dead code that hardcodes the old palette. Every colour resolves through a semantic token that carries both schemes. Do not reintroduce `dark:` utilities.

**The No-Chroma Rule.** Product category is never encoded by hue. The current build assigns eight different Tailwind colors to eight category and discount states; in this system category is carried by icon plus label, and discount by number plus label plus green. A user who cannot distinguish the hues loses nothing. The one deliberate exception is the **per-store dot** on the store badge: a retailer's identity colour is useful when the task is "show me only Karún", and it is confined to a 6px dot that never becomes a text colour or a background.

**The No-Warm-Background Rule.** The canvas is cool. Do not introduce cream, sand, bone, linen, parchment, or any tint in the hue 40–100 band at low chroma. Warmth in this product comes from the copy and from the savings green, never from the substrate.

## Typography

**Display Font:** Plus Jakarta Sans (with `ui-sans-serif, system-ui, sans-serif` fallback)
**Body Font:** Plus Jakarta Sans (same stack)
**Label/Mono Font:** none

**Character:** One humanist sans for everything. It is warm enough to feel approachable and geometric enough to stay precise at 12px, which is what a price index needs — a face that survives being read, not one that performs in a hero. There is no mono family and no display family: the current build uses JetBrains Mono for the brand name and 9px uppercase labels, and Syne for the headline, which is what makes it read as a developer tool rather than an optical index. Aligned price columns come from `font-variant-numeric: tabular-nums`, which is a feature of the family rather than a second typeface.

The family is self-hosted as woff2 (`/fonts/`) with `font-display: swap`, preloaded at weights 400, 600, and 700. No third-party font stylesheet in the critical path.

### Hierarchy
- **Display** (700, 30px mobile / 38px ≥640px / 44px ≥1024px, 1.15, -0.02em): the page `<h1>` only. One per page. `text-wrap: balance`.
- **Headline** (700, 22px / 26px ≥640px, 1.25, -0.015em): section headings and the dialog title.
- **Title** (600, 16px, 1.35): card titles, chain names, the price label.
- **Body** (400, 15px, 1.6): prose. Max 70ch. The product description paragraph and the "cómo funciona" text.
- **Body Small** (400, 13.5px, 1.55): helper text, metadata rows, timestamps.
- **Label** (600, 13px, 0 letter-spacing): control labels, chip text, table headers.
- **Price** (700, 19px on card / 24px in the detail header, 1.2, `tnum`): every monetary figure. Tabular figures so columns align and a discount is readable as a subtraction.

### Named Rules

**The Sentence Case Rule.** No text in this product is set in all caps with wide tracking. Eyebrows, kickers, section markers, and the brand wordmark are set in sentence case at normal tracking. Uppercase is reserved for the literal string `CLP` and the currency prefix when it must precede a number.

**The One Family Rule.** No second typeface is introduced for hierarchy, labels, prices, or numerals. Hierarchy comes from weight, size, and color — never from a font switch.

## Layout

**Grid.** A single centered column, max 1200px, with 20px gutters at ≤640px, 24px at ≥640px, 32px at ≥1024px. Content above the fold is one column at every width; side-by-side layouts are an enhancement, never the base.

**Page anatomy, in order:**

1. **Header** — sticky, 56px tall on mobile and 64px on ≥640px. Brand mark (glasses glyph inside a filled rounded square, ink on surface) plus the wordmark "Ópticas Chile" in sentence case at 600 weight. On ≥1024px: inline nav links (Catálogo · Cómo funciona · Fuentes) and a live-status pill reading "7 ópticas · en vivo" with a pulsing dot. Below 1024px: a 44px menu button that opens a full-width panel below the header. The header has a hairline bottom border and an opaque surface — never a blur.
2. **Search surface** (the hero) — the `<h1>`, one line of plain subtext, the search field, and the category chips, fused into a single unit. Left-aligned at every width; on mobile the heading, subtext, and field stack. No stat row, no floating pill, no secondary CTA.
3. **Results toolbar** — a single row: the live result count as plain text ("184 lentes en 7 ópticas"), the sort select, an in-stock toggle, a "Filtros" button, and a refresh button. On mobile the toolbar wraps to two rows and "Filtros" opens a bottom sheet; at ≥1024px the filter panel is inline beside the grid — so **the "Filtros" button exists only below 1024px**, where the sheet is the only route to the filters. It is not shown at ≥1024px, where the panel is already on screen.
4. **Results grid** — `repeat(1, 1fr)` at base, 2 columns ≥640px, 3 ≥1024px, 4 ≥1280px. Cards use `minmax(0, 1fr)` so long product names cannot blow out the track.
5. **Cómo funciona** — one short prose paragraph and the seven chain names as a text list. Not cards, not numbered steps.
6. **Footer** — brand mark and wordmark, one line ("Comparador independiente de precios de armazones y lentes en Chile."), the independence disclaimer, and the year. **The seven chain names and the last-update timestamp are NOT in the footer** — the chain list lives in the "Fuentes" section, where it can be linked from the navigation, and the live timestamp belongs to the results toolbar, which owns the live data.
7. **Asesor IA** — a fixed trigger at the bottom right; on mobile it becomes a bottom sheet occupying the full viewport height, on desktop a 400px right-hand panel.

**Density.** Product cards are information-dense by design: image well, brand, model, chain, price, discount, and a history affordance all fit in one card without scrolling. The results grid is the densest region of the product and is allowed to be dense.

**Breakpoints.** `sm` 640px, `md` 768px, `lg` 1024px, `xl` 1280px. Mobile styles are the base; every `min-width` query adds capability. There are no `max-width` overrides except where a desktop-only affordance must be removed.

**Safe areas.** The viewport meta carries `viewport-fit=cover`. The sticky header gets `padding-top: env(safe-area-inset-top)`; the chat trigger and any bottom sheet get `padding-bottom: env(safe-area-inset-bottom)` via `max(16px, env(safe-area-inset-bottom))`.

## Elevation & Depth

**Flat by default.** The system expresses hierarchy with a 1px hairline and a two-step surface scale (Canvas → Surface, plus Surface Sunken for wells). There is no ambient shadow on cards, no glow on buttons, and no backdrop blur anywhere in the product. Cards sit on the canvas with a hairline; the only elevation is on surfaces that genuinely float.

### Shadow Vocabulary
- **Overlay** (`0 1px 2px oklch(0.20 0.02 250 / 0.06), 0 8px 24px -8px oklch(0.20 0.02 250 / 0.14)`): popovers, dropdowns, the desktop advisor panel, the mobile sheet handle.
- **Modal** (`0 24px 48px -12px oklch(0.20 0.02 250 / 0.25)`): the price-history dialog and its scrim only.

### Named Rules

**The Flat-By-Default Rule.** A surface is flat at rest. A shadow appears only when an element is detached from the page flow — popover, dialog, dragged sheet — never as ambient decoration on a resting card or button.

**The No Blur Rule.** `backdrop-filter` is prohibited in product surfaces. Frosted glass is decoration that costs a paint pass and reads as generated. The current build blurs the header, the stats bar, the tab strip, the search panel, the product cards, and the chat trigger — six layers, zero information.

## Shapes

**Corner language.** Tight and consistent: 6px on chips and badges, 9px on buttons, inputs, and selects, 13px on cards and panels, 18px on dialogs and sheets. Fully round (`999px`) is reserved for things that are genuinely a pill or a dot: the live-status indicator, the discount pill, the avatar circle.

The current `--radius: 0.85rem` (13.6px) combined with `rounded-xl` / `rounded-2xl` / `rounded-3xl` on nearly every element produces the blobby, over-softened look. This system uses one radius per element class, and the value steps down as elements get smaller.

**Borders.** 1px hairline everywhere. Borders are the primary separation mechanism; a second background color is not needed to separate two levels of surface. Interactive elements that gain emphasis on hover change border color to Hairline Strong rather than growing a shadow.

**Clipping.** Product image wells are square-cornered inside the card (radius 9px) rather than bleeding to the card edge, so the image reads as an object placed on a surface rather than a photo card.

## Components

### Buttons
- **Shape:** 9px radius, 1px border, 40px tall on pointer-fine devices and 44px on coarse pointers.
- **Primary:** solid Petrol Deep with white text, no shadow. Padding 10px/18px. On hover, background moves to Petrol Hover. On active, 2% darker.
- **Secondary:** Surface background, Hairline border, Ink text. On hover, border becomes Hairline Strong.
- **Ghost:** transparent, Ink Muted text, no border. Used for icon-only affordances (refresh, close).
- **Focus:** 2px solid Petrol ring at 2px offset, on every variant, always visible against both the button and the canvas.
- **Loading:** the label is replaced by a 14px spinner and the button is disabled; the width does not change.

### Chips (if used)
- **Style:** 6px radius, 1px border, 13px/600 label, 8px/14px padding.
- **Selected:** Petrol Tint background, Petrol Tint Ink text, Petrol border at 40% alpha.
- **Unselected:** Surface background, Hairline border, Ink Muted text.
- **Category chips:** always icon + text label. The icon is 16px, monochrome, inheriting the text color. Never color-coded per category.

### Cards / Containers
- **Corner Style:** 13px radius.
- **Background:** Surface.
- **Shadow Strategy:** none at rest (see Elevation & Depth). On pointer-fine hover only, the border becomes Hairline Strong and the Overlay shadow appears.
- **Border:** 1px Hairline.
- **Internal Padding:** 16px, 20px at ≥640px.

### Product Card
- **Shape:** 13px radius, 1px Hairline border, Surface background, overflow hidden.
- **Image well:** 4:3 ratio, **pure white in both themes** (`bg-white`) with a 1px inset hairline, 9px radius, inset 12px from the card edge, centered object, no blur. The white backdrop is a deliberate exception to the Surface-Sunken rule: the product photography is transparent PNGs of frames, and they read muddy on a tinted well. A missing image shows a 16px monochrome glasses glyph at 40% opacity, not a shimmer.
- **Content:** chain name and discount badge on one row; brand and model; chain price in Price type with the struck-through previous price in Ink Subtle; a "ver historial" affordance.
- **Discount and savings are complementary, never duplicated.** The badge carries the **rate** (`-35%`); the savings line carries the **amount** ("Ahorrás $12.990"). Showing the same figure twice is noise.
- **Savings line:** when the same product is cheaper at another chain, a Savings Green line states the amount in words — "En Karün cuesta $12.900 menos" — never a bare percentage.
- **States:** hover lifts the border on pointer-fine only. Focus-visible rings the whole card.

### Inputs / Fields
- **Style:** 1px Hairline border, Surface background, 9px radius, 44px minimum height, 15px text, 16px on coarse pointers to prevent iOS zoom on focus.
- **Focus:** border becomes Petrol, plus a 3px Petrol Tint ring. The label floats as a real `<label>` above the field — no placeholder-as-label.
- **Error:** 1px Fault Red border, an error message below the field, and `aria-invalid` on the input.
- **Placeholder:** Ink Subtle, but never the only label.

### Navigation
- **Style:** opaque Surface, 1px Hairline bottom border, no blur. 56px tall on mobile, 64px from 640px.
- **Brand:** 32px filled rounded square containing the glasses glyph in Paper, followed by "Ópticas Chile" in sentence case at 600 weight, 15px. Not uppercase, not monospace, not tracked out.
- **Links:** 13px/600, Ink Muted, becoming Ink on hover. Active link carries a 2px Petrol underline.
- **Live status:** a 6px dot in Savings Green with a slow pulse plus the text "7 ópticas · en vivo" at 12px in Ink Muted. The dot carries a text equivalent.
- **Mobile:** a 44×44 menu button. Tapping it opens a full-width panel beneath the header containing the same links at 44px rows, and locks background scroll.

### Price history dialog
- **Shape:** 18px radius, Surface, Overlay → Modal shadow. Desktop panel caps at 560px wide (the shared `Dialog` primitive's `sm:max-w-[560px]`); the chart scales to it.
- **Content:** the product name, the current price, and the price series. The series is drawn in Petrol with the current point marked. **Every label lives in HTML around the SVG, never inside it** — text inside a scaled viewBox becomes unreadable on a phone. The chart container is a well (`bg-surface-sunken`), taller on mobile (`aspect-[4/3]`) than on desktop (`sm:aspect-[21/9]`). The chart viewport is measured with a `ResizeObserver` so the series never distorts.
- **Interaction:** pointer events only (`onPointerMove` + `onPointerDown`), so mouse, touch and pen all produce a readout. The SVG carries `role="img"` with a summary `aria-label`, and the underlying points are exposed in an `sr-only` table.
- **Mobile:** full-screen sheet, not a centered box with margins.
- **Known redundancy:** the minimum and maximum appear twice — once in the top readout and once in the row below the chart. Both were required by the implementation brief; dropping them from the top readout is a one-line change if it reads as noise in review.

### Advisor panel
- **Trigger:** a 52×52 circular button, Surface background, 1px border, Ink glyph, fixed to the bottom right at 16px plus the safe-area inset.
- **Panel:** on mobile, a bottom sheet at full viewport height with a handle bar, `role="dialog"`, `aria-modal`, focus trap, and Escape to close. On desktop, a **420px** right-hand panel.
- **Feed:** `aria-live="polite"`; user and assistant messages are visually distinct by alignment and a subtle tonal difference, not by color alone.

## Do's and Don'ts

### Do:
- **Do** set mobile styles as the base and add capability with `min-width` queries. Design at 360px first.
- **Do** use `font-variant-numeric: tabular-nums` on every price so columns align.
- **Do** keep every interactive element at 44×44 CSS px on coarse pointers, with visible space between adjacent targets.
- **Do** use a real `<label>` for every input and `aria-pressed` / `aria-selected` on every toggle chip.
- **Do** state the real number: live counts, chain names, actual savings amounts, and the last-update timestamp.
- **Do** keep the accent under 10% coverage of any screen.
- **Do** respect `prefers-reduced-motion: reduce` on every transition and animation, and never gate content visibility on an entrance animation.
- **Do** show the category as icon plus text, and the discount as number plus label plus color.
- **Do** give every price, savings figure, and helper string at least 4.5:1 contrast against its own background.

### Don't:
- **Don't** use `backdrop-filter` anywhere in a product surface.
- **Don't** put an uppercase tracked label above a heading, or number sections `01 / 02 / 03`.
- **Don't** build a grid of identical icon-plus-heading-plus-paragraph cards.
- **Don't** use a display font for the headline, or a monospace font for the brand name or for labels.
- **Don't** assign a different hue per product category or per discount state.
- **Don't** add a shadow to a resting card or button.
- **Don't** render a skeleton that is shaped like a stat when no real stat exists.
- **Don't** use a gradient for emphasis, and never for text.
- **Don't** use `transition-all`; name the properties that change.
- **Don't** hide or shrink a core function on mobile. If it matters, make it work at 360px.
- **Don't** scale desktop layouts down. Rethink the mobile layout on its own terms.

### Ratified deviations
- **Token naming.** The canonical token names are the shadcn-style ones (`primary`, `card`, `muted-foreground`, `border`, `accent`, `success`, `warning`, `destructive`); the descriptive names in the frontmatter (`petrol-deep`, `surface`, `ink`, …) are aliases for the same variables, not separate ones.
- **Petrol hover / active are real tokens** (`--primary-hover`, `--primary-active`), not alpha fades of `--primary`.
- **Ink subtle** exists as `--ink-subtle`; **`--on-white`** is a theme-independent ink for content that sits on the always-white product well.
- **The product image well is pure white in both themes**, not Surface Sunken — the deliberate exception, because the product photography is transparent PNGs. Its missing-image label therefore uses `--on-white`, and the well's ring is the theme-aware `--well-ring`.
- **The per-store dot keeps one hue per chain**, but the hues are tokenised CSS variables (`--store-gmo`, `--store-vendome`, `--store-rk`, `--store-schilling`, `--store-econopticas`, `--store-karun`, `--store-lentesplus`, `--store-unknown`) at a mid lightness, so a single value works on both canvases.
- **The results grid is** 1 column → 2 at ≥640px → 3 at ≥1024px → 4 at ≥1280px.
- **The footer carries** the brand, one line, the independence disclaimer and the year; the chain list lives in the "Fuentes" section and the live timestamp belongs to the results toolbar.
- **The product card is not focusable as a whole** — it is not interactive. Its two actions are, and each carries a focus ring.
- **The discount badge shows the rate** (`-40%`) and the savings line shows the amount (`Ahorrás $12.990`); they never repeat each other.
- **Token declarations are unlayered CSS**, because Tailwind v3.4 drops non-`:root` class rules inside `@layer base`.
