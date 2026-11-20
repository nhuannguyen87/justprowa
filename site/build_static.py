"""Save the public pages as plain HTML for GitHub Pages (no server: forms open the visitor's email app).

  BASE_PATH=/justprowa python build_static.py dist
"""
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

os.environ["STATIC_SITE"] = "1"
os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/build.db"

from fastapi.testclient import TestClient  # noqa: E402

from app.content import PLANS  # noqa: E402
from app.main import APP_DIR, app  # noqa: E402

PAGES = ["", "services", "plans", "work", "about", "contact", "terms", "quote"] + [f"subscribe/{p['key']}" for p in PLANS]
LINK = re.compile(r'(href|src)="/(?!/)([^"?#]*)([^"]*)"')


def relink(html: str, base: str) -> str:
    """Site-root links -> links under the Pages base path, with a trailing slash for page folders."""
    def fix(m):
        attr, path, rest = m.groups()
        if path and not path.startswith("static/"):
            path = path.rstrip("/") + "/"
        return f'{attr}="{base}/{path}{rest}"'
    return LINK.sub(fix, html)


def build(out: Path, base: str) -> None:
    shutil.rmtree(out, ignore_errors=True)
    shutil.copytree(APP_DIR / "static", out / "static")
    with TestClient(app) as c:
        for page in PAGES:
            r = c.get(f"/{page}")
            assert r.status_code == 200, (page, r.status_code)
            (out / page).mkdir(parents=True, exist_ok=True)
            (out / page / "index.html").write_text(relink(r.text, base))
        (out / "404.html").write_text(relink(c.get("/404-page").text, base))
    (out / ".nojekyll").touch()


if __name__ == "__main__":
    build(Path(sys.argv[1] if len(sys.argv) > 1 else "dist"), os.getenv("BASE_PATH", "").rstrip("/"))
