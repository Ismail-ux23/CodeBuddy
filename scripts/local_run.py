"""Run a backend command with the private project .env (no secrets printed)."""
import os
from pathlib import Path
import subprocess
import sys
from dotenv import dotenv_values

root = Path(__file__).resolve().parents[1]
env = {**os.environ, **{k: v for k, v in dotenv_values(root / '.env').items() if v is not None}}
args = sys.argv[1:]
if args and args[0] == '--test':
    args.pop(0)
    env['TEST_DATABASE_URL'] = env['DATABASE_URL'].rsplit('/', 1)[0] + '/codebuddy_test'
    env['TEST_REDIS_URL'] = 'redis://127.0.0.1:56379/4'
if not args:
    raise SystemExit('Usage: backend/.venv/bin/python scripts/local_run.py [--test] command ...')
raise SystemExit(subprocess.call(args, cwd=root / 'backend', env=env))
