# Ponytail debt ledger

Every deliberate shortcut in this project is marked with a `ponytail:` comment naming its ceiling
and the trigger that should make someone revisit it. This file collects them so a deferral cannot
quietly become permanent.

> Harvested 2026-08-15 from `grep -rnE '(#|//) ?ponytail:'` plus the two markers that live in Python
> docstrings. **Re-harvested 2026-08-16** after Task 10, **2026-08-17** after the backup fix, and
> **2026-08-18**, the session that cleared both fired triggers.
> **Line numbers drift — the comment is the source of truth, this file is the index.**
> Re-run the harvest rather than trusting the numbers below. Use a bare `grep -rn 'ponytail:'`:
> the `(#|//)`-anchored version **misses every marker written in a docstring or a KDoc**, which is
> **three of the thirteen** (bare grep 13, anchored 10 — counted 2026-08-18), including the one
> on `ColaStore.respaldar` added the day that line was written.

**13 markers in the code · 1 with no trigger · 0 whose trigger has already fired · 4 discharged.**

> **2026-08-18:** the two fired triggers are gone — one discharged, one narrowed to what is still
> actually unproven. Line numbers below drifted again (`AssetStore` 188 → 211); re-run the harvest.

## Discharged

- **`ColaStore.kt` — the MediaStore round trip.** *Upgrade named:* "verify it by hand once Task 10
  makes a capture reachable." Task 10 did, on 2026-08-17, and **the answer was no** — the marker
  was promoted to a 🔴 defect rather than ticked. **Fixed the same day:** the row is created once
  and its `Uri` remembered in prefs, and the growth is over — **verified on the device 2026-08-18**:
  two real captures, one new MediaStore row, written through the remembered `Uri`. Discharged as a
  *deferral*, and it
  earned the rule it leaves behind: **a deferral hides a defect until something forces it open.**
  It was the stated justification for a decision for three days. A narrower marker replaces it, on
  the stale-`Uri` case, with a trigger that can actually fire.

- **`bunker_core/static/movil/queue.js:8`** — localStorage instead of IndexedDB, flushed from the
  page rather than the service worker. *Upgrade named:* "when captures must sync without the app
  being opened." **Done 2026-08-16, Task 10.** The store did not become better; it stopped being
  the only one. `queue.js` is now a facade over two backends — native SQLite through `Puente` inside
  the APK, localStorage in a plain browser at `/movil/` — and the marker was deleted rather than
  reworded, which is what discharging one looks like.

- **`android/…/MainActivity.kt` — the exact-alarm ask that had no way back.** *Upgrade named:*
  "a banner in the WebView (Task 10)". Task 10 landed on 2026-08-16 without it; **built 2026-08-18**
  as a fourth key on the `estado()` envelope plus `Puente.pedirAlarmaExacta`, and the banner is
  verified in a real browser across all five shapes the key can take — missing, granted, revoked,
  absent, missing again. The automatic ask stays one-shot and pref-guarded on purpose: the two
  paths must not be able to un-spend each other.

- **`android/…/Transmisor.kt` — `postReal` "deliberately untested".** *Upgrade named:* "Task 8's
  flush on the phone", which ran on 2026-08-15 and left the marker owed. **Paid 2026-08-18:** the
  leaked connection its twin `AssetStore.leerReal` was fixed for on 2026-08-15 was indeed there —
  `disconnect()` sat after three throwing calls, and `vaciar` swallows the exception and moves on,
  so a queue of N captures leaked N connections per flush **with no link, which is this app's
  normal condition**. Now in a `finally`, with the first check in the class that opens a real
  socket. Not fully discharged: a NARROWER marker replaces it, on the timeouts, which no unit test
  can reach. **Two things that check does not buy, against what the first draft of this entry
  claimed:** the leak itself is not observable from a unit test, and the check runs on the JVM's
  `HttpURLConnection` while the phone runs OkHttp's — with `usesCleartextTraffic="false"` making
  its `http://127.0.0.1` a URL production never sees. Both are read, not measured, and both
  comments now say so.

## Triggers that have already fired

**None, as of 2026-08-18.** Both entries that stood here were closed in one pass; keep the heading,
because an empty section is the only way to see that it went empty.

## No trigger — the one that rots silently

- **`disquera/models.py:102`** `no-trigger` — a dead model kept rather than dropped after the minute
  ledger was removed (2026-08-14). *Ceiling:* nothing reads or writes it. *Upgrade:* **none named.**
  Its twin at `movies/models.py:108` says "drop it if a schema cleanup ever runs for its own
  reasons"; this one was left half-written. Copy that sentence into it and it stops rotting.

## The rest

### Android (the APK)

- **`AssetStore.kt:211`** — the fetch checks the response code now, but nothing checks *content*.
  *Ceiling:* a 2xx carrying the wrong body is indistinguishable from a good one, and
  `hayGeneracionValida` only asks whether the files are non-empty. *Upgrade:* a hash or a
  content-type check, the day an asset arrives corrupted with a 200.
- **`ColaStore.respaldar()`** *(new 2026-08-17, replaces the discharged one above)* — a `Uri` that
  goes stale, because the user deleted the file from `Documents/`, silently stops backing up for
  ever. *Ceiling:* no retry, **deliberately** — a retry that re-inserts turns a full disk into the
  exact unbounded growth this fix removed. *Upgrade:* the day something actually reads the backup,
  because **nothing calls `leerRespaldo()` today** — grep the whole tree and it has no callers at
  all. That fact, not the MediaStore ownership rule, is the real reason the backup restores nothing.
- **`Transmisor.kt`** *(new 2026-08-18, narrower than the one it replaces)* — the connect and read
  timeouts, 10 s and 15 s, are numbers nobody has watched expire. *Ceiling:* a link that is up but
  unusable — a captive portal, the laptop suspended mid-request — is exactly what they exist for
  and exactly what no check reaches, because a mock cannot make time pass. *Upgrade:* measure them
  the day a flush is seen hanging rather than failing.
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
