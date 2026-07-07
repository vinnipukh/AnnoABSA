# Claude Skills Knowledge Summary

Extracted from frontend/.claude/skills/ for frontend work on AnnoABSA.

## 1. ui-styling — shadcn/ui + Tailwind Patterns

**Stack:** Vite + React 19 + Tailwind v3 (not v4) + DaisyUI v4 (not shadcn/ui).
AnnoABSA uses DaisyUI `data-theme` attr, not shadcn `class` dark mode.

**Key conventions for this project:**
- Theme classes: `bg-base-300`, `text-base-content`, `bg-primary`, `text-primary-content`, etc. — these are DaisyUI semantic classes.
- Tailwind is v3 (CommonJS config: `module.exports` with `require("daisyui")`).
- `index.css` has bare @tailwind directives — no CSS variable layers needed for DaisyUI themes.
- Dark mode: DaisyUI handles it via `data-theme="dark"` on `<html>`.

**Relevant patterns from skill (adapt for DaisyUI):**
- Component composition over monolithic components
- Utility-first: use Tailwind/DaisyUI classes directly
- Mobile-first: responsive with `sm:`, `md:`, `lg:` breakpoints
- 8dp spacing rhythm (Tailwind spacing is 4px base)
- Touch targets >= 44x44px

## 2. ui-ux-pro-max — Design Intelligence Reference

**Priority hierarchy (1=most critical):**
1. Accessibility (contrast 4.5:1, focus rings, aria-labels, keyboard nav)
2. Touch & Interaction (min 44×44px, 8px+ spacing, loading feedback)
3. Performance (lazy loading, no CLS, debounce/throttle)
4. Style Selection (consistency, SVG icons, no emojis as icons)
5. Layout & Responsive (mobile-first, no horizontal scroll, proper breakpoints)
6. Typography & Color (16px base, line-height 1.5, semantic tokens)
7. Animation (150-300ms, transform/opacity only, reduced-motion support)
8. Forms & Feedback (visible labels, error near fields, loading states)
9. Navigation (predictable back, bottom nav ≤5)
10. Charts & Data

**AnnoABSA-specific notes:**
- Uses `@phosphor-icons/react` — keep using this icon family
- No emojis as structural icons ever
- Dark/light mode both tested before delivery
- Toast auto-dismiss in 3-5s
- Disabled state: reduced opacity (0.38–0.5) + cursor change

## 3. design-system — Three-Layer Token Architecture

**Token layers (not used in AnnoABSA directly but good practice):**
- Primitive (raw values: `--color-blue-600: #2563EB`)
- Semantic (purpose: `--color-primary: var(--color-blue-600)`)
- Component (specific: `--button-bg: var(--color-primary)`)

**AnnoABSA relevance:**
- This project uses DaisyUI's built-in token system via `data-theme` + Tailwind semantic classes
- Not using CSS custom property layering
- Good practice: consistency in spacing, colors, and component states even without explicit tokens
- State table pattern (default → hover → active → disabled → focus) useful for component work

## Current Frontend Architecture

| File | Purpose |
|------|---------|
| `App.tsx` | Main SPA: header, compare/manual mode, AI suggestions, chat, footer, settings modal |
| `SettingsPanel.tsx` | Full settings modal with all config toggles/inputs |
| `AISuggestions.tsx` | AI prediction suggestion list with accept/reject |
| `DarkModeToggle.tsx` | Legacy dark mode toggle (not used — DaisyUI handles via settings.theme) |
| `ModelTripletColumn.tsx` | Model A/B triplet display with checkboxes |
| `ManualInputForm.tsx` | Manual triplet creation form |
| `PhraseAnnotator.tsx` | Inline phrase annotation component |
| `HelperAgentChatbox.tsx` | Floating chat box for agent Q&A |
| `types.ts` | All TypeScript interfaces |
| `tailwind.config.js` | Tailwind v3 + DaisyUI v4, themes: light, dark, caramellatte, forest, cupcake, abyss |

**Theme system:** DaisyUI `data-theme` attr on `<html>` — NOT shadcn dark mode.
**Icons:** Inline SVGs in buttons/header (no phosphor-icons imported yet in App.tsx).
