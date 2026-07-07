---

# Phase 2, Task 3 (Revised): DaisyUI Semantic Class Migration + Theme Integration

## Goal

Convert all hardcoded Tailwind color classes to DaisyUI semantic classes across the frontend. Enable 4 themes (`light`, `dark`, `caramellatte`, `forest`) via the settings panel. This replaces the previous DaisyUI brief — that one failed because components used hardcoded colors that don't respond to `data-theme`.

## Why This Approach

DaisyUI themes work by injecting CSS variables that semantic classes (`bg-base-100`, `text-primary`, etc.) read from. Hardcoded classes (`bg-white`, `text-gray-900`) never read these variables, so they never change. The fix is mechanical: swap hardcoded classes for semantic equivalents, component by component.

**Scope boundary:** This task changes **color utility classes only**. Do not change component structure, do not adopt DaisyUI component classes (`btn`, `card`, `modal`, etc.), do not touch layout/spacing/flex classes. Markup and behavior stay identical — only colors become theme-aware.

---

## Reference Material

- DaisyUI color system: https://daisyui.com/docs/colors/
- DaisyUI theme list & names: https://daisyui.com/docs/themes/
- Tailwind dark mode config (to be removed): https://tailwindcss.com/docs/dark-mode

---

## Step 1 — Install & Configure DaisyUI

```bash
cd frontend && npm install -D daisyui@latest
```

`tailwind.config.js`:

```js
module.exports = {
  // ... existing content/theme config
  plugins: [require("daisyui")],
  daisyui: {
    themes: ["light", "dark", "caramellatte", "forest"],
  },
}
```

**Remove** any existing `darkMode: 'class'` config line if present — DaisyUI's `data-theme` attribute replaces Tailwind's class-based dark mode entirely.

---

## Step 2 — Semantic Class Reference

DaisyUI provides these semantic color tokens. Each has a matching `-content` variant for text/icons placed on top of that color.

| Token | Use for |
|---|---|
| `base-100` | Main page/card background (lightest surface) |
| `base-200` | Slightly recessed surface (e.g. input backgrounds, hover states) |
| `base-300` | Borders, dividers, more recessed surfaces |
| `base-content` | Default text color on base backgrounds |
| `primary` | Primary buttons, active states, links |
| `primary-content` | Text/icons on primary background |
| `secondary` | Secondary actions |
| `secondary-content` | Text/icons on secondary background |
| `accent` | Highlights, badges |
| `accent-content` | Text/icons on accent background |
| `neutral` | Neutral dark elements (e.g. footers, headers in some designs) |
| `neutral-content` | Text/icons on neutral background |
| `success` / `success-content` | Success states, confirmations |
| `warning` / `warning-content` | Warnings |
| `error` / `error-content` | Errors, destructive actions |
| `info` / `info-content` | Informational messages |

Usage pattern: `bg-{token}`, `text-{token}`, `border-{token}`. For muted/secondary text, use opacity modifiers: `text-base-content/60`, `text-base-content/70`.

---

## Step 3 — Migration Mapping Table

Use this as the default translation. Apply judgment where visual hierarchy matters (e.g. a card floating above the page background should be `base-100` if the page is `base-200`, not both the same).

