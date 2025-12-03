# Repository Guidelines

## Project Structure & Modules
- Entry scripts: `addPlan.py` runs the keepalive workflow (create tasks + clean last week); `getUserId.py` inspects the current account and planner layout.
- Shared code: `planner_agent.py` orchestrates Graph Planner calls, `graph_client.py` wraps token + HTTP handling, `config.py` reads env-based settings with current defaults.
- All traffic targets Microsoft Graph; secrets are configurable via env vars to avoid in-repo credentials.

## Setup, Build, and Run
- Use Python 3.10+ and a virtualenv: `python -m venv .venv && .\.venv\Scripts\activate`.
- Install dependencies: `pip install msal requests`.
- Run keepalive (create + cleanup): `python addPlan.py`.
- Fetch user data and planner topology only: `python getUserId.py`.
- Optional: capture dependencies for others with `pip freeze > requirements.txt`; keep it updated when adding libraries.

## Coding Style & Naming
- Follow PEP 8: 4-space indentation, snake_case for functions/variables, CapWords for classes (if added).
- Keep module-level constants uppercase; prefer `os.getenv` for credentials and prefixes.
- Prefer small, pure functions; keep network side effects at the edge. Add docstrings for public helpers.

## Testing Guidelines
- No automated test suite exists yet. When adding logic, create lightweight unit tests using `pytest` under a `tests/` directory (mirror module names).
- Name tests `test_<module>.py` and functions `test_<behavior>`; run via `pytest`.
- For Graph calls, stub HTTP with `responses` or `requests-mock` to avoid live calls in CI.

## Security & Configuration Tips
- Never commit client secrets or tenant IDs; rely on environment variables (`CLIENT_ID`, `CLIENT_SECRET`, `TENANT_ID`, `USER_EMAIL`).
- Validate scopes before use and log only non-sensitive metadata. Rotate credentials if accidental exposure occurs.
- Use `python-dotenv` locally if you prefer a `.env` file, but add it to `.gitignore`.

## Commit & Pull Request Guidelines
- Write present-tense, concise commits: `Add planner task creation helper`, `Improve Graph error handling`.
- Include context in PRs: purpose, manual test notes, screenshots or sample outputs for Graph interactions.
- Link relevant issues and call out any required credentials/config changes so reviewers can reproduce runs quickly.
