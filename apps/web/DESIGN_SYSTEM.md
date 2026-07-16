# SalesPilot Design System

An internal, enterprise-grade design system — the shared visual and
interaction language for every future screen in the AI Sales Agent SaaS.
Modeled on the engineering bar of Stripe Dashboard, Linear, Attio, and
Vercel: quiet, consistent, fast, accessible. This document is the map;
the code under `src/` is the territory.

**This package ships primitives, not pages.** Nothing here renders a
dashboard, a settings screen, or any other application view — those are
built later, by composing what's documented below.

---

## 1. Philosophy

- **Tokens, not values.** No component ever writes a hex color, a raw px
  spacing value, or an ad-hoc shadow. Everything resolves through a CSS
  custom property, defined once in `src/styles/globals.css` and mapped to a
  Tailwind class name in `tailwind.config.ts`. Changing a token changes
  every consumer at once — that's the whole point.
- **Composition over configuration.** Components are small and combine
  (`Card` + `CardHeader` + `CardTitle`, `Dialog` + `DialogContent` +
  `DialogHeader`) rather than growing a single component with fifty props.
- **Motion is a whisper.** Durations are 120–320ms, easings are standard
  cubic-béziers, and nothing bounces or overshoots. See §5.
- **Every interactive element is keyboard- and screen-reader-accessible**
  by construction — most of this comes for free from Radix UI primitives;
  where it doesn't (custom comboboxes, drag-and-drop), it's hand-wired.

---

## 2. Tech stack

Next.js 15 (App Router) · React 19 · TypeScript (strict) · Tailwind CSS 3 ·
Radix UI primitives · class-variance-authority · tailwind-merge · clsx ·
Framer Motion · React Hook Form · Zod · next-themes · Lucide React ·
`@tanstack/react-table` · Recharts · `cmdk` · `input-otp` · `react-day-picker`
· `date-fns` · Sonner (toasts).

---

## 3. Folder structure

```
src/
  styles/globals.css          — CSS variable tokens (colors, radius, shadow, motion) + base layer
  tailwind.config.ts (root)   — maps token names to Tailwind classes
  icons/index.ts              — the ONLY place lucide-react is imported from
  motion/
    tokens.ts                 — duration/easing constants for Framer Motion
    variants.ts               — reusable Framer Motion `Variants` presets
  hooks/                      — use-media-query, use-disclosure, use-debounced-value, use-copy-to-clipboard
  lib/utils.ts                — cn(), getInitials(), formatCurrency(), formatCompactNumber(), clamp()
  components/
    ui/                       — flat directory of ~65 primitives (button.tsx, dialog.tsx, ...)
    data-table/                — the enterprise DataTable and its sub-parts
    charts/                    — ChartContainer + Line/Bar/Area/Pie/Radar chart wrappers
    layout/                   — AppLayout, PageLayout, Container, Section, ResponsiveGrid, ...
```

**Why flat `components/ui/`?** It's the shadcn/ui convention on purpose —
any engineer who has touched a shadcn codebase can find `select.tsx` in one
guess. `data-table/`, `charts/`, and `layout/` get their own folders because
each is a small *system* of files that belong together, not a single
component.

### Naming conventions

- Files: kebab-case (`icon-button.tsx`). Components: PascalCase (`IconButton`).
- One primary export per file, named exactly after the file (plus small
  co-located sub-components: `card.tsx` exports `Card`, `CardHeader`,
  `CardTitle`, etc.).
- Props interfaces are named `<Component>Props` and exported.
- Variant props always use the same vocabulary across components:
  `variant` (visual style), `size` (sm/md/lg), `tone` (semantic color for
  status-ish components — Alert, Badge, Progress).

---

## 4. Design tokens

### 4.1 Color

All colors are defined as `<hue> <saturation>% <lightness>%` triplets (no
`hsl()` wrapper) in `:root` and `.dark` in `globals.css`, then mapped in
`tailwind.config.ts` as `hsl(var(--token) / <alpha-value>)` — this is what
makes `bg-primary/10` or `ring-ring/50` work correctly.

