---
name: production-readiness
description: Use when reviewing a codebase for launch readiness, monetization viability, or robustness across data persistence, payment/fulfillment mapping, security, and feature completeness — before GTM decisions, after long build phases, when a feature inventory alone isn't enough, or when the user worries that money/data flows are "correctly and safely mapped."
---

# Production-Readiness Methodology

A methodology for auditing a codebase for launch and monetization readiness. Born from real audits where a feature inventory marked a payment path "safe" — and tracing the **actual call signatures** proved it was broken in production. The lesson at the core of this skill:

> **A feature is not complete because it exists. It is complete because its wiring is traced end-to-end against real signatures.**

## When to use
- Before a GTM / launch / pricing decision.
- After a long build phase — "what do we actually have, and does it work?"
- User worries about money, data, or safety mapping.
- You need a defensible answer to "is this ready to ship / monetize / launch?"

## The 7-section output (write to a tracked file)
1. **Feature & Capability Inventory** — each item tagged Complete / Partial / Missing + `file:line` evidence. Partial = real-but-one-path, wired-only-in-dev, or stubbed on a money/lifecycle route.
2. **Gap Analysis** — Critical (blocks every model) / Model-specific / Nice-to-have.
3. **Competitive Feature Gap** — `Competitor feature | Our status | What we must add`. **Never assert competitor specifics from memory → flag "requires current web research."** Seed with the user's strategic categories.
4. **Unused Capabilities** — built but not wired to a user or money path.
5. **Prioritized Remediation** — P0/P1/P2/P3, each with `file:line` + one-line reason.
6. **Monetization Path Scan** — one line per path, Viability Strong / Possible / Weak / Not-Viable + reason.
7. **This-codebase additional paths** — only paths evidenced by the code itself (cited), not brainstormed.

## Additional sections (when applicable)
8. **Output Quality Assessment** — For codebases that produce creative/content output: rate each production stage on a 1-10 quality scale with evidence.
9. **Service Integration Completeness** — For codebases with multiple services: verify each service is wired into the PRIMARY production pipeline, not just registered in a registry.
10. **Claim-vs-Reality Audit** — For every docstring/comment claiming "AI-powered", "ML-based", "automated", or "intelligent": verify the implementation matches the claim.
11. **Shared Service Wiring Audit** — For codebases using external/shared packages: verify each imported symbol actually exists in the source package, is actually used after import, and is wired to a user-facing endpoint.
12. **Runtime Correctness Audit** — For codebases with complex import trees: verify all stdlib API usage is correct, all module-level variables are defined before use, and all verification functions are actually called.

## The discipline (do not skip)
- **Cite `file:line` for every capability claim. Uncited claims are OMITTED, not weakened.** This single rule prevents the "looks complete" failure that a feature inventory invites.
- **Trace signatures, not docstrings.** A service with a great docstring can have a method body that rejects the call. Open every method the money/data path calls and confirm the arguments match the *real* signature.
- **Read the actual file.** Never trust that a file "does X" because it exists or because it imports X. Open it; read the lines. Metadata and docstrings lie; code doesn't.
- **Dev ≠ prod.** A flow that passes under sqlite/tests can fail under postgres/k8s. Check: `DATABASE_URL` wiring, mount/volume persistence, placeholder dialects, route registration order, env-var names, ephemeral container stores.
- **Don't speculate competitors.** Flag for live web research instead of asserting figures from memory.
- **Never present 80% as 100%.** State Done vs Skipped explicitly with reasons.

---

## Audit Techniques

### 1. Output-validation trace
For every service that *produces* output (render / build / generate / export / normalize / compose / assemble), **invoke the public entry point** and **inspect the returned object's actual shape and values** — not just that it returned. When the service produces **N variants**, assert the variants **differ as intended** and do **not** cross-contaminate. Compare the produced shape against the **real consumer/importer schema**. Check the **gateway predicate**: `is_valid = len(errors) == 0` is a lie if `errors` is never appended to. Check that **unresolvable required inputs fail loudly**, not fall through to a default.

### 2. Test-quality / entry-point-coverage trace
Tests that pass can give false readiness if they never exercise the **public entry point** — only its helpers. For every capability under audit, open the test file and ask: **does any test invoke the public entry point** and assert on its **output or side effect**? Apply the **deletion test**: if you deleted the method under audit, would *any* test fail? If not, the capability is untested.

