# UI Implementation Wave 1

Date: 2026-10-22. Status: IMPLEMENTED and ACTUALLY BROWSER VERIFIED; required checks passed.
This is a frontend presentation change, not a new product Phase.

## A–Q. Implementation contract

| Item | Result |
| --- | --- |
| A. Starting branch / HEAD | ui/pencil-redesign / 54ce53f |
| B. Starting tree | No application changes; only intentionally untracked design/fonts/. |
| C. Pencil references | Foundations, components and all nine approved desktop/mobile screen states inspected through MCP. Original localhost preserved. |
| D. Functional gate | Properties, dashboard-v2, reservation create/edit, CSV protections and audit/history exist. API contracts and handlers preserved. |
| E. IMPLEMENTED | Properties desktop/mobile, property detail, dashboard desktop/mobile, reservations desktop/mobile, reservation create/edit/history. |
| F. DESIGNED BUT NOT FUNCTIONALLY AVAILABLE | No requested core screen is blocked. No export, bulk selection, guest identity, OTA sync or hard deletion was introduced. |
| G. Tokens | Existing Pencil blue-gray/white palette, 4px rhythm, 6px controls/10px cards; CSS custom properties in globals.css. |
| H. Shared UI | AppHeader, PropertyNav, PageHeader, Button, Surface, StatusBadge, SectionHeader, DataQualityNotice, KpiCard, FormField, FieldGroup, ChartContainer, ReservationMobileCard. |
| I. Font | @fontsource-variable/noto-sans-kr 5.3.1, pinned with integrity in pnpm-lock.yaml. Local package CSS/WOFF2, font-display:swap and Unicode subsets; no build-time Google request or copied design/fonts. |
| J. Container | Shared max 1376px including desktop padding, producing 1280px usable content at 1440px. Approved properties list caps at 1120px. No dashboard negative margin. |
| K. Properties | Real organization/property data, registration, address, inventory, detail links and existing pagination. |
| L. Detail | Existing metadata and routes retained; main facts plus operational actions. |
| M. Dashboard | Primary revenue/known profit, early quality notices, estimated operating metrics, supporting KPIs, real Recharts, channel/cost detail. All eight existing values and comparisons retained. |
| N. Reservations | Semantic table with grouped stay dates and right-aligned numbers; equivalent mobile cards preserve every existing field and detail action. |
| O. Create/edit | Existing form event handlers, validation helpers, expected_version and API payloads preserved. Identity remains read-only on edit; required reasons, release confirmation, conflict/reload and audit remain. |
| P. Accessibility | Skip link, current navigation, visible focus, implicit labels, fieldset disabling, form-level error association, semantic headings/tables/time, text statuses and estimates, 44px main targets. |
| Q. Responsive | Fluid shell; two/three-column desktop analysis; mobile key financial metrics first, compact estimates, stacked charts and reservation cards. |

## Functional boundaries

FastAPI, schemas, repositories, migrations, RLS, roles, authentication helpers and
Supabase semantics are unchanged. Server pages remain Server Components. AppHeader
is a small pathname-aware Client Component using the existing SignOut component;
its visibility is presentation only. ProtectedLayout still requires the token.
No business data is fetched from the browser through Supabase.

Dashboard helpers, grouping, calculations, API calls and period semantics are unchanged.
Korean source, known-profit limitations, missing-data/null behavior, UNKNOWN/CANCELLED
rules and estimation wording remain. Recharts keeps actual response data, null gaps,
unclamped occupancy and exact-value table. Empty chart messages only reflect rendering
availability, never invented zeroes or observations.

## Pencil translation and deliberate differences

The Pencil mock values/shapes were not copied. Actual records can have long identifiers,
negative profit or larger money values: wrapping, responsive tables and chart dimensions
take precedence over exact fixed artwork positions. Existing icon-free text links remain
where they are clearer than adding an icon dependency. Property type retains its existing
server enum label. Charts retain accessible live Recharts rather than neutral design shapes.

Global header combines existing identity, property navigation, health and sign-out targets.
Existing required/optional field contracts are unchanged; one shared field wrapper styles
text, numbers, dates, selects and textarea. No shadcn migration or UI framework was added.

## R–AG. Verification and delivery

