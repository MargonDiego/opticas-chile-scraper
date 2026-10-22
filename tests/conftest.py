import os
import shutil
import tempfile

# The engine is built at import time from src.config.settings, so the throwaway
# database URL must be forced BEFORE anything from src is imported. Without
# this, the autouse fixture would drop_all/create_all the developer's real
# catalog (default: sqlite+aiosqlite:///data/opticas.db).
_TEST_DB_DIR = tempfile.mkdtemp(prefix="opticas-test-db-")
_TEST_DB_PATH = os.path.join(_TEST_DB_DIR, "test_opticas.db").replace(os.sep, "/")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_TEST_DB_PATH}"

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlmodel import SQLModel  # noqa: E402

from src.database import engine  # noqa: E402


@pytest_asyncio.fixture(scope="session", loop_scope="session", autouse=True)
async def cleanup_test_database():
    """Dispose the engine before removing the throwaway database directory.

    On Windows the SQLite file stays locked by the pooled connections, so
    ``shutil.rmtree(ignore_errors=True)`` silently fails and the temp dir leaks.
    """
    yield
    await engine.dispose()
    shutil.rmtree(_TEST_DB_DIR, ignore_errors=True)


@pytest.fixture(autouse=True)
def reset_health_cache():
    """Keep the /api/health TTL cache from leaking between test cases."""
    from src.main import _reset_health_cache

    _reset_health_cache()


@pytest.fixture(autouse=True)
async def setup_test_database():
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
        await conn.run_sync(SQLModel.metadata.create_all)
        # Same composite index created by src.database.init_db(), so tests see
        # the production schema shape without invoking the real bootstrap.
        await conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_price_snapshots_product_scraped "
                "ON price_snapshots (product_id, scraped_at DESC);"
            )
        )
