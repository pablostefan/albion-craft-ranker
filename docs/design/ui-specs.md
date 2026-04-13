# Albion Craft Ranker UI Specs

## 1. Purpose and Scope

This document defines the UI/UX specification for the Next.js 15 dashboard planned in Variant B of `crafting-economy`.

The UI must satisfy the PRD user stories for:

- ranking all craftable items by profitability
- making `return_rate_pct` the fastest metric to read
- comparing best city recommendations
- switching between Marketplace, Black Market, and Comparison modes
- filtering by category, tier, enchantment, city, and quality
- exposing item-level cost breakdowns without forcing CLI usage

Primary routes:

- `/` -> ranking dashboard
- `/items/[id]` -> item detail and city comparison

Out of scope for this spec:

- authentication
- personal saved presets
- notifications
- mobile-native patterns

## 2. Visual Theme

### Theme direction

Albion-themed dark strategy board: low-key metallic surfaces, parchment-like data panels, danger/profit accents inspired by city banners and Black Market contrast. The interface should feel tactical, not generic SaaS.

### Design principles

- Dense information layout without becoming visually flat
- `return_rate_pct` is the hero metric in every ranking row and in the detail summary
- Filters stay available but never dominate the table on small screens
- City and market context must be visible close to profit numbers, not hidden in tooltips
- Every state must remain readable under dark theme and high contrast conditions

### Recommended typography

- Display/headings: `Cinzel`, fallback `Georgia`, serif
- UI/body/numbers: `IBM Plex Sans`, fallback `Arial`, sans-serif
- Tabular metrics: `IBM Plex Mono`, fallback `Menlo`, monospace

### Color tokens

Use global theme tokens first in Tailwind config or app theme setup. Do not hardcode colors inside components.

| Token | Value | Usage |
|------|------|------|
| `--color-bg-canvas` | `#0d1117` | app background |
| `--color-bg-elevated` | `#151b23` | cards, sidebars, dialogs |
| `--color-bg-panel` | `#1a222d` | table header, sticky controls |
| `--color-bg-hover` | `#222d39` | hover states |
| `--color-border-muted` | `#304050` | default borders |
| `--color-border-strong` | `#4e6478` | focus ring support and active dividers |
| `--color-text-primary` | `#f4f1e8` | main text |
| `--color-text-secondary` | `#b7c0ca` | supporting copy |
| `--color-text-muted` | `#8b97a3` | tertiary labels |
| `--color-profit-strong` | `#4ddc8b` | positive `return_rate_pct`, profit badges |
| `--color-profit-soft` | `#163c2a` | positive row background chip |
| `--color-loss-strong` | `#ff6b6b` | negative margin states |
| `--color-loss-soft` | `#4a2024` | negative row background chip |
| `--color-accent-gold` | `#d8b25a` | selected city, premium controls, icons |
| `--color-accent-ember` | `#c96a2b` | comparison emphasis, Black Market accent |
| `--color-info` | `#6cb7ff` | freshness, hints, neutral delta |
| `--color-focus-ring` | `#f7d774` | keyboard focus outline |

### Elevation and surfaces

- Canvas uses a radial gradient from `#131a23` to `#090c11`
- Panels use 1px borders and soft inset highlight, not glassmorphism
- Main table header and filter sidebar remain visually heavier than content rows
- Hover states brighten borders before changing fill, to preserve contrast

## 3. Layout System and Breakpoints

### Breakpoints

| Label | Range | Layout intent |
|------|------|------|
| Mobile | `< 768px` | stacked flow, filter drawer, horizontal table scroll |
| Tablet | `768px - 1023px` | 2-row top control bar, collapsible sidebar, compact table |
| Desktop | `>= 1024px` | persistent left sidebar + main content grid |
| Wide | `>= 1440px` | expand ranking table density and detail comparison area |

### Max widths

