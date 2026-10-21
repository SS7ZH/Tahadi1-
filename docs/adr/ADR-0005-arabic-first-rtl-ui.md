# ADR-0005 — Arabic-first, right-to-left UI

### Status

* **Accepted**

### Date

2026-10-21

### Deciders

* Team member 1 (Muhaned)
* Team member 2 (Saeed)

### Related requirement IDs

* NFR-1 (RTL/UX: `dir=rtl`, `lang=ar`, no overflow), NFR-8 (accessibility, WCAG 2.2 AA)
* FR-1..FR-15 (implied: every UI string is Arabic)

### Context

Tahadi is an Arabic-first web app for coaches/clients in Riyadh. The requirements
demand a fully right-to-left experience with no horizontal overflow on all 6 screens,
all text right-aligned, and keyboard/screen-reader operability (NFR-1, NFR-8). The
stack is React + TypeScript, so RTL is a first-class frontend responsibility.

### Decision

We will build the UI Arabic-first and right-to-left: set `dir="rtl"` and `lang="ar"`
on the document root, use logical CSS properties (`margin-inline`, `padding-inline`,
`text-align: start`) instead of physical `left`/`right`, write all copy in Arabic, and
meet a WCAG 2.2 AA baseline (visible focus, labelled inputs, contrast ≥ 4.5:1,
keyboard operability) on every screen.

### Rejected alternative

* **Option:** Build in English / LTR first and add RTL as a later "mirror" pass.
* **Why rejected:** Refitting LTR layouts to RTL later causes overflow and
  misalignment (the exact risk in R-007) and doubles the UI work. Authoring RTL-first
  is cheaper and matches the product language.

### Accepted downside

* **Downside:** The whole team must work with Arabic text and logical CSS from the
  start, and browser/OS render differences need visual checks.
* **Mitigation / acceptance:** Use logical properties and a small set of RTL-safe
  utilities; run an RTL baseline check (a test that a screen has no horizontal
  overflow) and a visual regression on the key screens (R-007).

### Consequences

* All 6 screens render `dir=rtl`, `lang=ar`, and right-aligned.
* Components use logical properties so the layout is resilient to direction changes.
* Accessibility is designed in from the start (keyboard, focus, contrast) rather than
  retrofitted.

### Related ADRs

* `ADR-0001-choose-three-tier-option-a.md`

### How this gets verified (optional)

* A test asserts no horizontal overflow on each of the 6 screens.
* A contrast check on key text passes ≥4.5:1; focus is visible on every control.
