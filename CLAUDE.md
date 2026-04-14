# Project Instructions — MIT Discord Bot

## Git & GitHub Workflow (MANDATORY — DO NOT SKIP)

### Feature Branching
- Every task or implementation chunk gets its own short-lived feature branch
- Branch naming: `feature/<task-id>-<short-description>` (e.g. `feature/task-1-slash-commands`)
- Never batch multiple unrelated tasks onto a single branch

### Commits
- Write well-documented commits: a concise subject line plus a body explaining **why** the change was made
- Example format:
  ```
  feat: add /analyze slash command with RSI and moving averages

  Implements the /analyze command using CoinGecko OHLCV data and
  pandas-ta for technical indicator calculation. Supports a time
  range parameter (e.g. 7d, 30d, 90d).
  ```

### Pull Requests
- After completing each feature branch: push and **prompt the user to create a PR**
- Create PRs with `gh pr create` including a summary, tech notes, and a test plan checklist
- Always target `main` as the base branch
- Do not merge without user confirmation
