#!/usr/bin/env bash
# One-command local start (macOS / Linux): ./run.sh
set -e
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
  echo "Creating virtual environment…"
  python3 -m venv .venv
fi
source .venv/bin/activate
pip install -q -r requirements.txt
if [ ! -f .env ]; then
  cp .env.example .env
  python3 - <<'PY'
import secrets, re, pathlib
p = pathlib.Path(".env"); s = p.read_text()
p.write_text(s.replace("SECRET_KEY=change-me-to-a-long-random-string", "SECRET_KEY=" + secrets.token_hex(32)))
PY
fi
if [ ! -f data/jps.db ] || ! python3 -c "
from sqlmodel import Session, select
from app.db import engine, init_db
from app.models import AdminUser
init_db()
import sys; sys.exit(0 if Session(engine).exec(select(AdminUser)).first() else 1)" 2>/dev/null; then
  echo ""
  echo "No staff login yet – let's create one (e.g. ben)."
  read -p "Username: " U
  python3 -m app.cli create-admin "$U"
fi
echo ""
echo "  Website:  http://localhost:${PORT:-8000}"
echo "  Admin:    http://localhost:${PORT:-8000}/admin"
echo "  (Ctrl+C to stop)"
echo ""
exec uvicorn app.main:app --reload --port "${PORT:-8000}"
