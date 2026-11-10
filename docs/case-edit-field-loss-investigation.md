# Case edit — where the five fields are lost

Date: 2026-11-10
Scope: "editing an existing case and saving it wipes Last Known, Age, Gender,
Authoritative Source, Source URL"

## Summary

One of the five is verifiably lost, in the frontend, on every save:
**Last Known Date**.

The other four — Age, Gender, Authoritative Source, Source URL — round-trip
through the edit form intact. The backend stores and returns all five
correctly. The cause of the Last Known loss is a type mismatch introduced by
the Zod parse boundary.

Secondary defect from the same root cause: the case page renders
"Last known" as an empty value.

---

## 1. The confirmed bug — Last Known Date is wiped on every save

### Where the data is lost

`frontend/src/routes/persons/[id]/edit/+page.svelte:116`

```js
lastKnownDate = isoToMonthYear(person.last_known_date);
```

`person` comes from `getPerson()` (`frontend/src/lib/api.ts:223`), which
parses the wire payload through `PersonDetailSchema`
(`frontend/src/lib/schemas/overlays.ts:52`).

`overlays.ts:77`

```js
last_known_date: isoDateNullable.optional(),
```

`isoDateNullable` (`frontend/src/lib/schemas/wire.ts:52`) transforms the wire
string `"2026-01-15"` into a **`Date` object**.

`isoToMonthYear` (`frontend/src/lib/dateFormat.ts:112`) only accepts strings:

```js
export function isoToMonthYear(iso: unknown): string {
	if (typeof iso !== 'string' || !iso) return '';
	...
}
```

A `Date` is not a string → it returns `''` → the month picker renders
**empty** → `handleSubmit` (same file, line 275) sends:

```js
baseData.last_known_date = lastKnownDateIso || null;   // → null
```

→ `PATCH /api/persons/{id}/` with `last_known_date: null` → the stored date is
**erased**.

### Verified, end to end

The wire payload below is the real `GET /api/persons/{id}/` response captured
from the running Django API. The edit form was rendered with the real
`getPerson()` (stub at the `fetch` layer only — the Zod parse runs for real),
then saved.

```
FORM SHOWS:          last_known_date: ""            ← stored value 2026-01-15
WIRE HAS:            last_known_date: "2026-01-15"
PATCH SENDS:         last_known_date: null          ← the wipe
```

### The backend is not involved

Verified against the real Django API (SQLite test DB, `manage.py test`):

```
POST   /api/persons/  → 201   {last_known_date: 2026-01-15, age_at_incident: 42,
                                 gender: F, authoritative_source: ACGT,
                                 authoritative_url: https://example.org/case/12345}
GET    /api/persons/1/ → 200   all five present on the wire
PATCH  /api/persons/1/ → 200   after PATCH: all five unchanged — LOST ON PATCH: none
```

`PersonWriteSerializer` (`backend/cases/serializers.py:624`) uses
`exclude = ['categories']`, so every `Person` model field is writable, and
`PersonViewSet.perform_update` (`backend/cases/views.py:466`) is a plain
`serializer.save()`. No field is dropped server-side.

### When it was introduced

| commit | date | what |
|---|---|---|
| `abeb127` | 2026-09-06 | Zod parse boundary lands; `last_known_date` becomes a `Date` at runtime |
| `c5c9939` | 2026-09-30 | edit form switches to `isoToMonthYear(person.last_known_date)`, still assuming a string |

`c5c9939`'s message says "Zod wire schemas, backend DateField, and API
contract unchanged" — the author assumed the value was still a string.

### Why the type checker did not catch it

`frontend/src/lib/types.ts:214` declares `last_known_date?: string | null`,
but `getPerson` returns `parsed.data as unknown as Person` — the `as unknown`
casts the `Date` back to the declared `string`. The type is a lie at runtime.

---

## 2. The same root cause also blanks the case page

`frontend/src/routes/persons/[id]/+page.svelte:1033`

```svelte
<dd>{formatMonthYear(person.last_known_date)}</dd>
```

`formatMonthYear` (`frontend/src/lib/dateFormat.ts:95`) has the same
string-only guard, so it returns `''`. The sidebar row is present but empty.
Verified by rendering the real page:

```html
<div class="sidebar-field"><dt>Last known</dt> <dd></dd></div>
```

The **list** page and the **watchdog** page are fine — `getPersons()` and
`getWatchdog()` do not run the Zod parse, so they still receive raw strings.

