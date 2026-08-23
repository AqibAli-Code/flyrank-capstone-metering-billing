# BUILDLOG.md

Honest log of where AI (Claude) helped, where it was wrong, and what I actually changed. Written as I went, not reconstructed at the end.

---

## Phase 1: Pricing engine + database schema

**AI helped:** Generated the full pricing engine (`app/pricing/config.py`) and pinned test suite in one pass. The token pricing rules (cached input cheaper, reasoning bills as output, categories priced separately not summed) were correctly encoded on the first try and all 6 tests passed immediately when I ran them.

**AI helped:** Generated the SQLAlchemy models and DDL matching the brief's schema requirements, including the `UNIQUE (tenant_id, idempotency_key)` constraint that ended up being central to passing Probe 1 later.

**What I actually did:** Set up the venv, Docker, and Postgres myself in PowerShell, which surfaced a string of environment issues AI didn't (and couldn't) anticipate in advance:
- `type nul` and `touch` don't exist in PowerShell — had to switch to `New-Item`.
- Forgot to activate the venv before running `pytest`/`pip` — commands failed with "not recognized" until I ran `.\venv\Scripts\Activate.ps1`.
- Port 5432 was already taken by a native Postgres install on my machine — remapped Docker to `5433:5432` instead of touching the native service.
- Got a `ModuleNotFoundError: No module named 'app'` running `python scripts\init_db.py` directly — fixed by running it as a module (`python -m scripts.init_db`) instead of a file path, since direct-path execution doesn't add the project root to `sys.path`.

Verified everything at the source: `\dt` and `\d usage_events` directly in `psql`, not just trusting SQLAlchemy's echoed SQL.

---

## Phase 2: Idempotent metering + quota enforcement

**AI helped:** Wrote the insert-first, catch-the-constraint-violation idempotency pattern, which avoids a check-then-insert race condition I wouldn't have thought to avoid on my own.

**Where AI's first version needed a fix:** The initial `/generate` endpoint hardcoded `quantity=1` per call against a 100,000-token quota — meaning the quota boundary would never realistically trigger without 100,000 requests. Caught before testing, fixed to use the actual summed token count from the metadata (1,050 tokens per call) so a boundary test was actually reachable.

**What I actually did:** Wrote a dedicated seed script (`seed_near_quota.py`) to place a tenant 1,050 tokens under the limit so I could test the exact boundary in two calls instead of firing ~95 real requests. Verified both the `200` at the boundary and the `429` past it via curl before trusting it.

---

## Phase 3: Stripe integration — the longest debugging stretch

This phase had the most back-and-forth, and most of it was genuine infrastructure debugging, not AI writing wrong code.

**Issue 1 — persistent 404 on `/webhooks/stripe`.** Took several rounds to find. AI's early hypothesis (a router-prefix mismatch) turned out to be a red herring — I refactored the router to use `prefix="/webhooks"` + `@router.post("/stripe")`, but this produced the *exact same path* as the original code. The refactor was cosmetic and AI was upfront that it likely wasn't the real fix. The actual cause, found by checking `netstat -ano | findstr :8000`, was **two separate uvicorn processes bound to port 8000 simultaneously** — a stale one from earlier in the session was intermittently answering requests instead of my current code. Fixed by killing both PIDs and starting exactly one fresh process.

**Issue 2 — same 404 came back later.** This time the real cause was a **port mismatch**: `stripe listen` was pointed at `localhost:8001`, while `uvicorn` was running on the default `8000`. Neither AI nor I caught this until I posted a screenshot showing both terminal banners side by side — a good reminder that pasting actual terminal output, not just describing the symptom, is what actually gets bugs found.

**Issue 3 — real bug, not infrastructure.** Once webhooks reached the app, `checkout.session.completed` failed with `AttributeError: current_period_start`. This was a genuine Stripe API version issue: newer API versions moved `current_period_start`/`current_period_end` off the top-level `Subscription` object onto `subscription.items.data[]`. AI correctly diagnosed this from the traceback and the API version string, and the fix (indexing into `items.data[0]`) worked on the first try.

**What I actually did throughout:** Ran every fix myself, pasted real terminal output (not paraphrased descriptions) when things didn't work, and pushed back with the actual screenshot when a suggested fix ("everything's fine") turned out to be incomplete — the database still showed the tenant stuck on `free` even after webhooks were returning `200`, which led to catching the port mismatch.

---

## EVIDENCE.md — caught my own placeholder mistakes

Worth logging honestly: I pasted `EVIDENCE.md` for review three times before it was correct.
1. First pass had broken/unclosed code fences and only showed one half of each probe.
2. Second pass had a literal leftover `PASTE_REAL_ID` placeholder I forgot to fill in, and a duplicated `event_id` reused across two different probes (copy-paste error).
3. Third pass had Stripe IDs that were **AI's example format text**, copied verbatim instead of my real values — caught because the review flagged that the exact string matched what had been typed as an illustrative example, not something that could plausibly be a real Stripe ID.

Each round was caught before committing, not after — final version has real, verified, non-duplicated values.

---

## Overall

AI was most useful for: initial code scaffolding, spotting the Stripe API version issue from a traceback, and catching evidence-file inconsistencies I'd missed on my own re-reads. AI was least useful (or actively wrong) for: the first router-prefix "fix" that didn't address the real 404 cause, and general 404 troubleshooting that required actual terminal output before making real progress — reasoning about the code in the abstract wasn't enough to find a duplicate-process or port-mismatch bug. The pattern that actually worked was: paste real output → get a specific, falsifiable hypothesis → test it → paste the result again.