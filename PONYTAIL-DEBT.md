# Ponytail debt ledger

Every deliberate shortcut in this project is marked with a `ponytail:` comment naming its ceiling
and the trigger that should make someone revisit it. This file collects them so a deferral cannot
quietly become permanent.

> Harvested 2026-08-15 from `grep -rnE '(#|//) ?ponytail:'` plus the two markers that live in Python
> docstrings. **Line numbers drift — the comment is the source of truth, this file is the index.**
> Re-run the harvest rather than trusting the numbers below.

**14 markers · 1 with no trigger · 2 whose trigger has already fired.**

## Triggers that have already fired

These two are the ones to read first: the condition their own comment names as the moment to
revisit has happened.

- **`bunker_core/static/movil/queue.js:8`** — localStorage instead of IndexedDB, flushed from the
  page rather than the service worker. *Ceiling:* a service worker cannot read localStorage, so
  moving the flush means moving the store. *Upgrade:* "when captures must sync without the app being
  opened" — **which is the entire reason "Transmisor de Campo v2" exists**. Task 10 replaces this
  file's storage with the native bridge and keeps the API as a facade.
- **`android/…/Transmisor.kt:106`** — `postReal` deliberately untested; every check injects `poster`
  instead. *Ceiling:* the socket itself, `instanceFollowRedirects`, and `disconnect()` not being in
  a `finally` are all unproven. *Upgrade:* "Task 8's flush on the phone, which is the first time
  this runs for real" — **that flush ran on 2026-08-15 and reached Django**. What is owed now is
  either recording that it was verified, or admitting the `finally` still has not been.

## No trigger — the one that rots silently

- **`disquera/models.py:102`** `no-trigger` — a dead model kept rather than dropped after the minute
  ledger was removed (2026-08-14). *Ceiling:* nothing reads or writes it. *Upgrade:* **none named.**
  Its twin at `movies/models.py:108` says "drop it if a schema cleanup ever runs for its own
  reasons"; this one was left half-written. Copy that sentence into it and it stops rotting.

## The rest

### Android (the APK)

- **`AssetStore.kt:188`** — the fetch checks the response code now, but nothing checks *content*.
  *Ceiling:* a 2xx carrying the wrong body is indistinguishable from a good one, and
  `hayGeneracionValida` only asks whether the files are non-empty. *Upgrade:* a hash or a
  content-type check, the day an asset arrives corrupted with a 200.
- **`ColaStore.kt:144`** — the MediaStore round trip is verified by hand on the phone, not by a
  check. *Ceiling:* Robolectric cannot query back what it accepted. *Upgrade:* an instrumented test,
  which this plan's constraints rule out — so verify it by hand once Task 10 makes a capture
  reachable. **This is the load-bearing one:** `decisions/log.md` (2026-08-14) rejected a relay
  *because* the backup file buys the same durability, and that trade rests on a restore path nobody
  has exercised.
- **`MainActivity.kt:57`** — the exact-alarm request is sent once and the answer remembered.
  *Ceiling:* whoever declines keeps the inexact alarm for ever, with no way back. *Upgrade:* a
  banner in the WebView (Task 10), the first screen able to say why the queue is slow and offer the
  intent again.

### Django / the web companion

- **`bunker_core/insights.py:124`** — no index on `(category, start_time)`. *Ceiling:* invisible at
  53 rows. *Upgrade:* index it if Deep Work ever grows to thousands of sessions.
- **`bunker_core/views.py:472`** — `valid_days` matched by substring. *Ceiling:* correct only
  because weekdays are single digits 0-6. *Upgrade:* a real membership test if that field ever holds
  anything wider.
- **`bunker_core/templates/movil/sw.js:7`** — network-first, not cache-first. *Ceiling:* a
  slow-but-alive network makes the shell wait for the timeout. *Upgrade:* stale-while-revalidate,
  if that ever bites.
- **`catalog/views.py:234`** — `max(current_page - previous, 0)`. *Ceiling:* re-reading and a typo
  are indistinguishable from there, so a lower page records zero rather than a negative delta.
  *Upgrade:* if undo ever matters, it is a delete endpoint, not arithmetic.
- **`posada/views.py:611`** — the streak is a counter. *Ceiling:* it cannot be recomputed or
  audited. *Upgrade:* derive it from a completion ledger — a much larger change than the guard it
  sits next to.
- **`posada/achievements.py:35`** — read-modify-write instead of `F()`. *Ceiling:* one user, and it
  runs inside the transaction. *Upgrade:* `F()` + `refresh_from_db` if there is ever real
  concurrency. *(Also: this comment is in Spanish, against the `CLAUDE.md` rule — one of the ~190
  the backlog tracks.)*

### CLI / TUI

- **`cli/tui/chess_screens.py:205`** — the engine is hardcoded to `"stockfish"`. *Ceiling:* Lc0 is
  not packaged for Debian, so the toggle offered a motor that never answered. *Upgrade:* change the
  string if another UCI engine is ever installed in the image.

### Models kept rather than dropped

- **`movies/models.py:108`** — dead model, nothing reads or writes it since the minute ledger was
  removed. *Ceiling:* it held 0 rows. *Upgrade:* drop it if a schema cleanup ever runs for its own
  reasons — a destructive migration buys nothing on its own.
