---
name: docs-style
description: Design style guide for the Great Lakes Horizon Scan topic browser (docs/index.html). Use whenever building or extending any page in the docs/ site.
user-invocable: true
---

# Design Style Guide — Great Lakes Topic Browser

Follow these rules when building or modifying pages in `docs/`.

## Color Palette

| Role | Value |
|------|-------|
| Primary dark (U-M blue) | `#00274c` |
| Accent gold (U-M maize) | `#ffcb05` |
| Page background | `#f9f9f7` |
| Card / panel background | `#fff` |
| Border / divider | `#ddd` or `#e8e8e8` |
| Hover row tint | `#eef3f9` |
| Active row tint | `#dce8f5` |
| Keyword chip bg | `#edf2fa` |
| Keyword chip border | `#c5d5ea` |
| Keyword chip text | `#2a4a70` |

## Typography

- **Body font:** `Georgia, "Times New Roman", serif` at `15px`, `color: #111`, `line-height: 1.6`
- **Monospace font (meta, code, keywords):** `"Courier New", monospace`
- **Header `<h1>`:** `1.4rem`, bold, `letter-spacing: 0.01em`
- **Subheader subtitle:** `0.85rem`, `color: #ccd9e8`
- **Section headings (`.section`):** `1rem`, `color: #00274c`, bottom border `1px solid #ddd`
- **Table headers:** `0.8rem`, uppercase, `letter-spacing: 0.03em`, weight normal
- **Comment text:** `0.88rem`, `line-height: 1.65`, `color: #222`
- **Meta / secondary text:** `0.78–0.82rem`, `color: #666–#777`

## Layout

- `box-sizing: border-box`, no default margin/padding
- `.container`: `max-width: 1100px`, centered, `padding: 30px 40px`
- Full-width `<header>` with `background: #00274c`, `padding: 28px 40px 22px`, `border-bottom: 3px solid #ffcb05`

## Components

### Header
Dark blue background, white h1, muted subtitle (`#ccd9e8`), maize bottom border 3px.

### Data Table (`.topic-table`)
- `border-collapse: collapse`, `font-size: 0.9rem`, white background, `border: 1px solid #ddd`
- `<thead>`: dark blue bg, white text, uppercase small caps
- Row hover: `#eef3f9`; active row: `#dce8f5`; `cursor: pointer`; `transition: background 0.12s`
- Row borders: `1px solid #e8e8e8`; cell padding `9px 14px`

### Keyword Chips (`.kw`)
`inline-block`, bg `#edf2fa`, border `1px solid #c5d5ea`, `border-radius: 3px`, padding `1px 7px`, monospace font, `color: #2a4a70`.

### Detail Panel (`#detail`)
White card with `border: 1px solid #ddd`, hidden by default (`display: none`).
- Panel header: dark blue bg, white title, muted count text (`#aac4de`), close button that lightens on hover.
- Comment rows: `padding: 14px 18px`, `border-bottom: 1px solid #ebebeb`; last child has no border.

### Meta Bar
Monospace, `0.82rem`, `color: #666` — used for dataset stats / timestamps.

## Interaction

- Rows are clickable; clicking loads a detail panel below via `fetch()` from `data/topics/t{id}.json`.
- Detail panel scrolls into view smoothly (`scrollIntoView({ behavior: "smooth", block: "nearest" })`).
- Always escape user-generated text with an `escapeHtml()` helper before injecting into the DOM.
- External links: `target="_blank" rel="noopener"`, styled `color: #2a6496`.

## CSS Reset

```css
* { box-sizing: border-box; margin: 0; padding: 0; }
```