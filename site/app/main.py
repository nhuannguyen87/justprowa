"""Just Professional Services – website + admin (FastAPI)."""
import mimetypes
import re
import time
import uuid
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Annotated, Optional
from zoneinfo import ZoneInfo

from fastapi import BackgroundTasks, Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, col, func, or_, select
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.sessions import SessionMiddleware

from . import content, payments
from .config import settings
from .db import get_session, init_db
from .emailer import send_email
from .icons import icon
from .models import (AdminUser, Attachment, ContactMessage, QuoteRequest, QuoteResponse, Subscription, now_utc)
from .security import AdminRequired, check_csrf, csrf_token, current_admin, verify_password

APP_DIR = Path(__file__).resolve().parent
TZ = ZoneInfo(settings.TIMEZONE)
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

@asynccontextmanager
async def lifespan(_app):
    init_db()
    yield


app = FastAPI(title=settings.SITE_NAME, docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY, same_site="lax",
                   https_only=settings.SITE_URL.startswith("https"), max_age=60 * 60 * 12)
app.mount("/static", StaticFiles(directory=APP_DIR / "static"), name="static")
templates = Jinja2Templates(directory=APP_DIR / "templates")


@app.middleware("http")
async def security_headers(request: Request, call_next):
    resp = await call_next(request)
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")  # browsers must trust our file types, not guess
    resp.headers.setdefault("X-Frame-Options", "DENY")            # no clickjacking via iframes
    resp.headers.setdefault("Referrer-Policy", "same-origin")     # tracking links never leak to other sites
    return resp

DB = Annotated[Session, Depends(get_session)]


# ---------------------------------------------------------------- template helpers
def local(dt: Optional[datetime], fmt: str = "%d %b %Y, %-I:%M %p") -> str:
    if not dt:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(TZ).strftime(fmt)


def money(cents: Optional[int]) -> str:
    return "" if cents is None else f"${cents / 100:,.2f}"


def fmt_days(value: str) -> str:
    if not value:
        return "—"
    out = []
    for d in value.split(","):
        try:
            out.append(date.fromisoformat(d).strftime("%a %d %b"))
        except ValueError:
            out.append(d.capitalize())
    return ", ".join(out)


templates.env.globals.update(icon=icon, biz=settings.BUSINESS, c=content, payments_enabled=payments.enabled,
                             static=settings.STATIC_SITE)
templates.env.filters.update(local=local, money=money, days=fmt_days)


def render(request: Request, name: str, status_code: int = 200, **ctx) -> HTMLResponse:
    ctx.setdefault("page", "")
    ctx["csrf"] = csrf_token(request)
    ctx["admin"] = current_admin(request)
    ctx["flashes"] = request.session.pop("flash", [])
    return templates.TemplateResponse(request, name, ctx, status_code=status_code)


def flash(request: Request, msg: str, kind: str = "ok") -> None:
    request.session.setdefault("flash", []).append({"msg": msg, "kind": kind})


def upcoming_days(n: int = 10) -> list[date]:
    d, out = datetime.now(TZ).date(), []
    while len(out) < n:
        d += timedelta(days=1)
        if d.weekday() != 6:  # skip Sundays
            out.append(d)
    return out


def clean(s: Optional[str], limit: int = 2000) -> str:
    return (s or "").strip()[:limit]


# ---------------------------------------------------------------- public pages
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return render(request, "home.html", page="home")


@app.get("/services", response_class=HTMLResponse)
def services(request: Request):
    return render(request, "services.html", page="services")


@app.get("/plans", response_class=HTMLResponse)
def plans(request: Request):
    return render(request, "plans.html", page="plans")


@app.get("/work", response_class=HTMLResponse)
def work(request: Request, cat: str = "All"):
    items = [w for w in content.WORK if cat == "All" or w[1] == cat]
    return render(request, "work.html", page="work", items=items, cat=cat,
                  cats=["All", "Handyman", "Carpentry", "Renovations", "Maintenance"])


@app.get("/about", response_class=HTMLResponse)
def about(request: Request):
    return render(request, "about.html", page="about")


@app.get("/terms", response_class=HTMLResponse)
def terms(request: Request):
    return render(request, "terms.html", page="terms")


# ---------------------------------------------------------------- quote / call-out request
@app.get("/quote", response_class=HTMLResponse)
def quote_form(request: Request, type: str = "quote"):
    kind = type if type in content.REQUEST_KINDS else "quote"
    return render(request, "quote.html", page="quote", days=upcoming_days(), form={"kind": kind}, errors={})


