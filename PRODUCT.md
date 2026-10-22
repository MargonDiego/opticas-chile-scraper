# Product

## Register

product

## Users

People in Chile who are about to buy eyewear — frames, prescription lenses, or contact lenses — and want to know whether the price they were quoted is fair.

Their situation is specific and usually physical:

- They are on their phone, often standing in or near an optical shop, or at home in the evening with a browser tab open beside a quote.
- They do not know the market. A quoted price for a mid-range frame might be normal or might be double.
- They are price-aware and mildly skeptical. They have been quoted before and could not tell.
- They are not a professional buyer. Optics vocabulary ("esferoftalmia", "fotocromático", "índice de refracción") is not a shared language with them.
- Most arrive on a phone with a mediocre connection and a short attention span. The desktop site is the secondary case.

The primary task is: **find out what this product should cost, and where to get it cheaper.**

Success for them looks like: recognizing the discount or the absence of one, in under a minute, without reading instructions.

## Product Purpose

Ópticas Chile is an independent, automated price index for eyewear sold in Chile. It scrapes real listings from seven optical chains — GMO, Rotter & Krauss, Schilling, Place Vendôme, Econópticas, Karün, and Lentesplus — and exposes them as a searchable catalog with per-store pricing, discount history, and price history.

It exists because optical pricing in Chile is opaque. The same frame carries a wildly different price depending on where you buy it, and there was no way to check. The index makes the spread visible.

What success looks like for the product:

- A visitor recognizes their model and sees the price range across chains within one screen.
- The savings figure ("you could pay X less at another chain") is visible without clicking.
- The advisor chat answers practical questions in plain language ("¿me conviene polarizado si conduzco de noche?") instead of product-catalog questions.

The site is not a store. It does not sell anything. Its value is credibility and legibility: the user should trust the number more than the salesperson's number.

## Brand Personality

**Cercano, ágil, humano.**

- *Cercano* — warm and plain-spoken, in Chilean Spanish. It talks to the user like a knowledgeable friend, not like a retailer with a script. No "empodera", no "soluciones integrales", no exclamation marks selling something.
- *Ágil* — fast to read, fast to scan, fast to act. The user is on a phone comparing prices; the interface should get out of the way of that comparison.
- *Humano* — it acknowledges that buying eyewear is a slightly stressful, personal decision, and it respects the user's intelligence enough to show them the raw data.

Emotional goal: **confidence**, the feeling of "ok, now I know what to pay."

Not the goal: excitement. This is not a store; delight at the wrong moment is noise.

## Anti-references

These are specific failure modes to design against, not general vagueness.

1. **Inter or Poppins on a warm cream background with soft shadows everywhere.** The default AI-generated landing look. The current app already avoids this on fonts, but its `dark` theme and neon accents land in the same "generated" register from the opposite direction.
2. **A repeated grid of identical "icon + heading + paragraph" cards.** Three or four of the same shape, same size, same icon treatment, used to fill space.
3. **An uppercase tracked eyebrow label above every section heading, and `01 / 02 / 03` numbered section markers used as scaffolding.** The current app does this in the navbar ("MONITOR DE PRECIOS & CATÁLOGO EN VIVO" in 9px mono uppercase) and in the filter bar ("AHORRO:", "CONSULTANDO CATÁLOGO EN VIVO...").
4. **A rainbow of hardcoded Tailwind hues.** The current product cards use emerald, indigo, amber, cyan, purple, teal, rose, and blue for category and discount signalling, on top of a blue-500 primary. Eight accents with no system is noise, not information.
5. **Glassmorphism as decoration.** `backdrop-blur` on the navbar, the stats bar, the tab strip, the search panel, the product cards, and the chat FAB — six blurs on one page, none of them carrying information.
6. **A hero that is a marketing banner sitting above the actual tool.** The current hero is a centered `<h2>` plus a paragraph, with no `<h1>` anywhere on the site, and the search surface starts in a separate section below.

## Design Principles

1. **Data before decoration.** Every pixel that does not help someone compare prices gets removed. If an element is decoration, it is decoration that came from a template.
2. **Show the real number, or show nothing.** Live counts, real chain names, actual savings. Never a skeleton bar dressed as a stat, never a placeholder that looks like data. A number that is still loading says so honestly.
3. **One task per screen.** Search and comparison are the product. The brand chrome introduces itself once and then gets out of the way.
4. **Plain Chilean Spanish, no jargon.** If a word would need explaining, it is the wrong word. "Ahorrás" over "ahorro estimado"; "ópticas" over "establecimientos".
5. **The phone is the primary device.** Designed at 360px first and enhanced upward. The user is in a shop with one hand on the phone.
6. **Consistency is a feature.** The same control looks and behaves the same everywhere in the product. If the "Buscar" button differs from the "Actualizar" button, one of them is wrong.

## Accessibility & Inclusion

Target: **WCAG 2.1 AA** as a floor, not a goal.

- Body text and labels reach at least 4.5:1 contrast against their background; large text and UI borders at least 3:1. Muted grays are the failure point here — they get pushed toward the ink end of the ramp until they pass.
- Every interactive element has a visible focus indicator with sufficient contrast against both the element and the page background.
- Every touch target is at least 44×44 CSS pixels, with space between adjacent targets.
- All motion respects `prefers-reduced-motion: reduce`. Nothing depends on an entrance animation to become visible.
- No information is carried by color alone. Product category is encoded by icon *and* text label, never by hue. Savings are shown as a number *and* a color.
- The layout reflows to 320px without horizontal scrolling, and respects `env(safe-area-inset-*)` on notched devices.
- Spanish copy is written for Chile specifically. Terms are checked against local usage, not machine translation.
