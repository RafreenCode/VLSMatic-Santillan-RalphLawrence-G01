---
name: VLSMatic Planning Studio
description: A precise, approachable IPv4 planning workspace derived from the VLSMatic identity.
colors:
  network-navy: "#001030"
  structural-navy: "#06254b"
  routing-cyan: "#0095a6"
  signal-cyan: "#00b7c6"
  capacity-lime: "#a2c617"
  action-lime: "#b9e51d"
  network-ice: "#e9f5f6"
  workspace: "#f3f7f8"
  surface: "#ffffff"
  ink: "#071b35"
  muted: "#53687a"
  line: "#cbd9de"
  line-strong: "#8aa3ad"
  danger: "#a32d38"
typography:
  display:
    fontFamily: "Inter, Aptos, Segoe UI, ui-sans-serif, system-ui, sans-serif"
    fontSize: "clamp(3rem, 6vw, 5.8rem)"
    fontWeight: 800
    lineHeight: 0.94
    letterSpacing: "-0.04em"
  headline:
    fontFamily: "Inter, Aptos, Segoe UI, ui-sans-serif, system-ui, sans-serif"
    fontSize: "clamp(2.7rem, 5vw, 5rem)"
    fontWeight: 800
    lineHeight: 0.96
  body:
    fontFamily: "Inter, Aptos, Segoe UI, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.55
  label:
    fontFamily: "Inter, Aptos, Segoe UI, ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.72rem"
    fontWeight: 800
    letterSpacing: "0.06em"
rounded:
  field: "8px"
  control: "9px"
  surface: "14px"
  pill: "999px"
spacing:
  xs: "8px"
  sm: "12px"
  md: "18px"
  lg: "28px"
  xl: "48px"
components:
  button-primary:
    backgroundColor: "{colors.action-lime}"
    textColor: "{colors.network-navy}"
    rounded: "{rounded.control}"
    padding: "12px 18px"
  button-secondary:
    backgroundColor: "transparent"
    textColor: "{colors.network-navy}"
    rounded: "{rounded.control}"
    padding: "12px 18px"
  input:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "11px 13px"
---

# Design System: VLSMatic Planning Studio

## Overview

**Creative North Star: "The Network Operations Desk"**

VLSMatic should feel like a calm technical instrument: authoritative enough for network planning, but readable enough for a student to understand the result at a glance. Deep structural fields establish boundaries, cyan traces relationships and selection, and lime identifies capacity and safe forward actions.

The interface favors information-rich ledgers, proportional maps, and explicit status over decorative dashboard charts. Motion explains recalculation and selection; it never runs continuously or obscures server-authoritative values.

**Key Characteristics:**

- Technical, direct, and spatially disciplined.
- Cool-white working surfaces against deep navy infrastructure.
- Real network quantities drive every visual indicator.
- Semantic HTML remains complete before enhancement.

## Colors

The palette uses the logo's navy, cyan, and lime as functional signals rather than interchangeable decoration.

### Primary

- **Network Navy:** establishes planning boundaries, canvas stages, and technical authority.
- **Structural Navy:** separates internal regions inside dark technical surfaces.

### Secondary

- **Routing Cyan:** identifies networks, current selections, links, and information.
- **Signal Cyan:** provides focus visibility and higher-energy routing detail.

### Tertiary

- **Capacity Lime:** communicates available capacity and positive plan state.
- **Action Lime:** is reserved for the main forward action on a surface.

### Neutral

- **Network Ice:** supports selected and informational regions.
- **Workspace:** provides the cool page ground.
- **Surface:** carries forms, requirements, and ledgers.
- **Ink and Muted:** form the primary and secondary text hierarchy.
- **Line and Line Strong:** divide dense planning data without heavy cards.

**The Signal Ownership Rule.** Cyan means relationship or selection; lime means capacity or forward action. Do not swap their roles.

## Typography

**Display Font:** Inter with Aptos, Segoe UI, and system sans fallbacks

**Body Font:** Inter with Aptos, Segoe UI, and system sans fallbacks

**Label/Mono Font:** the body stack for labels and the browser monospace stack for addresses

**Character:** A compact, contemporary sans system keeps the interface legible and operational. Large headings are tightly tracked; addresses use tabular or monospace forms for reliable scanning.

### Hierarchy

