import os
import re
import tempfile

TMP = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{TMP}/test.db"
os.environ["UPLOAD_DIR"] = f"{TMP}/uploads"
os.environ["SMTP_HOST"] = ""

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlmodel import Session, select  # noqa: E402

from app.cli import create_admin  # noqa: E402
from app.db import engine, init_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Attachment, ContactMessage, QuoteRequest, QuoteResponse, Subscription  # noqa: E402

EMAIL_IN_PAGE = re.compile(r"mailto:|[\w.+-]+@[\w-]+\.[\w.]+")


def shows_email(html):  # ignores input placeholders like "you@email.com"
    return EMAIL_IN_PAGE.search(re.sub(r'placeholder="[^"]*"', "", html))

PNG = (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
       b"\x00\x00\x00\rIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82")


@pytest.fixture(scope="module")
def client():
    init_db()
    create_admin("ben", "test-password-1")
    with TestClient(app) as c:
        yield c


def csrf(c, url):
    html = c.get(url).text
    return re.search(r'name="csrf" value="([^"]+)"', html).group(1)


def quote_data(token, **over):
    d = {"csrf": token, "kind": "quote", "subject": "Fix deck", "description": "Twelve boards are rotten, please quote.",
         "address": "1 Test St, Perth WA 6000", "full_name": "Sam Customer", "phone": "0400 111 222",
         "email": "sam@example.com", "contact_method": "email", "agree": "1", "days": ["flexible"]}
    d.update(over)
    return d


@pytest.mark.parametrize("url", ["/", "/services", "/plans", "/work", "/work?cat=Carpentry", "/about", "/contact",
                                 "/terms", "/quote", "/quote?type=callout", "/subscribe/silver", "/admin/login"])
def test_pages_load(client, url):
    r = client.get(url)
    assert r.status_code == 200
    assert "Just Professional" in r.text
    assert "PayOnce" not in r.text


def test_404(client):
    r = client.get("/nope")
    assert r.status_code == 404 and "Page not found" in r.text


def test_quote_validation(client):
    t = csrf(client, "/quote")
    r = client.post("/quote", data=quote_data(t, email="bad", agree=""))
    assert r.status_code == 422
    assert "Enter a valid email" in r.text and "confirm you" in r.text


def test_quote_rejects_bad_file(client):
    t = csrf(client, "/quote")
    r = client.post("/quote", data=quote_data(t), files=[("files", ("evil.exe", b"MZ", "application/octet-stream"))])
    assert r.status_code == 422 and "only photos" in r.text