### 3. Business-model feature-completeness trace
Identify the product's **documented business/monetization model**. For each load-bearing capability, confirm it **exists as *behavior*, not just as copy or a config field**. Distinguish **claim vs close**: a template that *parks* a draft at `pending_review` is a *claim*; the webhook receiver that actually approves/sends/audits is the *close*. Missing close = incomplete capability.

### 4. Multi-output differentiation trace
List every `(input, output-variant)` pair. Confirm the variant is **actually selected/produced** — not a fallback that emits the whole input. Assert variant **isolation**: variant A's output must not contain variant B's identifiers, tokens, or tenant data.

### 5. Dead-DDL / orphaned-persistence trace
List every storage object created. For each, grep for **writes** and **reads**. A store with CREATE but no INSERT, or CREATE+INSERT but no SELECT, is orphaned or write-only.

### 6. Live-run / end-to-end invocation trace
Identify every **critical end-to-end path**. **Invoke the public entry point** with realistic parameters — not a unit test with every dependency mocked. Watch for **runtime signature mismatches**, **missing/config attributes**, **import failures** silently caught, **timeout / hang**, and **success/failure output** quality.

### 7. Stub-method trace
Read the method body — not just the signature. Look for: `logger.info(...)` followed by `return True` with no actual work. Look for: `# This would use ...` / `# For now, log ...` / `# TODO: implement ...` comments. Trace to the external boundary: does the method actually call an external API, write to a DB, or mutate state?

### 8. Integration-layer trace
For every external-system integration: connection is real, resources are actually created, data is actually transferred, transitions use correct identifiers, reconnection exists, concurrency is safe.

### 9. Service-level review
Every public method on a critical path has real implementation; no bare `except: pass` on money/data/integration paths; external-system methods have timeout + retry; shared-state access has concurrency protection.

### 10. Test-health trace (run the suite)
**Never claim "tests pass" without running them.** Run the full test suite and count passed/failed/errors. Fix our regressions immediately. Document pre-existing failures.

### 11. Code-coherence trace (entry points use real implementations)
Map every entry point (CLI commands, route handlers, scheduler jobs) to the services they call. Verify the **full call chain** from entry point → service → output. Check for duplicate implementations.

### 12. Dead-code / duplicate-implementation trace
For each major capability, list every file that implements it. Determine which is wired to an entry point, which is actually called in production.

### 13. Test-infrastructure trace (schemas match production)
Compare test fixture schemas column-by-column with production schema. Verify constructor parameters in tests match the real service's `__init__` signature.

### 14. Dead-config trace
List every field in every config dataclass/object. For each field, grep for `self.config.<field_name>` or `config.<field_name>` outside its definition. If zero usages, it's dead config.

### 15. Output-quality trace
Rate each production stage 1-10 with specific evidence. 1-2: Hardcoded/stub/placeholder. 3-4: Template-based or keyword-only. 5-6: Functional but basic. 7-8: Good quality with real dynamic generation. 9-10: Professional-grade with full pipeline integration.

### 16. Service-integration trace (disconnected quality services)
List all "quality" or "enhancement" services. For each, grep for calls from the PRIMARY production pipeline. If a quality service has zero callers from the production path, it's disconnected.

### 17. Claim-vs-reality trace (fake AI/ML claims)
Grep for claim words: `AI`, `ML`, `machine learning`, `intelligent`, `automated`, `smart`, `neural`, `deep learning`, `predictive`, `NLP`. Read the method body. Does it use a real ML model, real AI, or just keyword counting, regex matching, template strings, hardcoded values?

### 18. Minimum-viable-quality gate
For each user-facing output, ask: *"Would a paying customer be satisfied with this?"* Set minimum quality thresholds per output type. If an output fails the minimum threshold, mark the capability as "Stub" even if it technically works.

### 19. Shared-vs-local service check (import shadowing)
Check if the project has a directory that shadows a known canonical package name. For every shadowed module, compare local vs canonical. Verify which canonical services are imported but never used.

### 20. Verification-wiring trace (function defined but never called)
Grep for all `def _verify_*`, `def _validate_*`, `def _check_*` functions. For each, grep for **callers** outside the function definition. If zero callers exist, the verification is dead code.

### 21. Dead-import / unused-symbol trace
For every `from X import Y`, grep the rest of the file for `Y`. If `Y` appears only in the import line, it's unused, dead code.

### 22. Silent-error trace (exceptions swallowed)
Grep for `except:` or `except Exception:` followed by `pass`. On critical paths, the silent swallow is a bug.

### 23. Runtime correctness: stdlib API usage
Check `hmac.new()` → should be `hmac.HMAC()`. Check `timezone.utc` import. Verify stdlib symbols exist in source module.