- App shell max width: `1600px`
- Main content gutters: `16px` mobile, `24px` tablet, `32px` desktop
- Sidebar width: `320px` desktop, `288px` tablet drawer

### Responsive wireframes

#### Desktop wireframe

```text
+-----------------------------------------------------------------------------------+
| Header: logo | server selector | freshness badge | help                           |
+----------------------------+------------------------------------------------------+
| Filter Sidebar             | Top Controls                                         |
| - category                 | market toggle | sort info | active chips | refresh   |
| - tier                     +------------------------------------------------------+
| - enchantment              | Ranking Summary Strip                                |
| - city                     | best item | avg return | negative count | last sync  |
| - quality                  +------------------------------------------------------+
| - min profit               | Ranking Table                                        |
| - weights                  | rows with prominent return_rate_pct                  |
| - reset/apply              | sticky header, sortable columns, pagination          |
+----------------------------+------------------------------------------------------+
```

#### Tablet wireframe

```text
+--------------------------------------------------------------------+
| Header: logo | market toggle | filter button | refresh            |
+--------------------------------------------------------------------+
| Summary strip: avg return | best city spread | stale data count   |
+--------------------------------------------------------------------+
| Active filter chips                                               |
+--------------------------------------------------------------------+
| Ranking table with compact columns and horizontal scroll          |
| [drawer opens from left for filters + weights]                   |
+--------------------------------------------------------------------+
```

#### Mobile wireframe

```text
+--------------------------------------------------------------+
| Header: logo | filter button | market toggle icon           |
+--------------------------------------------------------------+
| Hero stat card: return_rate_pct focus + selected mode        |
+--------------------------------------------------------------+
| Active chips scroll row                                      |
+--------------------------------------------------------------+
| Cardified table rows or horizontally scrollable compact table|
| item + tier + city                                            |
| large return_rate_pct                                         |
| profit + focus + link to detail                               |
+--------------------------------------------------------------+
| Bottom sticky actions: filters | weights | refresh           |
+--------------------------------------------------------------+
```

## 4. Information Architecture

### Dashboard sections

1. Global header
2. Control row
3. Summary strip
4. Filter sidebar or drawer
5. Ranking table
6. Pagination or load-more footer

### Item detail sections

1. Back navigation preserving query params
2. Item overview card
3. Profit summary card with `return_rate_pct`
4. Cost breakdown table
5. Revenue breakdown card
6. City comparison chart/table
7. Related navigation: previous item, next item

## 5. Ranking Dashboard Specification

### Header

Content:

- app title `Albion Craft Ranker`
- server badge defaulting to `West`
- freshness indicator using stale/fetching/fresh/error states from the PRD state machine
- optional premium fee mode indicator if backend exposes it later

Behavior:

- on desktop, header is sticky with compact height
- on mobile, header shrinks and prioritizes filter access and market mode visibility

### Summary strip

Purpose: give orientation before the user scans rows.

Required metrics:

- best current `return_rate_pct`
- count of profitable items in current filter set
- current selected city mode (`Best city` or explicit city)
- stale-data warning count if backend returns freshness metadata

### Ranking table

Default sorting: `return_rate_pct desc`

Required columns:

| Column | Priority | Desktop | Tablet | Mobile | Notes |
|------|------|------|------|------|------|
| `rank` | high | yes | yes | optional badge | sticky first column |
| `item_name` | high | yes | yes | yes | include icon slot and click target |
| `tier` | high | yes | yes | yes | render as `T4`, `T5` etc. |
| `enchantment` | medium | yes | compact | badge in item cell | `@0` to `@3` |
| `return_rate_pct` | critical | yes | yes | yes | largest row text, color-coded |
| `profit` | high | yes | yes | yes | silver amount, signed |
| `best_city` | high | yes | yes | yes | explicit city label and bonus hint |
| `profit_per_focus` | medium | yes | compact | secondary line | only if focus cost > 0 |
| `focus_cost` | medium | yes | compact | secondary line | hidden when 0 |
| `liquidity` | medium | yes | compact | hidden | badge or sparkline-ready |
| `freshness` | medium | yes | hidden | hidden | age in hours or freshness badge |