async def save_upload(up: UploadFile, request_id: int) -> Attachment:
    ext = Path(up.filename or "").suffix.lower()
    folder = settings.UPLOAD_DIR / str(request_id)
    folder.mkdir(parents=True, exist_ok=True)
    stored = f"{uuid.uuid4().hex}{ext}"
    size, limit = 0, settings.MAX_UPLOAD_MB * 1024 * 1024
    with open(folder / stored, "wb") as fh:
        while chunk := await up.read(1024 * 256):
            size += len(chunk)
            if size > limit:
                fh.close()
                (folder / stored).unlink(missing_ok=True)
                raise ValueError(f"{up.filename} is larger than {settings.MAX_UPLOAD_MB} MB")
            fh.write(chunk)
    return Attachment(request_id=request_id, original_name=(up.filename or stored)[:200],
                      stored_name=stored, content_type=up.content_type or "", size=size)


@app.post("/quote", response_class=HTMLResponse)
async def quote_submit(
    request: Request, bg: BackgroundTasks, db: DB,
    kind: str = Form("quote"), subject: str = Form(""), description: str = Form(""),
    address: str = Form(""), days: list[str] = Form([]), full_name: str = Form(""),
    phone: str = Form(""), email: str = Form(""), contact_method: str = Form("phone"),
    agree: str = Form(""), website: str = Form(""), csrf: str = Form(""),
    files: list[UploadFile] = File([]),
):
    check_csrf(request, csrf)
    form = dict(kind=kind, subject=clean(subject, 200), description=clean(description, 5000), address=clean(address, 300),
                days=days, full_name=clean(full_name, 120), phone=clean(phone, 40), email=clean(email, 200).lower(),
                contact_method=contact_method if contact_method in content.CONTACT_METHODS else "phone")
    if website:  # honeypot – bots fill hidden fields
        return RedirectResponse("/", status_code=303)

    files = [f for f in files if f and f.filename]
    errors = {}
    if kind not in content.REQUEST_KINDS: errors["kind"] = "Choose a request type."
    if len(form["subject"]) < 3: errors["subject"] = "Give your request a short title."
    if len(form["description"]) < 10: errors["description"] = "Tell us a bit more about the job."
    if len(form["address"]) < 5: errors["address"] = "Enter the property address."
    if len(form["full_name"]) < 2: errors["full_name"] = "Enter your full name."
    if len(re.sub(r"\D", "", form["phone"])) < 8: errors["phone"] = "Enter a valid phone number."
    if not EMAIL_RE.match(form["email"]): errors["email"] = "Enter a valid email address."
    if not agree: errors["agree"] = "Please confirm you've read the policy."
    if len(files) > settings.MAX_FILES: errors["files"] = f"Attach up to {settings.MAX_FILES} files."
    for f in files:
        if Path(f.filename).suffix.lower() not in settings.ALLOWED_EXT:
            errors["files"] = f"{f.filename}: only photos, videos (mp4/mov) or PDFs please."
    if errors:
        return render(request, "quote.html", 422, page="quote", days=upcoming_days(), form=form, errors=errors)

    valid_days = {d.isoformat() for d in upcoming_days()} | {"flexible"}
    qr = QuoteRequest(kind=kind, subject=form["subject"], description=form["description"], address=form["address"],
                      preferred_days=",".join(d for d in days if d in valid_days), full_name=form["full_name"],
                      phone=form["phone"], email=form["email"], contact_method=form["contact_method"])
    db.add(qr); db.commit(); db.refresh(qr)
    try:
        for f in files:
            db.add(await save_upload(f, qr.id))
    except ValueError as e:
        db.rollback()
        for a in db.exec(select(Attachment).where(Attachment.request_id == qr.id)).all():
            db.delete(a)
        db.delete(qr); db.commit()
        errors["files"] = str(e)
        return render(request, "quote.html", 422, page="quote", days=upcoming_days(), form=form, errors=errors)
    db.commit()

    track = f"{settings.SITE_URL}/track/{qr.token}"
    bg.add_task(send_email, settings.NOTIFY_EMAIL, f"New {content.REQUEST_KINDS[kind].lower()} {qr.ref}: {qr.subject}",
                f"{qr.full_name} ({qr.phone}, {qr.email}) sent a {content.REQUEST_KINDS[kind].lower()}.\n\n"
                f"Address: {qr.address}\nPreferred days: {fmt_days(qr.preferred_days)}\n"
                f"Contact by: {content.CONTACT_METHODS[qr.contact_method]}\nFiles: {len(files)}\n\n{qr.description}\n\n"
                f"Open in admin: {settings.SITE_URL}/admin/requests/{qr.id}", reply_to=qr.email)
    bg.add_task(send_email, qr.email, f"We've received your request {qr.ref} – Just Professional Services",
                f"Hi {qr.full_name.split()[0]},\n\nThanks for contacting Just Professional Services. "
                f"We've received your request \"{qr.subject}\" (ref {qr.ref}) and will be in touch soon.\n\n"
                f"You can check its status and see our reply here:\n{track}\n\n"
                f"Ben 0424 595 086 · Ash 0473 634 321\nJust Professional Services")
    return RedirectResponse(f"/quote/thanks/{qr.token}", status_code=303)


