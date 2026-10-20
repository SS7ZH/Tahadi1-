from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import settings


def normalize_db_url(url: str) -> str:
    """Supabase hands out postgres:// or postgresql:// URLs; SQLAlchemy needs the psycopg (v3) driver name."""
    url = url.strip().strip("'\"").strip()
    url = url.removeprefix("jdbc:")
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    if not url.startswith(("postgresql+", "sqlite")):
        shown = url.split("://", 1)[0][:30] if "://" in url else url[:12]
        raise ValueError(
            "DATABASE_URL must start with postgresql:// (copy the 'URI' / connection string from "
            f"Supabase > Connect > Session or Transaction pooler). It currently starts with: {shown!r}..."
        )
    return url


def build_engine(url: str, *, migrations: bool = False) -> Engine:
    url = normalize_db_url(url)
    kwargs: dict = {}
    connect_args: dict = {}
    if url.startswith("postgresql"):
        # Supabase's transaction pooler (pgbouncer, port 6543) cannot use prepared statements.
        connect_args["prepare_threshold"] = None
        if settings.is_production and "sslmode=" not in url:
            connect_args["sslmode"] = "require"
        use_null_pool = settings.DB_NULLPOOL if settings.DB_NULLPOOL is not None else settings.is_production
        if use_null_pool or migrations:
            kwargs["poolclass"] = NullPool
        else:
            kwargs.update(pool_pre_ping=True, pool_size=5, max_overflow=5)
    engine = create_engine(url, connect_args=connect_args, **kwargs)
    if url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def _fk_on(dbapi_conn, _):  # noqa: ANN001
            dbapi_conn.execute("PRAGMA foreign_keys=ON")
    return engine


@lru_cache
def get_engine() -> Engine:
    return build_engine(settings.DATABASE_URL)


@lru_cache
def get_sessionmaker() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    db = get_sessionmaker()()
    try:
        yield db
    finally:
        db.close()