| Token | Light | Dark | Use |
|---|---|---|---|
| `background` / `foreground` | `#FAFAF9` / `#0F172A` | `#0F172A` / near-white | Page canvas + default text |
| `card`, `popover` | white | `#111827` / slightly lighter | Elevated surfaces |
| `primary` / `primary-hover` | `#16A34A` / `#15803D` | `#22C55E` / `#16A34A` | Brand actions |
| `secondary`, `muted` | `#F5F5F4` | `#1F2937` | Low-emphasis surfaces |
| `accent` | `#DCFCE7` | `#14532D` | Soft brand highlight (selected nav item, info callouts) |
| `border`, `input`, `ring` | `#E5E7EB` | `#374151` | Structure + focus |
| `success` / `warning` / `danger` / `info` | `#16A34A` / `#F59E0B` / `#DC2626` / `#0EA5E9` | brighter variants | Status semantics, each with a `-soft` background variant for badges/alerts |
| `sidebar*` | white-based | darker-than-card | The primary nav rail — intentionally distinct from `card` |
| `chart-1..5` | green/blue/amber/violet/rose | brighter variants | Data visualization palette |
| `overlay`, `skeleton` | — | — | Modal backdrops, loading shimmer |

**Dark mode is a separate palette, not an inversion.** Surfaces step
`background → card → popover` from darkest to lightest (the opposite
direction from light mode, where `card` is white and `background` is
slightly grey) — this is what gives dark UIs visual depth instead of a
flat, inverted look. Shadows are also redefined per-theme: dark mode uses
much lower-opacity shadows and leans on `border` for separation, matching
how Linear/Vercel do dark mode.

**Adding a new semantic color** (e.g. a "beta" badge tone): add
`--beta` / `--beta-foreground` / `--beta-soft` to both `:root` and `.dark`
in `globals.css`, then add the `beta` key to the relevant `colors.*` block
in `tailwind.config.ts`. Never reach for an arbitrary Tailwind color
(`bg-purple-500`) in a component.

### 4.2 Typography

Inter is the default UI font everywhere. Poppins (`font-display`) is
reserved for marketing/landing display headings — never used in the
application shell. Both load via `next/font/google` in `app/layout.tsx`
and are exposed as `--font-sans` / `--font-display`.

| Class | Size / line-height | Use |
|---|---|---|
| `text-display-xl` → `text-display-sm` | 72px → 40px | Marketing only, pair with `font-display` |
| `text-heading-1` → `text-heading-6` | 36px → 16px | Page/section/card titles |
| `text-body-xl` → `text-body-sm` | 18px → 13px | Copy, controls, table cells |
| `text-caption` | 12px | Metadata, timestamps, badges |
| `text-overline` | 11px, wide tracking | Eyebrow labels above headings |

Use `font-mono` for code/IDs. Use the `.text-balance` utility
(`text-wrap: balance`) on wrapping headings so they don't orphan a single
word on the last line.

### 4.3 Spacing

`tailwind.config.ts` overrides Tailwind's numeric spacing keys so they
resolve to **exact pixel values matching their key name**:
`p-2` = 2px, `p-4` = 4px, `p-6` = 6px, `p-8` = 8px, `p-10` = 10px, `p-12` =
12px, `p-16` = 16px, `p-20` = 20px, `p-24` = 24px, `p-32` = 32px, `p-40` =
40px, `p-48` = 48px, `p-56` = 56px, `p-64` = 64px, `p-80` = 80px, `p-96` =
96px, `p-128` = 128px. (Note this **differs from stock Tailwind**, where
`p-8` is 32px — that's deliberate; the brief calls for a literal px-named
scale.) Non-overridden keys (1, 3, 5, 7, ...) still fall back to Tailwind's
default rem scale as an escape hatch, but code review should question any
spacing value outside the named list.

### 4.4 Radius

`rounded-xs` (4px) · `rounded-sm` (6px) · `rounded-md` (8px) · `rounded-lg`
(12px, the default for cards/inputs/buttons) · `rounded-xl` (16px) ·
`rounded-2xl` (20px) · `rounded-full`.

### 4.5 Shadows

`shadow-sm/md/lg` for general elevation, plus purpose-named
`shadow-dropdown`, `shadow-popover`, `shadow-floating`, `shadow-modal`,
`shadow-sidebar`. All are CSS variables so dark mode can redefine them as
near-invisible instead of just "the same shadow, darker."

### 4.6 Motion

`duration-fast` (120ms) / `duration-normal` (200ms) / `duration-slow`
(320ms) and `ease-standard` / `ease-emphasized` / `ease-decelerate` /
`ease-accelerate` are both Tailwind utilities (`transition-duration-fast`)
**and** JS constants in `src/motion/tokens.ts` for Framer Motion. Reusable
`Variants` objects live in `src/motion/variants.ts`:
`fadeIn`, `fadeInUp`, `scaleIn`, `modalVariants`, `dropdownVariants`,
`drawerRightVariants` / `drawerLeftVariants`, `sidebarVariants`,
`toastVariants`, `pageTransitionVariants`, `staggerContainer` /
`staggerItem`, `hoverScale`. Import these instead of writing new
`transition={{...}}` objects — that's how the whole app stays feeling like
one product instead of fifty components each animated by a different
author. `prefers-reduced-motion` is handled globally in `globals.css`
(durations collapse to ~0 rather than animations being removed outright).

