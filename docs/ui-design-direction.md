# Stay Insight UI design expansion

Date: 2026-10-22. Design only; no application implementation or product Phase change.
Canvas: design/stay-insight.pen, edited through Pencil MCP only.

## Preserved design

The original localhost, UI Foundations, Components, Properties — Redesign and
Properties — Mobile frames were compared before/after and remain unchanged.
Existing tokens, Noto Sans KR, blue-gray palette, 4px rhythm and 6/10px radii remain.

## A. New frames

| Frame | Node | Width |
| --- | --- | ---: |
| Operational Components | MGiud | 1440 |
| Property Detail — Desktop | v695xL | 1440 |
| Dashboard V2 — Desktop | qn0En | 1440 |
| Reservations — Desktop | SWY3S | 1440 |
| Reservation Create — Desktop | jCMXZ | 1440 |
| Reservation Edit — Desktop | EDdai | 1440 |
| Dashboard V2 — Mobile | gHyzP | 390 |
| Reservations — Mobile | xYhtm | 390 |

Create/edit are separate states because identity fields and required reasons differ.

## B–C. Components

Fourteen added reusable patterns: KPI Card, Comparison Indicator, Data Quality
Notice, Form Field, Form Label, Help Text, Validation Error, Textarea, Field Group,
Table Header, Reservation Table Row, Chart Container, Audit Event, Mobile Reservation
Card. Text/number/date/select use one Form Field with overrides, not competing styles.
Existing App Header, Navigation Item, Page/Section Header, Primary/Secondary Button,
Status Badge and Empty State are reused. The approved Property Card is preserved.

## D. Dashboard hierarchy

Revenue and known operating profit are primary; estimated occupancy/ADR/RevPAR form
one separate group. Costs, count and average stay are quieter secondary information.
Monthly financial and occupancy trends precede channel and cost details.
Source, date basis, comparisons and quality explanations remain visible.
No new KPI or calculation; read [dashboard-v2](dashboard-v2.md) and [metrics](metrics.md).

All dashboard numbers are unbound design placeholders. Chart areas are explicitly
marked design representations, with no invented plotted observations. The component
board includes tooltip, empty and missing-data concepts. Missing months are gaps,
not zero; unavailable ratios are not zero. Percentage-point comparisons remain distinct.
Info notices explain normal estimates; amber is reserved for conditions needing review.
Known profit does not become verified accounting profit or actual completed-stay revenue.

## E. Reservation table

Keep existing fields, grouping source with identifier and dates into one stay column.
Use horizontal separators and right-aligned KRW/count columns. Status contains text.
CSV, manual registration and manual corrections have distinct meanings. No guest PII,
search/sort/export, row selection, bulk action or reservation hard delete was added.
Rows use existing development examples, not invented production records. Hover, empty,
loading and stale-edit/reload concepts live on the component board.

## F–G. Forms and history

Group identity, stay dates, amounts, rooms/guests, status and reason. Registration
allows an absent external ID; editing keeps identity immutable. Reason is required
for edits, cancellation/reopening and protection release, not initial creation.
Fields retain required/optional labels and meaningful null/zero distinctions.
CSV corrections show the protected field. Inline release confirmation explains that
current values stay unchanged until a subsequent new CSV updates the field.
History stays secondary and read-only: source, time, short actor identity, reason,
field, before and after; no raw JSON or invented pre-Phase-12 history.
[Manual workflow](manual-reservations.md), [audit](reservation-audit.md),
[CSV contract](imports.md), [inventory](inventory-availability.md).

## H–I. Mobile

Dashboard: full-width key financial metrics, early estimate notice, compact operating
rows, stacked chart containers, then channel/cost detail. Reservations: cards expose
identifier, source/status, dates, quantities, money and a 44px detail action, without
forcing the desktop table into horizontal overflow. Registration stays near the top.
The same global header and property navigation order are retained; no new app shell.

## J–K. Width and accessibility

Operational desktop recommendation: max-width 1280px inside a 1440px viewport,
80px side margins; preserve the approved properties screen's 1120px composition.
Mobile: 390px with 24px margins and 342px content. Frames show complete page flows,
not fixed-height production viewport requirements. Tall frame bounds were corrected.
Use 44px major actions, visible focus, labeled inputs, text errors and text status.
Contrast uses approved tokens. This is visual design review, not a complete WCAG audit.

## L–N. Implementation observations and next design

Current frontend has an Arial/Malgun Gothic stack, a narrow shared max-width and
an exceptional negative-margin dashboard. Most tables use full grid borders with
little numeric alignment; forms, links and repeated sections lack shared primitives.
Dashboard currently gives all eight metrics equal cards and places long explanations
before charts. Property type is an enum code; preserve its meaning if localized.
Historical documentation contains earlier phase limits: current code and additive
Phase 11/12 contracts take precedence. No source behavior was changed here.

Later React candidates: AppHeader, PropertyNav, PageHeader, Button, Card, Badge,
KpiCard, ComparisonIndicator, DataQualityNotice, FormField/FieldGroup, DataTable,
ReservationCard, ChartContainer and AuditTimeline. Do not implement them in this task.
Next Pencil screens: inventory/availability, expenses, CSV import flow, regional market,
then loading/error/empty/accessibility states across those existing workflows.

## Verification and delivery

Reviewed the seven new screens and operational component board visually. Inspected
mobile filter, chart, KPI rows and reservation card individually; corrected clipped
page bounds. Verified all five approved frames unchanged through Pencil node snapshots.
No frontend/backend/Docker/database files changed. Code tests/build were not rerun:
this task changes design and documentation only. Pencil-generated font files were
already untracked before this task and are excluded from the commit.