@app.get("/quote/thanks/{token}", response_class=HTMLResponse)
def quote_thanks(request: Request, token: str, db: DB):
    qr = db.exec(select(QuoteRequest).where(QuoteRequest.token == token)).first()
    if not qr:
        raise HTTPException(404)
    return render(request, "thanks.html", page="quote", qr=qr)


# ---------------------------------------------------------------- customer tracking page
def get_by_token(db: Session, token: str) -> QuoteRequest:
    qr = db.exec(select(QuoteRequest).where(QuoteRequest.token == token)).first()
    if not qr:
        raise HTTPException(404, "Request not found")
    return qr


@app.get("/track/{token}", response_class=HTMLResponse)
def track(request: Request, token: str, db: DB):
    qr = get_by_token(db, token)
    responses = sorted(qr.responses, key=lambda r: r.created_at)
    latest_quote = next((r for r in reversed(responses) if r.amount_cents is not None), None)
    return render(request, "track.html", qr=qr, responses=responses, latest_quote=latest_quote)


@app.post("/track/{token}/{decision}")
def track_decision(request: Request, token: str, decision: str, bg: BackgroundTasks, db: DB, csrf: str = Form("")):
    check_csrf(request, csrf)
    qr = get_by_token(db, token)
    if decision not in {"accept", "decline"} or qr.status != "quoted":
        raise HTTPException(400, "This quote can't be changed now.")
    qr.status = "accepted" if decision == "accept" else "declined"
    qr.updated_at = now_utc()
    db.add(qr); db.commit()
    word = "ACCEPTED" if decision == "accept" else "declined"
    bg.add_task(send_email, settings.NOTIFY_EMAIL, f"{qr.ref} quote {word} by {qr.full_name}",
                f"{qr.full_name} {word} the quote for \"{qr.subject}\".\n\n{settings.SITE_URL}/admin/requests/{qr.id}")
    flash(request, "Thanks — we've let the team know you accepted the quote. We'll be in touch to schedule the work."
          if decision == "accept" else "Thanks for letting us know. Your quote has been marked as declined.")
    return RedirectResponse(f"/track/{token}", status_code=303)


# ---------------------------------------------------------------- subscriptions
@app.get("/subscribe/{plan}", response_class=HTMLResponse)
def subscribe_form(request: Request, plan: str):
    if plan not in content.PLANS_BY_KEY:
        raise HTTPException(404)
    return render(request, "subscribe.html", page="plans", plan=content.PLANS_BY_KEY[plan], form={}, errors={})


