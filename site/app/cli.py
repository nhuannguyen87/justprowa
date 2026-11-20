"""Command line helpers.

  python -m app.cli create-admin ben          # asks for a password
  python -m app.cli create-admin ash --password "S0mething-long"
  python -m app.cli seed-demo                  # adds a few example requests for testing
"""
import argparse
import getpass
import sys

from sqlmodel import Session, select

from .db import engine, init_db
from .models import AdminUser, ContactMessage, QuoteRequest, QuoteResponse, Subscription
from .security import hash_password


def create_admin(username: str, password: str | None) -> None:
    username = username.strip().lower()
    if not password:
        password = getpass.getpass(f"Password for {username}: ")
        if password != getpass.getpass("Repeat password: "):
            sys.exit("Passwords don't match.")
    if len(password) < 8:
        sys.exit("Use at least 8 characters.")
    with Session(engine) as db:
        user = db.exec(select(AdminUser).where(AdminUser.username == username)).first()
        if user:
            user.password_hash = hash_password(password)
            print(f"Updated password for '{username}'.")
        else:
            db.add(AdminUser(username=username, password_hash=hash_password(password)))
            print(f"Created admin '{username}'.")
        db.commit()


def seed_demo() -> None:
    with Session(engine) as db:
        if db.exec(select(QuoteRequest)).first():
            print("Database already has requests – skipping demo data.")
            return
        a = QuoteRequest(kind="quote", subject="Replace rotten decking boards",
                         description="About 12 boards on the back deck are soft and splitting. Deck is roughly 4m x 5m, jarrah. Would also like it re-oiled.",
                         address="12 Example St, Applecross WA 6153", preferred_days="flexible", full_name="Sarah Demo",
                         phone="0400 000 001", email="sarah@example.com", contact_method="phone")
        b = QuoteRequest(kind="callout", subject="Leaking kitchen tap", description="Mixer tap in kitchen drips constantly, getting worse.",
                         address="7 Sample Rd, Scarborough WA 6019", full_name="Tom Example", phone="0400 000 002",
                         email="tom@example.com", contact_method="sms", status="quoted")
        db.add_all([a, b]); db.commit(); db.refresh(b)
        db.add(QuoteResponse(request_id=b.id, author="ben", message="Hi Tom, we can replace the cartridge or fit a new mixer. Price below includes a mid-range mixer and labour.", amount_cents=28500, emailed=False))
        db.add(Subscription(plan="silver", services="Gutter cleaning, Solar panel clean, Window clean", full_name="Lee Sample",
                            phone="0400 000 003", email="lee@example.com", address="3 Demo Ave, Joondalup WA 6027"))
        db.add(ContactMessage(full_name="Priya Test", email="priya@example.com", message="Do you service Mandurah?"))
        db.commit()
        print("Demo data added.")


def main() -> None:
    p = argparse.ArgumentParser(prog="python -m app.cli")
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("create-admin"); c.add_argument("username"); c.add_argument("--password")
    sub.add_parser("seed-demo")
    args = p.parse_args()
    init_db()
    if args.cmd == "create-admin":
        create_admin(args.username, args.password)
    elif args.cmd == "seed-demo":
        seed_demo()


if __name__ == "__main__":
    main()
