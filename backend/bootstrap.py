"""Create the first administrator with a hidden interactive password prompt."""
import argparse
import getpass

from sqlalchemy import select

from backend.database import Base, make_database
from backend.models import User, FederatedClient
from backend.security import password_hash


def initialize(engine, sessions):
    Base.metadata.create_all(engine)
    with sessions() as db:
        if engine.dialect.name == "sqlite":
            from sqlalchemy.dialects.sqlite import insert
        elif engine.dialect.name == "postgresql":
            from sqlalchemy.dialects.postgresql import insert
        else:
            raise ValueError("Only SQLite and PostgreSQL databases are supported")
        for i, name in enumerate(["Hospital A", "Hospital B", "Hospital C"]):
            db.execute(insert(FederatedClient).values(id=str(i), name=name).on_conflict_do_nothing(index_elements=["id"]))
        db.commit()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", default="Research Administrator")
    args = parser.parse_args()
    password = getpass.getpass("Admin password (at least 12 characters): ")
    if len(password) < 12 or len(password) > 128 or "@" not in args.email:
        parser.error("Valid email and password of 12–128 characters required")
    engine, sessions = make_database()
    initialize(engine, sessions)
    with sessions() as db:
        if db.scalar(select(User).where(User.email == args.email.lower())):
            parser.error("Account already exists")
        db.add(User(name=args.name, email=args.email.lower(), password_hash=password_hash(password), role="Admin"))
        db.commit()
    print("Admin created. No default password is stored in the repository.")


if __name__ == "__main__":
    main()