@app.post("/subscribe/{plan}", response_class=HTMLResponse)
def subscribe_submit(
    request: Request, plan: str, bg: BackgroundTasks, db: DB,
    services: list[str] = Form([]), full_name: str = Form(""), phone: str = Form(""), email: str = Form(""),
    address: str = Form(""), notes: str = Form(""), agree: str = Form(""), website: str = Form(""), csrf: str = Form(""),
):
    check_csrf(request, csrf)
    if plan not in content.PLANS_BY_KEY:
        raise HTTPException(404)
    p = content.PLANS_BY_KEY[plan]
    if website:
        return RedirectResponse("/", status_code=303)
    allowed = {label for _, label in content.PLAN_SERVICES}
    chosen = [s for s in services if s in allowed]
    form = dict(services=chosen, full_name=clean(full_name, 120), phone=clean(phone, 40), email=clean(email, 200).lower(),
                address=clean(address, 300), notes=clean(notes, 2000))
    errors = {}
    if len(chosen) != p["services"]: errors["services"] = f"Choose exactly {p['services']} services for the {p['name']} plan."
    if len(form["full_name"]) < 2: errors["full_name"] = "Enter your full name."
    if len(re.sub(r"\D", "", form["phone"])) < 8: errors["phone"] = "Enter a valid phone number."
    if not EMAIL_RE.match(form["email"]): errors["email"] = "Enter a valid email address."
    if len(form["address"]) < 5: errors["address"] = "Enter the property address."
    if not agree: errors["agree"] = "Please confirm you've read the terms."
    if errors:
        return render(request, "subscribe.html", 422, page="plans", plan=p, form=form, errors=errors)

    sub = Subscription(plan=plan, services=", ".join(chosen), **{k: form[k] for k in ("full_name", "phone", "email", "address", "notes")})
    db.add(sub); db.commit(); db.refresh(sub)
    bg.add_task(send_email, settings.NOTIFY_EMAIL, f"New {p['name']} plan sign-up: {sub.full_name}",
                f"{sub.full_name} ({sub.phone}, {sub.email}) wants the {p['name']} plan (${p['price']}/month).\n"
                f"Address: {sub.address}\nServices: {sub.services}\nNotes: {sub.notes or '—'}\n\n"
                f"{settings.SITE_URL}/admin/subscriptions")
    bg.add_task(send_email, sub.email, f"Your {p['name']} plan request – Just Professional Services",
                f"Hi {sub.full_name.split()[0]},\n\nThanks for choosing the {p['name']} maintenance plan "
                f"(${p['price']}/month, {p['services']} services a year).\nServices: {sub.services}\n\n"
                f"We'll call you shortly to confirm your first visit and set up payment.\n\nJust Professional Services")
    checkout = payments.checkout_for_plan(plan, sub.email)
    if checkout:
        return RedirectResponse(checkout, status_code=303)
    return render(request, "subscribe_thanks.html", page="plans", plan=p, sub=sub)


# ---------------------------------------------------------------- contact
@app.get("/contact", response_class=HTMLResponse)
def contact(request: Request):
    return render(request, "contact.html", page="contact", form={}, errors={})


@app.post("/contact", response_class=HTMLResponse)
def contact_submit(request: Request, bg: BackgroundTasks, db: DB, full_name: str = Form(""), phone: str = Form(""),
                   email: str = Form(""), message: str = Form(""), website: str = Form(""), csrf: str = Form("")):
    check_csrf(request, csrf)
    if website:
        return RedirectResponse("/", status_code=303)
    form = dict(full_name=clean(full_name, 120), phone=clean(phone, 40), email=clean(email, 200).lower(), message=clean(message, 5000))
    errors = {}
    if len(form["full_name"]) < 2: errors["full_name"] = "Enter your name."
    if not EMAIL_RE.match(form["email"]): errors["email"] = "Enter a valid email address."
    if len(form["message"]) < 5: errors["message"] = "Write a short message."
    if errors:
        return render(request, "contact.html", 422, page="contact", form=form, errors=errors)
    m = ContactMessage(**form)
    db.add(m); db.commit()
    bg.add_task(send_email, settings.NOTIFY_EMAIL, f"Website message from {m.full_name}",
                f"{m.full_name} ({m.phone or 'no phone'}, {m.email}):\n\n{m.message}", reply_to=m.email)
    flash(request, "Thanks — your message has been sent. We'll get back to you soon.")
    return RedirectResponse("/contact#form", status_code=303)


# ================================================================= ADMIN
def require_admin(request: Request) -> str:
    user = current_admin(request)
    if not user:
        raise AdminRequired()
    return user


Admin = Annotated[str, Depends(require_admin)]


@app.exception_handler(AdminRequired)
def _to_login(request: Request, exc: AdminRequired):
    return RedirectResponse(f"/admin/login?next={request.url.path}", status_code=303)


@app.exception_handler(StarletteHTTPException)
def _http_error(request: Request, exc: StarletteHTTPException):
    default = "Sorry, we couldn't find that page." if exc.status_code == 404 else "Please go back and try again."
    detail = exc.detail if isinstance(exc.detail, str) and exc.detail not in {"Not Found", "Bad Request"} else default
    return render(request, "error.html", exc.status_code, code=exc.status_code, detail=detail)


def admin_counts(db: Session) -> dict:
    return {
        "new": db.exec(select(func.count()).select_from(QuoteRequest).where(QuoteRequest.status == "new")).one(),
        "subs": db.exec(select(func.count()).select_from(Subscription).where(Subscription.status == "pending")).one(),
        "msgs": db.exec(select(func.count()).select_from(ContactMessage).where(ContactMessage.handled == False)).one(),  # noqa: E712
    }