def test_quote_flow_end_to_end(client):
    t = csrf(client, "/quote")
    r = client.post("/quote", data=quote_data(t), files=[("files", ("deck.png", PNG, "image/png"))], follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"].startswith("/quote/thanks/")
    token = r.headers["location"].rsplit("/", 1)[1]
    assert "Track this request" in client.get(r.headers["location"]).text

    with Session(engine) as db:
        qr = db.exec(select(QuoteRequest).where(QuoteRequest.token == token)).one()
        assert qr.status == "new" and qr.preferred_days == "flexible"
        att = db.exec(select(Attachment).where(Attachment.request_id == qr.id)).one()
        rid, aid = qr.id, att.id

    # admin pages need login
    assert client.get("/admin", follow_redirects=False).status_code == 303
    assert client.get(f"/admin/files/{aid}", follow_redirects=False).status_code == 303
    t = csrf(client, "/admin/login")
    assert client.post("/admin/login", data={"csrf": t, "username": "ben", "password": "wrong"}).status_code == 401
    r = client.post("/admin/login", data={"csrf": t, "username": "Ben", "password": "test-password-1"}, follow_redirects=False)
    assert r.status_code == 303
    assert "Fix deck" in client.get("/admin").text
    assert "Fix deck" in client.get("/admin?q=Sam&kind=quote").text
    page = client.get(f"/admin/requests/{rid}").text
    assert "deck.png" in page or f"/admin/files/{aid}" in page
    assert client.get(f"/admin/files/{aid}").content == PNG

    # reply with a quote
    t = csrf(client, f"/admin/requests/{rid}")
    r = client.post(f"/admin/requests/{rid}/reply", data={"csrf": t, "message": "Happy to help.", "amount": "1,250.50", "send": "1"})
    assert r.status_code == 200 and "emailed to the customer" in r.text
    with Session(engine) as db:
        assert db.get(QuoteRequest, rid).status == "quoted"
        assert db.exec(select(QuoteResponse).where(QuoteResponse.request_id == rid)).one().amount_cents == 125050

    # customer sees and accepts the quote
    page = client.get(f"/track/{token}").text
    assert "$1,250.50" in page and "Accept quote" in page
    t = csrf(client, f"/track/{token}")
    client.post(f"/track/{token}/accept", data={"csrf": t})
    with Session(engine) as db:
        assert db.get(QuoteRequest, rid).status == "accepted"
    # can't accept twice
    assert client.post(f"/track/{token}/decline", data={"csrf": t}).status_code == 400

    # admin status + notes
    client.post(f"/admin/requests/{rid}/status", data={"csrf": t, "status": "scheduled"})
    client.post(f"/admin/requests/{rid}/notes", data={"csrf": t, "notes": "Bring jarrah boards"})
    with Session(engine) as db:
        qr = db.get(QuoteRequest, rid)
        assert qr.status == "scheduled" and qr.admin_notes == "Bring jarrah boards"


def test_csrf_required(client):
    r = client.post("/contact", data={"full_name": "X", "email": "x@x.com", "message": "hello there"})
    assert r.status_code == 400


def test_subscribe_and_contact(client):
    t = csrf(client, "/subscribe/bronze")
    bad = client.post("/subscribe/bronze", data={"csrf": t, "services": ["Gutter cleaning"], "full_name": "Al", "phone": "0400000000",
                                                  "email": "al@example.com", "address": "2 Road, Perth", "agree": "1"})
    assert bad.status_code == 422 and "Choose exactly 2" in bad.text
    ok = client.post("/subscribe/bronze", data={"csrf": t, "services": ["Gutter cleaning", "Window clean"], "full_name": "Al Smith",
                                                 "phone": "0400000000", "email": "al@example.com", "address": "2 Road, Perth", "agree": "1"})
    assert ok.status_code == 200 and "Bronze plan request is in" in ok.text
    r = client.post("/contact", data={"csrf": t, "full_name": "Jo", "email": "jo@example.com", "message": "Do you do fences?"})
    assert r.status_code == 200 and "message has been sent" in r.text
    with Session(engine) as db:
        assert db.exec(select(Subscription)).first().services == "Gutter cleaning, Window clean"
        assert db.exec(select(ContactMessage)).first().full_name == "Jo"
    assert "Al Smith" in client.get("/admin/subscriptions").text
    assert "Do you do fences?" in client.get("/admin/messages").text


def test_honeypot(client):
    t = csrf(client, "/quote")
    before = client.get("/admin").text.count("JPS-")
    r = client.post("/quote", data=quote_data(t, website="spam.com"), follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/"


def test_login_locks_after_5_wrong_passwords(client):
    t = csrf(client, "/admin/login")
    for _ in range(5):
        assert client.post("/admin/login", data={"csrf": t, "username": "mallory", "password": "guess"}).status_code == 401
    r = client.post("/admin/login", data={"csrf": t, "username": "mallory", "password": "guess"})
    assert r.status_code == 429 and "locked" in r.text


def test_upload_served_with_real_type_not_claimed_type(client):
    t = csrf(client, "/quote")
    fake = b"<script>alert(1)</script>"
    r = client.post("/quote", data=quote_data(t, subject="Fake png"), files=[("files", ("x.png", fake, "text/html"))],
                    follow_redirects=False)
    assert r.status_code == 303
    with Session(engine) as db:
        aid = db.exec(select(Attachment).where(Attachment.original_name == "x.png")).one().id
    client.post("/admin/login", data={"csrf": csrf(client, "/admin/login"), "username": "ben", "password": "test-password-1"})
    r = client.get(f"/admin/files/{aid}")
    assert r.headers["content-type"] == "image/png" and r.headers["x-content-type-options"] == "nosniff"
    assert client.get("/").headers["x-frame-options"] == "DENY"


def test_static_build(tmp_path):
    import subprocess
    import sys
    site = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env = {**os.environ, "BASE_PATH": "/justprowa", "UPLOAD_DIR": f"{tmp_path}/up"}
    subprocess.run([sys.executable, "build_static.py", str(tmp_path / "dist")], cwd=site, env=env, check=True)
    quote = (tmp_path / "dist/quote/index.html").read_text()
    assert 'type="button" disabled>Send my request' in quote and 'type="submit"' not in quote and 'type="file"' not in quote
    assert "Online requests are coming soon" in quote and 'href="tel:0424595086"' in quote
    assert 'href="/justprowa/static/style.css?v=3"' in quote and 'href="/justprowa/terms/#quotation"' in quote
    home = (tmp_path / "dist/index.html").read_text()
    assert 'href="/justprowa/"' in home and "/admin" not in home
    assert (tmp_path / "dist/subscribe/gold/index.html").exists() and (tmp_path / "dist/404.html").exists()
    for page in (tmp_path / "dist").rglob("*.html"):
        assert not shows_email(page.read_text()), page


def test_no_business_email_on_public_pages(client):
    for url in ["/", "/contact", "/quote", "/subscribe/silver", "/terms"]:
        assert not shows_email(client.get(url).text), url