### 24. Credential hygiene trace
Grep config files for `://user:pass@`, `PASSWORD=`, `SECRET_KEY=`, `API_KEY=`. Check `.env` is in `.gitignore`.

### 25. In-memory-persistence trace
Grep for module-level `_store = {}`, `_items = []`, `_cache = {}`. User-created data must be stored in a database, not in memory.

### 26. Import smoke trace
Attempt to import every module in the project and report failures. Fix all actionable failures.

### 27. UI-to-backend wiring trace
For every API call in the frontend, verify the backend route exists. Verify response shape matches frontend expectations.

### 28. Route/endpoint collision trace
Grep all route patterns and check for duplicates.

### 29. Schema-mismatch trace
For every query, verify all referenced fields exist in the schema.

### 30. N+1 query trace
For every `for item in collection:` block, check if there's a DB query inside the loop. Fix with `WHERE IN` or subquery joins.

### 31. Task/job error-propagation trace
For every task/job function, find all `except` blocks. If the `except` block returns a value instead of re-raising, errors are swallowed.

### 32. Search-goal specificity trace
Check if queries are decomposed by goal (pricing, pain points, competitors, etc.). Verify extraction methods match the research goals.

### 33. Output validation checklist (HTML / document / API response)
Run structural, accessibility, performance, security, and content quality checks.

### 34. Python-version compat trace
Check runtime Python version against `requires-python`. Grep for 3.10+ features requiring compat shims.

### 35. Test-client / conftest env mismatch trace
Compare test fixture Model(**kwargs) against the model's actual `__init__` or SQLAlchemy schema.

### 36. Test-database isolation trace
Check whether test data is rolled back between tests. Check that fixtures generate unique values per test.

### 37. Security-scan integration trace
Run `pip-audit`, `bandit -r . -ll -ii`. Fix SQL injection, missing timeouts, hardcoded credentials, `except: pass` blocks.

### 38. Linter-config / stash trace
Check `pyproject.toml` for `ignore` settings. Every ignored rule should have a comment explaining why. Run `ruff check . --select E` and fix all remaining errors.

---

## Red flags — STOP and re-verify
- You're about to write "Complete" for a path you have not traced end-to-end.
- A capability claim has no `file:line`.
- You're stating a competitor figure from memory.
- "It imports X" — but you haven't confirmed X exports what's imported.
- **A method has a real signature and is called, but you haven't read its body** — it may be a stub that logs and returns `True`.
- **A config field exists but you haven't grepped for its usage** — it may be dead config.
- **An external-system integration method returns `True`** — confirm it makes a real API call.
- **A test passes but the test itself mocks the real boundary** — the real boundary may be a stub.
- **You have never invoked the critical end-to-end path** — every trace technique can pass while the runtime call chain fails.
- **A service produces N variants and you've confirmed each "loads" but not that they differ** — collapsed/identical variants are a defect.
- **Quality/enhancement services exist but aren't wired to the production pipeline** — grep for callers from the primary production flow.
- **A docstring claims "AI-powered" but the body uses keyword counting or templates** — read the implementation, not the documentation.
- **A method uses `hash(input) % len(templates)` or f-strings with hardcoded templates** — this is template selection, not generation.
- **An in-memory store is used for user data that must persist** — module-level dicts lose all data on restart.
- **A local directory shadows a canonical shared package** — verify resolution order.
- **A navigation/UI element links to a route that doesn't exist** — check every link against registered routes.
- **A route is defined but the blueprint/module is never registered** — orphan routes are dead code.
- **Two routes define the same URL pattern** — the second is silently shadowed.
- **A stub returns `[]`, `{}`, or `None` from a user-facing API** — the user sees an empty page with no error.
- **A verification function is defined but never called** — the protection it provides doesn't exist.
- **A module defines `_logger` but uses `logger` (or vice versa)** — inconsistent naming causes `NameError`.
- **A Pydantic/validation model is defined but the route handler accepts `dict`** — the validation is bypassed.
- **A task/job catches exceptions and returns an error dict** — the task appears successful even when it failed.
- **An N+1 query hides inside a list comprehension or for-loop** — per-row queries multiply latency.
- **A `try/except` block silently swallows errors** — `except Exception: pass` hides failures.
- **A shared/external service is imported but never used** — dead import.
- **Hardcoded credentials in config files** — `alembic.ini`, `docker-compose.yml`, `.env` with embedded passwords.
- **A frontend API call targets a route that doesn't exist or returns wrong shape** — the UI appears to work but data is missing.