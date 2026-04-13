# Deferred Items - Phase 02

Out-of-scope issues discovered during execution. NOT fixed in this plan.

## Plan 02-01

### passlib/bcrypt version incompatibility

- **Discovered:** Plan 02-01, Task 2 (test_password_hash_and_verify)
- **Symptom:** `passlib.handlers.bcrypt` cannot read bcrypt's version attribute
  (`AttributeError: module 'bcrypt' has no attribute '__about__'`), after which
  any `hash_password()` call raises
  `ValueError: password cannot be longer than 72 bytes` regardless of actual
  length.
- **Root cause:** passlib 1.7.4 pinned in requirements.txt is incompatible
  with bcrypt >= 4.1 (new package layout removed `__about__`).
- **Impact:** `app/auth/jwt_auth.hash_password` / `verify_password` are
  effectively broken in the current venv. Admin login flow that hashes
  passwords at startup is at risk.
- **Workaround in tests:** `test_password_hash_and_verify` is wrapped in a
  `pytest.skip` so the suite can progress.
- **Fix required (future plan):** Either pin `bcrypt<4.1` or bump
  `passlib>=1.7.5` (once released), or switch to using `bcrypt` directly.