Comparison mode adds paired revenue columns in a grouped header:

- `marketplace_profit`
- `black_market_profit`
- `delta`

The grouped header must not demote `return_rate_pct`. That metric remains visually primary even in comparison mode.

### `return_rate_pct` presentation rules

- Value uses tabular numerals and 18-20px equivalent on desktop rows
- Positive value chip uses `--color-profit-soft` background and `--color-profit-strong` text
- Negative values use `--color-loss-soft` background and `--color-loss-strong` text
- Zero or near-zero values use neutral info token
- Entire row receives a subtle left border accent aligned with the sign of `return_rate_pct`
- Items below 0% must also expose a text label for screen readers, for example `negative return rate`

### Row interaction

- Entire row is clickable except for explicit control elements
- Primary action opens `/items/[id]` preserving current URL search params
- Hover on desktop reveals a right chevron and stronger border
- Keyboard focus lands on row link wrapper with clear ring

### Table states

- Loading: 8 skeleton rows with fixed cell widths matching final layout
- Empty: explain that no items matched the current filter set and provide reset action
- Error: inline error panel with retry action and last successful sync time if available
- Stale: non-blocking amber banner above the table

## 6. Filter Sidebar Specification

### Structure

Order controls from fastest business decisions to advanced tuning:

1. market mode
2. category
3. tier
4. enchantment
5. city
6. quality
7. minimum profit
8. scoring weights
9. reset / apply

### Controls

| Control | Component | Behavior |
|------|------|------|
| Category | searchable select | supports `All` plus backend categories |
| Tier | segmented range or multi-select pills | default T4-T8 |
| Enchantment | segmented control `0 1 2 3` | single select |
| City | select | `Best city` first, then cities, then `Black Market eligible only` as future flag placeholder |
| Quality | select `1-5` with labels | default `1` |
| Min profit | numeric input | silver units |
| Weight config | collapsible group | advanced, hidden behind disclosure on mobile |

### Sidebar behavior

- Desktop: persistent left column with sticky internal scroll
- Tablet/mobile: opens as modal drawer with focus trap and dismiss button
- Mobile actions remain sticky at drawer bottom: `Reset`, `Apply`
- Active filters render as removable chips in the main content region after apply

## 7. Black Market Toggle Specification

### Modes

- `Marketplace`
- `Black Market`
- `Comparison`

### Interaction model

- Implement as accessible segmented control, one active option at a time
- Keyboard support: left/right arrows move between segments, `Enter` or `Space` activates
- Selected state must meet WCAG contrast even with accent colors
- The control updates URL search param `market`

### Behavior rules

- Default mode is `Marketplace`
- `Black Market` mode filters or annotates items that are not BM-eligible
- For non-eligible items, show `Not eligible` instead of blank values
- `Comparison` mode keeps a single row per item and displays both exit strategies side by side

## 8. Item Detail Page Specification

### Overview card

Fields:

- item name
- tier
- enchantment
- category
- recommended city
- selected market mode
- freshness badge

### Profit summary block

Layout priority:

1. `return_rate_pct`
2. `profit`
3. `profit_per_focus`
4. `focus_cost`

Presentation:

- `return_rate_pct` occupies the largest figure in the page hero
- show sign and percentage with one decimal at minimum
- companion caption explains formula: `profit / total_cost`

### Cost breakdown table

Required columns:

- material
- quantity
- unit price
- subtotal
- RRR applied
- effective quantity

Rules:

- artifact materials must explicitly show `No RRR`
- rows with returned resources should display the saved amount or effective reduction
- footer totals show gross material cost, RRR savings, effective craft cost

### Revenue breakdown card

Required rows:

- sell price
- setup fee `2.5%`
- sales tax `4%` or `8%`
- net revenue
- final profit

### City comparison

Preferred desktop layout: horizontal bar chart plus compact data table.

Required data per city:

- city name
- profit
- `return_rate_pct`
- RRR context
- Black Market relevance if applicable

Rules:

- best city receives star badge and stronger gold border
- negative-profit cities remain visible; do not hide losing options
- mobile collapses chart into stacked comparison cards or compact rows

## 9. Accessibility and WCAG 2.1 AA Requirements

### Visual contrast

- normal text contrast minimum `4.5:1`
- large text and metric numerals minimum `3:1`
- profit/loss color must never be the only signal; pair with label or iconography

### Keyboard navigation

- all filter controls reachable with keyboard only
- drawer modal traps focus when open
- table rows accessible as links, not `div` click handlers only
- segmented toggle follows roving tabindex or radio-group semantics

### Screen reader support

- icon-only buttons require `aria-label`
- summary cards need clear headings for quick navigation
- ranking table headers need proper `scope="col"`
- negative `return_rate_pct` rows expose status text like `loss-making item`

### Motion

- use short opacity and translate transitions only for panels and chips
- respect `prefers-reduced-motion: reduce`
- no essential information depends on animation

### Touch targets

- minimum `44x44px` for buttons, row affordances, drawer actions, segmented toggle options

## 10. State and Data Handling

### URL state

Persist at minimum:

- `market`
- `category`
- `tier`
- `enchantment`
- `city`
- `quality`
- `minProfit`
- `sortBy`
- `sortOrder`
- `weights`
- `page`

This is required so task 010 can navigate back to the ranking view without losing context.

### Data states expected from backend

Frontend tasks 008-010 should anticipate:

- loading
- partial data with stale warning
- empty result sets
- field-level absence such as `profit_per_focus = null`
- comparison payloads with both marketplace and black market values

### Ranking row badges

- `Best city`
- `BM eligible`
- `Stale`
- `Negative margin`

## 11. Validation Against PRD and Variant B

| Requirement source | UI response |
|------|------|
| Ranking by profitability | default sort by `return_rate_pct`, additional profit metrics available |
| Focus optimization | `profit_per_focus` and `focus_cost` shown in table and detail |
| Best city recommendation | explicit `best_city` column and city comparison module |
| Black Market comparison | 3-state segmented toggle with comparison layout |
| Margin visibility | `return_rate_pct` hero styling in list and detail |
| Beginner-friendly filters | visible sidebar with category, tier, enchantment, city, quality |
| Full dashboard web UI | responsive route design for desktop, tablet, mobile |
| Variant B task contract | component tree, wireframes, color scheme, breakpoints, accessibility documented |

## 12. Implementation Guidance for Frontend Tasks 008-010

### Task 008

- Build the theme through global tokens first in Tailwind or app theme config, then consume tokens in components.
- Keep the ranking table row height stable between loading and loaded states to avoid layout shift.
- Implement desktop table plus mobile compact-row renderer behind the same typed data contract.

### Task 009

- Use URL search params as the single source of truth for filters and market mode.
- Put `WeightConfig` behind a disclosure by default on tablet/mobile to avoid making the drawer too tall.
- In comparison mode, prefer grouped columns over doubling row count; doubling rows would destroy scanability.

### Task 010

- Preserve incoming search params in the back link and in prev/next navigation.
- Treat artifact materials as a first-class display condition, not a tooltip-only note.
- Build city comparison with a semantic table fallback even if a decorative bar chart is added.

## 13. Design Non-Negotiables

1. `return_rate_pct` remains the primary visible metric everywhere ranking decisions happen.
2. Black Market mode must read as an exit strategy switch, not a generic boolean filter.
3. Desktop keeps filters persistent; mobile keeps them one tap away.
4. Negative profitability must be obvious without relying on red color alone.
5. Every critical control and row action must be keyboard accessible.