---

## 5. Icons

Every icon comes from `@/icons`, which re-exports a curated subset of
`lucide-react`. **Never `import { X } from "lucide-react"` in a page or
feature component.** If an icon you need isn't exported yet, add it to
`src/icons/index.ts` — this keeps the icon set auditable in one file and
makes a future icon-library swap a one-line change per icon instead of a
project-wide find-and-replace.

---

## 6. Component catalog

All paths are relative to `src/components/` unless noted. Every component
is a named export with a documented `Props` interface — open the file for
the full prop list; this table is the index, not the reference.

### Buttons & actions
| Component | File | Notes |
|---|---|---|
| `Button` | `ui/button.tsx` | variants: primary/secondary/outline/ghost/soft/success/warning/danger/link · sizes sm/md/lg/icon · `isLoading`, `fullWidth`, `asChild` |
| `IconButton` | `ui/icon-button.tsx` | Square icon-only button; `aria-label` is required at the type level |
| `SplitButton` | `ui/split-button.tsx` | Primary action + attached dropdown for secondary actions |

```tsx
<Button variant="primary" isLoading={isSubmitting}>Save changes</Button>
<IconButton icon={Trash2} aria-label="Delete" variant="danger" size="sm" />
```

### Form inputs
`Input`, `PasswordInput`, `SearchInput`, `Textarea` (with `showCharacterCount`),
`Checkbox` (supports `indeterminate`), `RadioGroup`/`RadioGroupItem`, `Switch`,
`Select` family (Radix-based), `Combobox` (searchable single-select),
`MultiSelect` (chips + search), `TagInput` (free-text chips), `OtpInput`
family, `Calendar` (react-day-picker), `DatePicker`, `TimePicker`.

```tsx
<Combobox options={owners} value={ownerId} onValueChange={setOwnerId} placeholder="Assign owner" />
<DatePicker value={dueDate} onChange={setDueDate} />
```

### Data display
`Avatar` / `AvatarGroup`, `Badge`, `StatusBadge` (dot + label, optional
`pulse`), `Chip` (removable), `Progress`, `CircularProgress`, `Spinner`,
`Skeleton`, `Card` family, `MetricCard`, `StatCard`.

```tsx
<MetricCard label="Pipeline value" value="$482,300" change="+12.4%" trend="up" icon={TrendingUp} />
```

### Feedback & overlays
`Alert` (+ `AlertTitle`/`AlertDescription`), `Toaster`/`sonner`'s `toast()`,
`Dialog` family, `Drawer` family (side panel, not a mobile bottom-sheet),
`Popover`, `Tooltip` (needs the app-wide `TooltipProvider`, already mounted
in `AppProviders`), `DropdownMenu` family, `ContextMenu` family.

```tsx
import { toast } from "sonner";
toast.success("Campaign published");
```

### Navigation
`Breadcrumb` family + `BreadcrumbTrail` convenience wrapper, `Tabs`,
`Accordion`, `Pagination`, `ScrollArea`, `Sidebar` system
(`SidebarProvider`/`Sidebar`/`SidebarNavItem`/`SidebarTrigger`, collapsible
with per-item tooltips when collapsed), `TopNav`, `PageHeader`,
`SectionHeader`, `CommandPalette` (+ `useCommandPalette()` ⌘K hook).

### Data table
`components/data-table/` — `DataTable<TData>` wraps `@tanstack/react-table`
with sorting, global search, column visibility, sticky header, row
selection + bulk-actions bar, pagination, and built-in loading/empty
states. `DataTableColumnHeader` for sortable headers, `DataTableRowActions`
for the trailing "⋯" menu.

```tsx
<DataTable
  columns={columns}
  data={leads}
  enableRowSelection
  bulkActions={<Button size="sm" variant="danger">Delete</Button>}
  isLoading={isLoading}
/>
```

### Charts
`components/charts/` — `ChartContainer` + `ChartConfig` (maps a data key to
a label and a `--chart-N` color) underpin `LineChart`, `BarChart`,
`AreaChart`, `PieChart` (+ `DonutChart` preset), `RadarChart`, plus
`HeatmapPlaceholder`/`FunnelPlaceholder` reserving layout for chart types
not yet implemented.