| Hardcoded (before) | Semantic (after) |
|---|---|
| `bg-white` | `bg-base-100` |
| `bg-gray-50`, `bg-gray-100` | `bg-base-200` |
| `bg-gray-200`, `bg-gray-300` | `bg-base-300` |
| `bg-gray-800`, `bg-gray-900`, `bg-black` | `bg-neutral` (or `bg-base-300` if it's meant to invert with theme, not stay dark — check visually) |
| `text-black`, `text-gray-900` | `text-base-content` |
| `text-gray-500`, `text-gray-600` | `text-base-content/60` |
| `text-gray-400` | `text-base-content/40` |
| `text-white` | `text-base-100` (if on dark bg) or `{color}-content` (if on a colored bg, e.g. `primary-content` on `bg-primary`) |
| `border-gray-200`, `border-gray-300` | `border-base-300` |
| `bg-blue-500`, `bg-blue-600` | `bg-primary` |
| `text-blue-500`, `text-blue-600` | `text-primary` |
| `bg-green-500`, `bg-green-600` | `bg-success` |
| `bg-red-500`, `bg-red-600` | `bg-error` |
| `bg-yellow-500` | `bg-warning` |
| `hover:bg-gray-100` | `hover:bg-base-200` |
| `dark:bg-gray-800 dark:text-white` (any `dark:` variant) | **Delete entirely.** Semantic classes already adapt per theme — no `dark:` prefix needed anywhere. |

**Critical rule:** any class starting with `dark:` should be deleted after its base class is migrated to a semantic token. If you find a `dark:` variant with no clear semantic equivalent, flag it — don't guess.

---

## Step 4 — Before/After Example

**Before** (hypothetical snippet from `ManualInputForm.tsx`):

```tsx
<div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
  <h3 className="text-gray-900 dark:text-white font-semibold">
    Üçlülerinizi girin veya doğru olanları seçin
  </h3>
  <p className="text-gray-500 dark:text-gray-400 text-sm">
    Her iki model de eksikse
  </p>
  <button className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded">
    Ekle
  </button>
</div>
```

**After:**

```tsx
<div className="bg-base-100 border border-base-300 rounded-lg p-4">
  <h3 className="text-base-content font-semibold">
    Üçlülerinizi girin veya doğru olanları seçin
  </h3>
  <p className="text-base-content/60 text-sm">
    Her iki model de eksikse
  </p>
  <button className="bg-primary hover:bg-primary/90 text-primary-content px-4 py-2 rounded">
    Ekle
  </button>
</div>
```

Note: structure, spacing, and layout classes (`rounded-lg`, `p-4`, `px-4 py-2`, `font-semibold`, `text-sm`) are untouched. Only color-related classes change.

---

## Step 5 — Process (Component by Component)

Do **not** attempt a global find-replace across the whole codebase in one pass — too risky. Instead:

1. **Grep first:** find every file containing hardcoded color classes:
   ```bash
   grep -rn "bg-white\|bg-gray-\|bg-black\|text-gray-\|text-white\|text-black\|border-gray-\|dark:" frontend/src --include="*.tsx"
   ```
2. **Process one component file at a time**, in this order (lowest risk to highest):
   - `SettingsPanel.tsx` (already newest, most consistent)
   - `AISuggestions.tsx`
   - `ManualInputForm.tsx`
   - `PhraseAnnotator.tsx`
   - `HelperAgentChatbox.tsx`
   - `ModelTripletColumn.tsx` (if exists)
   - `App.tsx` (header, layout, mode toggle — do this last, highest risk of breaking layout)
3. **After each file:** visually verify in the browser (light theme) before moving to the next file.
4. **Do not touch** `CustomCheckbox.tsx` or other components confirmed unused/dead — skip them, note them in the report.

---

## Step 6 — Theme Selector Implementation

### Apply theme to document root

In `App.tsx`:

```tsx
useEffect(() => {
  document.documentElement.setAttribute('data-theme', currentTheme);
}, [currentTheme]);
```

### Persist theme

- Add `theme` key to `CONFIG_DATA` in `main.py`, default `"light"`
- On settings load: read `settings.theme`, apply it
- On change: update local state, apply immediately, `PATCH /settings` with `{ theme: newValue }`

### Settings panel — new section

Add before `"1. Ek Açıklama"`:

**"0. Görünüm"**

| Setting | Type | Config key |
|---|---|---|
| Tema | Dropdown | `theme` |

| Turkish label | DaisyUI theme name |
|---|---|
| Açık | `light` |
| Koyu | `dark` |
| Karamel | `caramellatte` |
| Orman | `forest` |

### Remove old toggle

- Delete `DarkModeToggle.tsx` and all references (should already be unused per earlier audit — confirm)
- Remove any `darkMode` state / localStorage logic in `App.tsx`

### Update `types.ts`

Add `theme: string` to `Settings` interface.

---

## Constraints

- Color utility classes only — no structural, layout, or component-pattern changes
- No `dark:` prefixed classes should remain anywhere after this task
- Match existing spacing/sizing/typography exactly
- All UI text stays Turkish (no new user-facing strings introduced by this task except the theme dropdown labels)
- No backend changes beyond the `theme` config key

---

## Verification

1. Grep confirms zero remaining `dark:` classes: `grep -rn "dark:" frontend/src --include="*.tsx"` returns nothing
2. Grep confirms no hardcoded `bg-gray-`, `bg-white`, `text-gray-`, etc. remain (spot-check, not exhaustive — some may be intentionally decorative, flag those)
3. Switch through all 4 themes in the settings panel — every visible surface (backgrounds, text, borders, buttons) changes appropriately
4. No visual regression in light theme compared to pre-migration screenshots
5. Theme persists after page refresh
6. All existing functionality unaffected: Compare mode, Manual mode, AI suggestions, chat, settings save
7. `npm run build` completes with no errors

## Definition of Done

1. Zero `dark:` classes remain in the codebase
2. All 4 themes fully reskin the app (backgrounds, text, borders, buttons all respond)
3. Theme dropdown in settings panel, persists via `PATCH /settings`
4. No layout/structural regressions
5. Report listing: any component skipped, any class with no clear semantic mapping (flagged, not guessed), any visual difference introduced

---
