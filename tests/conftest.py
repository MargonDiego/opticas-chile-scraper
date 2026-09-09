import os
import pytest
from sqlmodel import SQLModel
from src.database import engine, init_db

@pytest.fixture(autouse=True)
async def setup_test_database():
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
        await conn.run_sync(SQLModel.metadata.create_all)