@app.get("/admin/login", response_class=HTMLResponse)
def login_form(request: Request, next: str = "/admin"):
    return render(request, "admin/login.html", next=next, error="")


# ponytail: in-memory, per process, resets on restart; move to the DB if several server processes are used
LOGIN_FAILS: dict[str, list[float]] = {}
LOCK_AFTER, LOCK_SECONDS = 5, 15 * 60


@app.post("/admin/login", response_class=HTMLResponse)
def login(request: Request, db: DB, username: str = Form(""), password: str = Form(""),
          next: str = Form("/admin"), csrf: str = Form("")):
    check_csrf(request, csrf)
    name, now = username.strip().lower(), time.time()
    recent = [t for t in LOGIN_FAILS.get(name, []) if now - t < LOCK_SECONDS]
    if len(recent) >= LOCK_AFTER:
        return render(request, "admin/login.html", 429, next=next,
                      error="Too many wrong attempts. This login is locked for 15 minutes.")
    user = db.exec(select(AdminUser).where(AdminUser.username == name)).first()
    if not user or not verify_password(password, user.password_hash):
        if len(LOGIN_FAILS) > 10_000:
            LOGIN_FAILS.clear()
        LOGIN_FAILS[name] = recent + [now]
        return render(request, "admin/login.html", 401, next=next, error="Wrong username or password.")
    LOGIN_FAILS.pop(name, None)
    request.session.clear()
    request.session["admin"] = user.username
    return RedirectResponse(next if next.startswith("/admin") else "/admin", status_code=303)


@app.post("/admin/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/admin/login", status_code=303)


@app.get("/admin", response_class=HTMLResponse)
def admin_home(request: Request, user: Admin, db: DB, status: str = "", kind: str = "", q: str = ""):
    stmt = select(QuoteRequest).order_by(col(QuoteRequest.created_at).desc())
    if status in content.STATUSES:
        stmt = stmt.where(QuoteRequest.status == status)
    if kind in content.REQUEST_KINDS:
        stmt = stmt.where(QuoteRequest.kind == kind)
    if q.strip():
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(col(QuoteRequest.full_name).ilike(like), col(QuoteRequest.subject).ilike(like),
                              col(QuoteRequest.address).ilike(like), col(QuoteRequest.email).ilike(like),
                              col(QuoteRequest.phone).ilike(like)))
    rows = db.exec(stmt.limit(300)).all()
    by_status = dict(db.exec(select(QuoteRequest.status, func.count()).group_by(QuoteRequest.status)).all())
    return render(request, "admin/requests.html", apage="requests", rows=rows, status=status, kind=kind, q=q,
                  by_status=by_status, counts=admin_counts(db))


def get_request(db: Session, rid: int) -> QuoteRequest:
    qr = db.get(QuoteRequest, rid)
    if not qr:
        raise HTTPException(404)
    return qr


@app.get("/admin/requests/{rid}", response_class=HTMLResponse)
def admin_request(request: Request, rid: int, user: Admin, db: DB):
    qr = get_request(db, rid)
    if qr.status == "new":
        qr.status = "reviewing"; qr.updated_at = now_utc(); db.add(qr); db.commit(); db.refresh(qr)
    responses = sorted(qr.responses, key=lambda r: r.created_at)
    return render(request, "admin/request_detail.html", apage="requests", qr=qr, responses=responses,
                  counts=admin_counts(db), track_url=f"{settings.SITE_URL}/track/{qr.token}")


@app.post("/admin/requests/{rid}/status")
def admin_set_status(request: Request, rid: int, user: Admin, db: DB, status: str = Form(...), csrf: str = Form("")):
    check_csrf(request, csrf)
    qr = get_request(db, rid)
    if status not in content.STATUSES:
        raise HTTPException(400)
    qr.status, qr.updated_at = status, now_utc()
    db.add(qr); db.commit()
    flash(request, f"Status changed to {content.STATUSES[status]}.")
    return RedirectResponse(f"/admin/requests/{rid}", status_code=303)


@app.post("/admin/requests/{rid}/notes")
def admin_notes(request: Request, rid: int, user: Admin, db: DB, notes: str = Form(""), csrf: str = Form("")):
    check_csrf(request, csrf)
    qr = get_request(db, rid)
    qr.admin_notes, qr.updated_at = clean(notes, 5000), now_utc()
    db.add(qr); db.commit()
    flash(request, "Notes saved.")
    return RedirectResponse(f"/admin/requests/{rid}", status_code=303)