| Item | Actual status |
| --- | --- |
| R. ESLint | Passed on host and in the isolated Compose frontend. Backend Ruff also passed. |
| S. TypeScript/typegen | Passed on host and in the isolated Compose frontend. Backend mypy passed (115 files). |
| T. Frontend tests | 58 passed, no skipped tests. Four new UI/data-preservation tests; existing interaction/security suites retained. |
| U. Isolated production build | Passed in a disposable Compose frontend; all application routes generated. Active dev .next was not used. |
| V. Docker | Frontend rebuilt/recreated; Compose config passed and frontend/backend/db healthy. Backend health/readiness passed. No config edits or volume deletion. |
| W. Actual browser | ACTUALLY BROWSER VERIFIED: authenticated Chrome properties/detail/dashboard/reservations/create/edit/history on desktop; properties/dashboard at 390 CSS px. Authenticated in-app browser completed 390px reservation cards and all deferred smoke checks. Development-only reservation created, edited and cancelled with three audit events. |
| X. Pencil comparison | Approved properties, detail, dashboard, reservations and create/edit references inspected alongside live screens. Shared palette, hierarchy and columns preserved; form field alignment corrected. Mobile dashboard has stacked financial cards and two 300px live charts; mobile reservations retain badges, dates, money and full-width detail actions. Actual data/wrapping differs from design placeholders. |
| Y. Deferred smoke checks | ACTUALLY BROWSER VERIFIED: inventory/capacity forms and availability table; expense filters/summary/list; CSV upload controls and nested route; regional licenses, visitor chart and events with distinct sources/freshness. HTTP 200 and no desktop document overflow. |
| Z. Remaining differences | Dynamic data/wrapping, native form controls and real charts intentionally differ from static mockups. |
| AA. Changed files | Frontend presentation components/pages/CSS, frontend tests, one font dependency/lockfile, UI documentation. See Git diff. |
| AB. Documentation | This report, ui-design-direction.md and architecture ADR-065. |
| AC. Fonts/design | design/fonts remains untouched/untracked. Approved .pen unchanged. |
| AD. Commit | feat: implement approved Pencil UI redesign (see Git history for the resulting hash). |
| AE. Push/upstream | Normal push to origin/ui/pencil-redesign with upstream; final result reported in the delivery message. |
| AF. Limits | NOT VERIFIED: full WCAG conformance, performance/load and hosted deployment. Existing cold dev compilation/API latency and Chrome control instability are noted below. |
| AG. Wave 2 | Inventory/availability, expenses, CSV flow and regional market details; no Wave 2 work here. |

Backend regression suite: 298 passed, with two existing dependency deprecation warnings.
Frontend suite: 58 passed both on the host and in the isolated container.
The user logged into Chrome, which has a separate session from the in-app browser.
Authenticated Chrome verified real API values and saved changes. A subsequent reconnection
also verified properties/dashboard at 390 CSS px. Chrome control repeatedly timed out or
detached during navigation, including fresh-tab recovery. With explicit user approval,
verification continued in an authenticated in-app browser and completed mobile reservation
cards and inventory, expenses, CSV and market smoke checks. Authentication is unchanged.
Mobile reservation desktop table was display:none and cards display:grid, viewport 390px
and scrollWidth 375px including the scrollbar. Keyboard navigation exposed a solid 2px
focus outline on the brand link. No secrets or guest information were used for verification.

The existing Chrome zoom was 90%; viewport overrides were compensated and DOM measurements
confirmed 1440px desktop and 390px mobile widths. Mobile properties had scrollWidth 390;
dashboard had scrollWidth 373 (390 viewport including scrollbar), eight KPI articles,
two 300px charts, separate mobile channel rows, source/estimate labels and real values.
One cold dashboard request logged an API connection timeout after 35 seconds of dev
compilation. A warm retry displayed the real data successfully; backend readiness returned
HTTP 200. This is not evidence of a routing 404 or a change to authentication.

Development browser record: DEV-UI-WAVE1-20261022, DIRECT, 2026-10-20 to 2026-10-22.
Created with 300,000 KRW and one room, edited to 320,000 KRW and two rooms, then
cancelled with a verification reason. Version 3 and three audit events were observed;
the cancelled record remains for audit and is excluded from financial aggregation.
No guest identity or contact information was entered.

## Operations

Use the repository root. Frontend remains image-copied; restart alone is insufficient.

~~~powershell
docker compose up -d --build frontend
docker compose config --quiet
docker compose run --rm --no-deps frontend sh -c 'pnpm lint && pnpm exec next typegen && pnpm typecheck && pnpm test && pnpm build'
~~~

The isolated run uses its own writable container filesystem and .next directory.
No environment files, credentials, build output, font binaries or screenshots belong in
the commit. The intentional design/fonts directory is not a completely clean working tree.

## Completed review checklist

Verified properties/detail/dashboard/reservations at desktop width, properties/dashboard/
reservations at 390px, actual API records, navigation, keyboard focus and document overflow.
Development-only reservation create/edit/cancel retained its audit. Deferred routes returned
HTTP 200, including imports/new, with their existing controls and data. Corresponding Pencil
references were compared through MCP without editing the approved .pen file.
