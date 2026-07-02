from __future__ import annotations

import argparse
import asyncio

from mecateca.db.base import Base
from mecateca.db.engine import get_engine, get_sessionmaker
from mecateca.db import registry  # noqa: F401  (populate metadata)


async def _initdb() -> None:
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("schema created.")


async def _resetdb() -> None:
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    print("schema reset (dropped + recreated).")


async def _reseedtiers() -> None:
    from mecateca.contexts.progression import tiers as tiers_mod

    sm = get_sessionmaker()
    async with sm() as db:
        rows = await tiers_mod.reseed(db, "standard")
        await db.commit()
        print("tiers reseeded: " + ", ".join(f"{n}={ep}" for n, ep in rows))


async def _seedphil() -> None:
    from mecateca.contexts.catalog import seed_philosophy

    sm = get_sessionmaker()
    async with sm() as db:
        res = await seed_philosophy.seed(db)
        await db.commit()
        print(f"philosophy seed: {res}")


async def _fillphil(target: int) -> None:
    from mecateca.contexts.catalog import seed_philosophy
    from mecateca.deps import get_llm_provider

    provider = get_llm_provider()
    sm = get_sessionmaker()
    async with sm() as db:
        res = await seed_philosophy.fill_questions(db, provider, target=target)
        await db.commit()
        print("fill report:")
        for k, v in res.items():
            print(f"  {k}: {v}")


async def _loadpack(path: str) -> None:
    from mecateca.contexts.catalog.pack_loader import load_from_path

    sm = get_sessionmaker()
    async with sm() as db:
        sv = await load_from_path(db, path)
        await db.commit()
        print(f"loaded subject_version {sv.id} (version {sv.version}).")


async def _createadmin(email: str, password: str, name: str) -> None:
    from mecateca.contexts.identity import service

    sm = get_sessionmaker()
    async with sm() as db:
        user = await service.register(db, email, password, name)
        user.role = "admin"
        user.plan = "pro"
        await db.commit()
        print(f"admin created: {user.email} ({user.id})")


def main() -> None:
    p = argparse.ArgumentParser(prog="mecateca")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("initdb", help="create all tables (dev)")
    sub.add_parser("resetdb", help="drop + recreate all tables (dev)")
    sub.add_parser("reseedtiers", help="reload rank tiers from YAML + recompute ranks")
    sub.add_parser("seedphil", help="seed curriculum Filosofia tests (10/11/12, idempotent)")
    fp = sub.add_parser("fillphil", help="LLM-fill each Filosofia test up to N questions")
    fp.add_argument("--target", type=int, default=100)

    lp = sub.add_parser("loadpack", help="import a subject pack yaml")
    lp.add_argument("path")

    ca = sub.add_parser("createadmin", help="create an admin user")
    ca.add_argument("email")
    ca.add_argument("password")
    ca.add_argument("name")

    args = p.parse_args()
    if args.cmd == "initdb":
        asyncio.run(_initdb())
    elif args.cmd == "resetdb":
        asyncio.run(_resetdb())
    elif args.cmd == "reseedtiers":
        asyncio.run(_reseedtiers())
    elif args.cmd == "seedphil":
        asyncio.run(_seedphil())
    elif args.cmd == "fillphil":
        asyncio.run(_fillphil(args.target))
    elif args.cmd == "loadpack":
        asyncio.run(_loadpack(args.path))
    elif args.cmd == "createadmin":
        asyncio.run(_createadmin(args.email, args.password, args.name))


if __name__ == "__main__":
    main()