@app.post("/admin/requests/{rid}/reply")
def admin_reply(request: Request, rid: int, user: Admin, bg: BackgroundTasks, db: DB, message: str = Form(""),
                amount: str = Form(""), send: str = Form(""), csrf: str = Form("")):
    check_csrf(request, csrf)
    qr = get_request(db, rid)
    message = clean(message, 5000)
    amount_cents = None
    if amount.strip():
        try:
            amount_cents = round(float(amount.replace("$", "").replace(",", "").strip()) * 100)
            assert amount_cents >= 0
        except (ValueError, AssertionError):
            flash(request, "Quote amount must be a number, e.g. 450 or 1250.50", "err")
            return RedirectResponse(f"/admin/requests/{rid}#reply", status_code=303)
    if not message:
        flash(request, "Write a message for the customer.", "err")
        return RedirectResponse(f"/admin/requests/{rid}#reply", status_code=303)

    resp = QuoteResponse(request_id=qr.id, author=user, message=message, amount_cents=amount_cents, emailed=bool(send))
    db.add(resp)
    if amount_cents is not None and qr.status in {"new", "reviewing", "quoted", "declined"}:
        qr.status = "quoted"
    qr.updated_at = now_utc()
    db.add(qr); db.commit()

    if send:
        track = f"{settings.SITE_URL}/track/{qr.token}"
        price = f"\nQuoted price: {money(amount_cents)} (incl. GST)\n" if amount_cents is not None else ""
        action = "\nYou can accept or decline the quote here:" if amount_cents is not None else "\nView your request here:"
        bg.add_task(send_email, qr.email, f"Re: {qr.subject} ({qr.ref}) – Just Professional Services",
                    f"Hi {qr.full_name.split()[0]},\n\n{message}\n{price}{action}\n{track}\n\n"
                    f"{user.capitalize()}\nJust Professional Services\nBen 0424 595 086 · Ash 0473 634 321",
                    reply_to=settings.NOTIFY_EMAIL)
    flash(request, "Reply saved" + (" and emailed to the customer." if send else " (not emailed)."))
    return RedirectResponse(f"/admin/requests/{rid}", status_code=303)


@app.get("/admin/files/{aid}")
def admin_file(aid: int, user: Admin, db: DB, download: int = 0):
    a = db.get(Attachment, aid)
    if not a:
        raise HTTPException(404)
    path = settings.UPLOAD_DIR / str(a.request_id) / a.stored_name
    if not path.exists():
        raise HTTPException(404)
    # type from our own whitelisted extension, never the customer's claimed type (a fake ".png" could be HTML)
    media_type = mimetypes.guess_type(a.stored_name)[0] or "application/octet-stream"
    return FileResponse(path, media_type=media_type,
                        filename=a.original_name if download else None)


@app.get("/admin/subscriptions", response_class=HTMLResponse)
def admin_subs(request: Request, user: Admin, db: DB):
    rows = db.exec(select(Subscription).order_by(col(Subscription.created_at).desc())).all()
    return render(request, "admin/subscriptions.html", apage="subs", rows=rows, counts=admin_counts(db))


@app.post("/admin/subscriptions/{sid}/status")
def admin_sub_status(request: Request, sid: int, user: Admin, db: DB, status: str = Form(...), csrf: str = Form("")):
    check_csrf(request, csrf)
    s = db.get(Subscription, sid)
    if not s or status not in {"pending", "active", "cancelled"}:
        raise HTTPException(400)
    s.status = status
    db.add(s); db.commit()
    flash(request, f"{s.full_name}'s plan marked {status}.")
    return RedirectResponse("/admin/subscriptions", status_code=303)


@app.get("/admin/messages", response_class=HTMLResponse)
def admin_messages(request: Request, user: Admin, db: DB):
    rows = db.exec(select(ContactMessage).order_by(col(ContactMessage.created_at).desc())).all()
    return render(request, "admin/messages.html", apage="msgs", rows=rows, counts=admin_counts(db))


@app.post("/admin/messages/{mid}/toggle")
def admin_msg_toggle(request: Request, mid: int, user: Admin, db: DB, csrf: str = Form("")):
    check_csrf(request, csrf)
    m = db.get(ContactMessage, mid)
    if not m:
        raise HTTPException(404)
    m.handled = not m.handled
    db.add(m); db.commit()
    return RedirectResponse("/admin/messages", status_code=303)