```tsx
const config: ChartConfig = {
  won: { label: "Won", color: "hsl(var(--chart-1))" },
  lost: { label: "Lost", color: "hsl(var(--chart-3))" },
};
<BarChart data={data} config={config} xKey="month" />
```

### State & composite
`EmptyState`, `ErrorState` (with `onRetry`), `LoadingState`, `Timeline` /
`TimelineItem`, `StepIndicator`, `FileUpload` / `FileUploadItem`
(drag-and-drop + progress), `NotificationItem`, `ActivityItem`,
`DashboardWidget` (Card preset with built-in loading/error slots).

### Layout primitives (`components/layout/`)
`AppLayout` (Sidebar + TopNav + main shell), `PageLayout`, `Container`,
`Section`, `ResponsiveGrid` (+ `MetricGrid` preset), `SidebarLayout`
(in-page nav, e.g. Settings), `SplitLayout` (master/detail), `EmptyLayout`
(auth screens), `CenteredLayout`.

```tsx
<AppLayout sidebar={<Sidebar>...</Sidebar>} topNav={<TopNav right={<UserMenu />} />}>
  <PageLayout>
    <PageHeader title="Leads" actions={<Button>New lead</Button>} />
    ...
  </PageLayout>
</AppLayout>
```

### Forms (React Hook Form + Zod)
`ui/form.tsx` — `Form`, `FormField`, `FormItem`, `FormLabel`, `FormControl`,
`FormDescription`, `FormMessage`. `FormMessage` reads the field's Zod error
automatically; no manual error-string plumbing.

```tsx
const schema = z.object({ email: z.string().email() });
const form = useForm<z.infer<typeof schema>>({ resolver: zodResolver(schema) });

<Form {...form}>
  <form onSubmit={form.handleSubmit(onSubmit)}>
    <FormField
      control={form.control}
      name="email"
      render={({ field }) => (
        <FormItem>
          <FormLabel required>Email</FormLabel>
          <FormControl><Input type="email" {...field} /></FormControl>
          <FormMessage />
        </FormItem>
      )}
    />
    <Button type="submit" isLoading={form.formState.isSubmitting}>Continue</Button>
  </form>
</Form>
```

---

## 7. Accessibility

- Every interactive primitive is either a native element (`<button>`,
  `<input>`) or a Radix UI primitive, which ships correct ARIA roles,
  keyboard handling, and focus management out of the box.
- Focus is always visible: `:focus-visible` gets a 2px `ring` token
  application-wide (see `globals.css`), never suppressed.
- Icon-only controls (`IconButton`, `SidebarTrigger`, chip remove buttons)
  require an `aria-label` at the TypeScript level, not just by convention.
- Color is never the only signal: `StatusBadge` pairs color with a label,
  form errors pair red with text via `FormMessage`.
- `prefers-reduced-motion` is respected globally.
- Contrast: every text/background pairing in the token table targets WCAG
  AA (4.5:1 body text, 3:1 large text/UI components) in both themes.

---

## 8. Responsive strategy

Breakpoints: `sm` 640px · `md` 768px · `lg` 1024px · `xl` 1280px · `2xl`
1440px (see `tailwind.config.ts` `container.screens`). The rule is **adapt,
don't shrink**:
- `Sidebar` collapses to an icon rail (with tooltips) at `lg`, not a
  horizontally-squeezed sidebar.
- `SidebarLayout` and `SplitLayout` stack vertically below `lg` instead of
  rendering two cramped columns.
- `ResponsiveGrid` takes explicit per-breakpoint column counts
  (`cols={{ base: 1, sm: 2, lg: 4 }}`) rather than one column count that
  Tailwind squishes.
- `DataTable` wraps in a horizontally-scrolling container rather than
  trying to reflow columns — the correct behavior for dense tabular data
  on small screens.

---

## 9. Best practices / house rules

1. **No hardcoded colors, spacing, radii, or shadows** — if you typed a
   hex code, a raw `px` value outside the spacing scale, or `shadow-[...]`,
   stop and find (or add) the token.
2. **Compose, don't configure.** If a component needs a 6th boolean prop to
   handle a new layout, it probably wants a new sub-component instead.
3. **One import path per concept.** Icons from `@/icons`. `cn()` from
   `@/lib/utils`. Motion variants from `@/motion/variants`.
4. **Client components stay minimal.** Only add `"use client"` where
   interactivity genuinely requires it (this is why layout primitives like
   `Container`/`Section` are plain server components).
5. **Every new primitive gets a `Props` interface, a one-line JSDoc comment
   explaining *why* it exists (not what it obviously does), and a place in
   this document's catalog.**
