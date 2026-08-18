# Ponytail debt ledger

Every deliberate shortcut in this project is marked with a `ponytail:` comment naming its ceiling
and the trigger that should make someone revisit it. This file collects them so a deferral cannot
quietly become permanent.

> Harvested 2026-08-15 from `grep -rnE '(#|//) ?ponytail:'` plus the two markers that live in Python
> docstrings. **Re-harvested 2026-08-16** after Task 10, and **2026-08-17** after the backup fix.
> **Line numbers drift — the comment is the source of truth, this file is the index.**
> Re-run the harvest rather than trusting the numbers below. Use a bare `grep -rn 'ponytail:'`:
> the `(#|//)`-anchored version **misses every marker written in a docstring or a KDoc**, which is
> three of the fourteen — including the one on `ColaStore.respaldar` added the day this was written.

**14 markers in the code · 1 with no trigger · 2 whose trigger has already fired · 2 discharged.**

## Discharged

- **`ColaStore.kt` — the MediaStore round trip.** *Upgrade named:* "verify it by hand once Task 10
  makes a capture reachable." Task 10 did, on 2026-08-17, and **the answer was no** — the marker
  was promoted to a 🔴 defect rather than ticked. **Fixed the same day:** the row is created once
  and its `Uri` remembered in prefs, and the growth is over. Discharged as a *deferral*, and it
  earned the rule it leaves behind: **a deferral hides a defect until something forces it open.**
  It was the stated justification for a decision for three days. A narrower marker replaces it, on
  the stale-`Uri` case, with a trigger that can actually fire.

- **`bunker_core/static/movil/queue.js:8`** — localStorage instead of IndexedDB, flushed from the
  page rather than the service worker. *Upgrade named:* "when captures must sync without the app
  being opened." **Done 2026-08-16, Task 10.** The store did not become better; it stopped being
  the only one. `queue.js` is now a facade over two backends — native SQLite through `Puente` inside
  the APK, localStorage in a plain browser at `/movil/` — and the marker was deleted rather than
  reworded, which is what discharging one looks like.

## Triggers that have already fired

The condition each comment names as the moment to revisit has happened.

- **`android/…/Transmisor.kt`** — `postReal` deliberately untested; every check injects `poster`
  instead. *Ceiling:* the socket itself, `instanceFollowRedirects`, and `disconnect()` not being in
  a `finally` are all unproven. *Upgrade:* "Task 8's flush on the phone, which is the first time
  this runs for real" — **that flush ran on 2026-08-15 and reached Django**. Still owed, and now
  pointedly: the identical defect in `AssetStore.leerReal` — a leaked connection on the failure
  path, which is the common one — was found and fixed on 2026-08-15. `postReal` has not been read
  for it.
- **`android/…/MainActivity.kt`** — the exact-alarm request is sent once and the answer remembered.
  *Ceiling:* whoever declines keeps the inexact alarm for ever, with no way back. *Upgrade named:*
  "a banner in the WebView (Task 10)". **Task 10 landed on 2026-08-16 and the banner was not
  built.** The WebView now exists, so the stated upgrade is available and simply owed — the chip
  already grew a long-press for the asset escape hatch and is the obvious place for it.

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
- **`ColaStore.respaldar()`** *(new 2026-08-17, replaces the discharged one above)* — a `Uri` that
  goes stale, because the user deleted the file from `Documents/`, silently stops backing up for
  ever. *Ceiling:* no retry, **deliberately** — a retry that re-inserts turns a full disk into the
  exact unbounded growth this fix removed. *Upgrade:* the day something actually reads the backup,
  because **nothing calls `leerRespaldo()` today** — grep the whole tree and it has no callers at
  all. That fact, not the MediaStore ownership rule, is the real reason the backup restores nothing.
- **`MainActivity.kt`** — moved up to "Triggers that have already fired": Task 10 built the WebView
  on 2026-08-16 without building the banner.
- **`android/app/build.gradle.kts`** *(new 2026-08-16, Task 10)* — `copiarAssets` reproduces
  Django's template render with three string substitutions instead of invoking it. *Ceiling:* a
  fourth template tag in `app.html` ships raw and breaks the **bundled** copy. *Upgrade:* only if a
  phone ever has to live on bundled assets for long — the first successful contact with the server
  replaces them with Django's own render, so the drift is self-healing. Guarded meanwhile by
  diffing the bundled file against `/movil/asset/app.html`; they are identical bar the CSRF value.

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
