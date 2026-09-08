import pytest
from src.database import init_db

@pytest.fixture(autouse=True)
async def setup_test_database():
    await init_db()