---

## 3. The other four fields — checked, not reproducible

`Age` (`age_at_incident`), `Gender`, `Authoritative Source`,
`Authoritative Source URL` all survive the load → form → PATCH → DB path:

```
FORM SHOWS:   gender: "F"              age_at_incident: "42"
               authoritative_source: "ACGT"
               authoritative_url: "https://example.org/case/12345"
PATCH SENDS:  gender: "F"              age_at_incident: 42
               authoritative_source: "ACGT"
               authoritative_url: "https://example.org/case/12345"
```

All four are declared in `PersonDetailSchema` (`overlays.ts:70, 80, 81, 93`),
are preserved by the parse, are shown in the form, and are sent back
unchanged.

Everything else that could drop a field on write was checked and ruled out:

- only one place PATCHes a person — `frontend/src/lib/api.ts:315`
  (`updatePerson`), used only by the edit page;
- no reduced-field `Person.objects.filter(...).update(...)` anywhere in
  production code;
- `PersonWriteSerializer` raises a 400 on unknown keys rather than dropping
  them, so a malformed payload cannot silently half-apply;
- the Django admin's `fieldsets` omit `age_at_incident` (admin cannot edit it),
  but Django admin never clears a field it does not render.

Two display defects were found while checking, but neither loses data:

- the case page shows the raw enum letter for gender (`F`, not `Female`) —
  `persons/[id]/+page.svelte:1045`;
- the case card does not show gender or source at all; it shows
  Name / Parent / **Age** / Residence / Profession / abduction —
  `frontend/src/lib/caseCardData.ts:107-125`.

So the teammate's list of five is half confirmed. To close the gap, the
specifics are needed: which case id, which surface (web edit form, Django
admin, or an import), and what they saw before vs after the save.

---

## 4. The fix that was applied

Branch `fix/last-known-date-parse`. Option A: keep the Zod boundary as
designed and make the two date helpers read a `Date` as well as a string.

`frontend/src/lib/dateFormat.ts` — both helpers now go through the file's
existing `toUtcDate()` helper, so a `Date` and an ISO string are read the
same way:

```ts
function toYearMonth(value: unknown): { year: string; month: string } | null {
	const d = toUtcDate(value);
	if (!d) return null;
	return {
		year: String(d.getUTCFullYear()).padStart(4, '0'),
		month: String(d.getUTCMonth() + 1).padStart(2, '0'),
	};
}
```

`formatMonthYear()` and `isoToMonthYear()` both use it. The unreadable-string
pass-through (`formatMonthYear('not-a-date') === 'not-a-date'`) is kept.

`frontend/src/lib/types.ts:214` — `last_known_date?: string | Date | null`,
so the type matches the runtime. The watchdog page's two date helpers were
widened to accept a `Date` to match.

### The rejected alternative

Option B was to change `overlays.ts:77` to `z.string().nullable().optional()`
so `last_known_date` stays a string on the client, matching the declared
`Person` type and the list/watchdog pages. Narrower, but it makes the
overlay inconsistent with `date_of_birth` and `case_received_date`, and it
leaves the type lie in `types.ts` for those two fields.

### Still open

The form is month-precision (`YYYY-MM` → `YYYY-MM-DD` with `-01`). Saving a
case whose stored date has a real day (e.g. `2026-01-15`, from a legacy
import) rewrites it to `2026-01-01`. The month survives; the day does not.
Either:

- accept it (the month picker is the intended precision), or
- send the original day when the user did not touch the month field.

---

## 5. Regression test

The repo could not render a route component in a test: the vitest config uses
the plain Svelte plugin, not `svelteKit()`, so `$app/paths`,
`$app/navigation` and `$app/state` did not resolve.
`frontend/src/test-stubs/` plus three `resolve.alias` entries in
`frontend/vitest.config.ts` fix that.

`frontend/src/routes/persons/[id]/edit/edit.test.ts` renders the real edit
form, stubbed at the `fetch` layer so the real `getPerson()` (and therefore
the real Zod parse) runs. It pins four things:

- the form shows the last known month the case carries;
- the PATCH carries it back instead of `null`;
- age, gender, source and source URL survive the save;
- the save returns to the case page.

Run against the pre-fix code, it fails on `last_known_date` only: the form
shows an empty month picker and the PATCH carries `last_known_date: null`.
