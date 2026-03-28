---
name: dh-lottery-cli
description: Prepare and run the DH Lottery Playwright buyer in this workspace. Use when the user wants to bootstrap the local runtime, validate the lottery .env configuration, debug the CLI flow, or execute dhlottery.py from this repository.
---

# DH Lottery CLI

Use this skill for the local DH Lottery repository in the current workspace.

## Safety

- Treat an actual purchase as a real-money action.
- Do not run a purchase unless the user explicitly asks to buy or confirms after you explain that it will place a real order.
- Prefer a config check before the first real run or whenever the user asks for setup, validation, or debugging.

## Workflow

1. Prepare or repair the runtime with:

```bash
python "{baseDir}/scripts/run_lottery.py" --check-config
```

This wrapper auto-creates `<repo>/venv`, installs `requirements.txt`, and installs Playwright Chromium if needed.

2. Validate configuration without purchasing:

```bash
python "{baseDir}/scripts/run_lottery.py" --check-config
```

3. Run a real purchase only after explicit confirmation:

```bash
python "{baseDir}/scripts/run_lottery.py" --games 5
```

4. Use `--headed` when the user wants to debug the browser flow visually.

## Inputs

- Default dotenv file: `<repo>/.env`
- Required values: `DHLOTTERY_ID`, `DHLOTTERY_PW`
- Optional values: `DHLOTTERY_GAMES`, `DHLOTTERY_INTERVAL_DAYS`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`
- Override dotenv location with `--env-file <path>`
- Skip dotenv loading with `--no-dotenv`

## Outputs

- `--check-config` prints a safe summary without the password.
- Real runs print the purchase result and ticket lines.
- Failures return a non-zero exit code.

Read `{baseDir}/references/runtime.md` only when you need the variable list or wrapper details.
