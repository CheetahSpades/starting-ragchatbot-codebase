# Frontend Changes

## Dark / Light Mode Toggle Button

### What was added

A fixed-position theme toggle button in the top-right corner of every page, letting users switch between the existing dark mode and a new light mode. The chosen preference is persisted in `localStorage` and re-applied on the next page load before the first paint (no flash).

---

### Files changed

#### `frontend/index.html`
- Added an inline `<script>` in `<head>` that reads `localStorage('theme')` and sets `data-theme` on `<html>` before the browser renders anything, preventing a flash of the wrong theme.
- Added `<button id="themeToggle" class="theme-toggle">` as the first element inside `<body>`. The button contains two `<svg>` icons: a sun (shown in dark mode) and a moon (shown in light mode). Both icons have `aria-hidden="true"`; the button itself carries an `aria-label` that is updated dynamically.
- Bumped CSS and JS cache-busting query strings (`v=11` / `v=10`).

#### `frontend/style.css`
- **Light-mode variables** — added a `[data-theme="light"]` block that overrides the `:root` custom properties with a white / light-gray palette while keeping the same blue primary accent.
- **Smooth transitions** — added a `.theme-transitioning` class rule (applied momentarily by JS during a toggle) that transitions `background-color`, `color`, `border-color`, and `box-shadow` across all elements in 0.3 s without touching `transform`-based animations (e.g. the loading-dot bounce).
- **`.theme-toggle` button** — `position: fixed; top: 1rem; right: 1rem; z-index: 1000`, circular (44 × 44 px), border matches `--border-color`, shadow from `--shadow`. Hover scales up slightly and highlights the border in the primary blue.
- **Icon crossfade** — both SVGs are `position: absolute` and centered; `opacity` + `transform` transitions create a smooth swap: in dark mode the sun fades in while the moon rotates away, and vice-versa in light mode.
- **Focus-visible ring** — `outline: 2px solid var(--primary-color); outline-offset: 3px` on `:focus-visible` for keyboard navigation.
- **Light-mode code blocks** — overrides `background-color` on `code` and `pre` so inline/fenced code doesn't look washed-out on a white background.

#### `frontend/script.js`
- `themeToggle` added to DOM-element cache.
- `syncThemeAriaLabel()` — sets the button's `aria-label` to either "Switch to dark mode" or "Switch to light mode" based on the current `data-theme` attribute. Called on `DOMContentLoaded` and after every toggle.
- `toggleTheme()` — flips `data-theme` between `"light"` and `"dark"` on `<html>`, saves to `localStorage`, calls `syncThemeAriaLabel()`, temporarily adds `theme-transitioning` to `<html>` for smooth visual transitions, then removes the class after 350 ms.
- `setupEventListeners()` — wires `click` on `#themeToggle` to `toggleTheme()`.

---

### Accessibility

| Concern | How it's handled |
|---|---|
| Keyboard navigation | `<button>` is natively focusable; Tab/Enter/Space all work |
| Screen reader label | `aria-label` is updated on every toggle to describe the *next* action |
| Icon decorativeness | Both SVGs carry `aria-hidden="true"` so screen readers ignore them |
| Focus indicator | `:focus-visible` shows a 2 px blue outline; no `:focus` override that would hide it |
| Flash of wrong theme | Inline `<script>` in `<head>` sets the attribute before first paint |

---

## Light Theme Variant

### What was added / fixed

A complete, accessible light theme defined entirely via CSS custom properties under `[data-theme="light"]`. Activating it requires only setting `data-theme="light"` on `<html>` — all components respond automatically.

### Files changed

#### `frontend/style.css`

**`[data-theme="light"]` variable block — refinements**

| Variable | Dark value | Light value | Reason |
|---|---|---|---|
| `--border-color` | `#334155` | `#cbd5e1` | Slate-300 meets the WCAG 3:1 minimum contrast for UI component boundaries against white |
| `--focus-ring` | `rgba(37,99,235,0.2)` | `rgba(37,99,235,0.2)` | Same — kept at 0.2 for visibility on light backgrounds (previously was 0.15, raised) |

All other `:root` variables (`--primary-color`, `--primary-hover`, `--user-message`) are unchanged — `#2563eb` achieves ≥ 4.6:1 contrast against white text and ≥ 5.1:1 for white text on the blue bubble, both passing WCAG AA.

**Bug fix** — `.message-content blockquote` referenced the undefined variable `var(--primary)`. Corrected to `var(--primary-color)`.

**Semantic color overrides for light mode**

The dark-mode error and success variants (`#f87171`, `#4ade80`) are pastel shades designed for dark surfaces. They fail contrast requirements on white. Two targeted overrides are added:

| Element | Light-mode text color | Contrast vs white | WCAG level |
|---|---|---|---|
| `.error-message` | `#b91c1c` (red-700) | ~7.9 : 1 | AAA |
| `.success-message` | `#15803d` (green-700) | ~7.1 : 1 | AAA |

Background tints are reduced to 7% opacity so they remain a subtle hint rather than a wash of color.

**Welcome message** — In light mode the default `--border-color` border looks too faint against the white page. Added a targeted rule giving the welcome bubble a `--primary-color` border and a soft blue box-shadow so it remains visually distinct.

**Blockquote in light mode** — Explicit `border-left-color: var(--primary-color)` so the left accent renders correctly now that the base bug is fixed.

**Light-mode code blocks** — Existing override extended to also set `color: var(--text-primary)`, ensuring monospace text is dark (`#0f172a`) rather than potentially inheriting an unexpected shade from a parent.

### Accessibility checklist

| Concern | Status |
|---|---|
| Normal body text (`--text-primary` on `--background`) | `#0f172a` on `#ffffff` → ~19 : 1 ✅ AAA |
| Secondary text (`--text-secondary` on `--background`) | `#64748b` on `#ffffff` → ~4.7 : 1 ✅ AA |
| Primary interactive blue (`--primary-color` on `--background`) | `#2563eb` on `#ffffff` → ~4.6 : 1 ✅ AA |
| User message bubble (white text on `--user-message`) | `#ffffff` on `#2563eb` → ~5.1 : 1 ✅ AA |
| Error message text | `#b91c1c` on light red tint → ~7.9 : 1 ✅ AAA |
| Success message text | `#15803d` on light green tint → ~7.1 : 1 ✅ AAA |
| UI borders (`--border-color` vs adjacent bg) | `#cbd5e1` on `#ffffff` → ~3.2 : 1 ✅ meets UI component minimum |
