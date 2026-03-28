# Runtime Notes

## Repository assumptions

- The skill lives under `<workspace>/skills/dh-lottery-cli`.
- The repository root is resolved automatically from the script location.
- The entrypoint is `dhlottery.py` in the repository root.

## Runtime bootstrap

- `scripts/ensure_runtime.py` creates `<repo>/venv` when missing.
- It installs `requirements.txt`.
- It runs `python -m playwright install chromium`.

## Execution wrapper

- `scripts/run_lottery.py` prefers the repository virtualenv.
- It auto-runs `ensure_runtime.py` when the virtualenv is missing or broken.
- It forwards command-line flags to `dhlottery.py`.

## Dotenv and environment variables

Required:

- `DHLOTTERY_ID`
- `DHLOTTERY_PW`

Optional:

- `DHLOTTERY_GAMES`
- `DHLOTTERY_INTERVAL_DAYS`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

Default behavior:

- `dhlottery.py` loads `<repo>/.env` automatically when it exists.
- Use `--env-file <path>` to load a different dotenv file.
- Use `--no-dotenv` to skip dotenv loading and rely on process environment only.

## Safe commands

Check configuration without buying:

```bash
python "{baseDir}/scripts/run_lottery.py" --check-config
```

Run a real purchase after explicit confirmation:

```bash
python "{baseDir}/scripts/run_lottery.py" --games 5
```