- **Display:** extra-bold, tightly tracked, and used only for launch or page-defining headings.
- **Headline:** bold and compact for project and editor titles.
- **Body:** regular with generous line height and a practical maximum measure around 70 characters.
- **Label:** bold, compact, and uppercase for technical metadata and controls.

**The Address Legibility Rule.** CIDRs and exact address values use monospace or tabular numerals and must never truncate in the precision ledger.

## Layout

The main workspace is a fluid container capped at 1380px with at least 24px side clearance. Dashboard metrics use ribbons and ledger rows; the planning studio uses a requirements rail beside the address map and persistent inspector. At 900px the studio, editor, and dashboard regions become a single column. At 680px metrics stack into two columns, controls become full-width where useful, and table precision remains available through horizontal scrolling.

Spacing follows an 8–12px internal rhythm, 18–28px component rhythm, and 36–72px section rhythm. Dense data remains aligned to shared edges.

## Elevation & Depth

The system combines tonal layering with restrained ambient shadows. Dark stages and pale surfaces establish most hierarchy; shadows are reserved for major working regions, not every row.

### Shadow Vocabulary

- **Action lift:** a short lime-tinted shadow marks primary actions and strengthens slightly on hover.
- **Working surface:** a diffuse low-contrast navy shadow separates forms and ledgers from the workspace.
- **Stage depth:** a broader navy shadow anchors launch headers, network consoles, and the address-space stage.

**The Structural Depth Rule.** Rows are separated with lines and tone; only major regions receive elevation.

## Shapes

Controls use gently curved 8–9px corners. Major surfaces use 14px only where the base application pattern calls for a contained panel; planning-stage geometry is often square-edged to retain a technical, diagrammatic character. Status chips alone use full pill geometry.

## Components

### Buttons

- **Shape:** compact curved control with a minimum 44–50px target.
- **Primary:** action lime with navy text, heavy weight, and a small ambient lift.
- **Hover / Focus:** hover lifts by one pixel; keyboard focus uses a three-pixel signal-cyan outline.
- **Secondary:** transparent with a strong neutral border and an ice-toned hover state.

**The Control Clarity Rule.** Any anchor presented as a button is never underlined in default, hover, focus, or active states. Underlines remain available to ordinary contextual links.

### Chips

- **Style:** pale neutral or ice backgrounds with explicit text such as Current, Draft, or Read-only.
- **State:** color always accompanies a textual status.

### Cards / Containers

- **Corner Style:** major working surfaces are restrained; repeated projects and requirements use ruled rows instead of floating cards.
- **Background:** white for editing and ledgers, navy for boundaries and visualization.
- **Shadow Strategy:** major regions only.
- **Border:** strong dividers for lists; dashed borders only for empty states.
- **Internal Padding:** 18–30px for controls and dense regions, 34–70px for launch surfaces.

### Inputs / Fields

- **Style:** white or near-white fill, strong blue-gray stroke, and 8–9px radius.
- **Focus:** visible signal-cyan outline with offset.
- **Error / Disabled:** errors use danger red in both text and boundary treatment; messages remain actionable.

### Navigation

Navigation sits on a near-opaque white bar. Navy labels gain a cyan underline on hover and keyboard focus. The logo retains clear space and is never recolored in CSS.

### Brand Mark

The official horizontal wordmark asset is used consistently on authentication and application surfaces. The standalone icon is contextual artwork only and never substitutes for the wordmark.

### Address-Space Map

The SVG preserves true relative spans, while a transparent minimum hit target keeps very small subnets selectable. Selection synchronizes the map, requirement row, inspector, and ledger. Exact values always remain in semantic HTML.

## Do's and Don'ts

### Do:

- **Do** derive indicators from persisted server values.
- **Do** pair color states with status text, labels, and focus treatment.
- **Do** keep allocation data readable with JavaScript disabled.
- **Do** disable nonessential movement under reduced-motion preferences.
- **Do** use motion to reveal a real allocation boundary, connect selection states, or acknowledge an action.

### Don't:

- **Don't** introduce decorative charts, fabricated trends, or continuous animation.
- **Don't** use lime as a generic decoration or cyan as the primary submit action.
- **Don't** replace ledger rows with a wall of identical floating cards.
- **Don't** make JavaScript the source of allocation truth.
- **Don't** loop decorative motion or hide content before enhancement initializes.
