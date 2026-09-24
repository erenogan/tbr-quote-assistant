import os
import pathlib

# Uygulama import edilmeden ÖNCE DB adresini test DB'sine çevir.
# config.py, DATABASE_URL'i import anında okuyor; sıra önemli.
TEST_URL = os.environ["TEST_DATABASE_URL"]
os.environ["DATABASE_URL"] = TEST_URL

import psycopg
import pytest

SQL_DIR = pathlib.Path("/db")
SQL_FILES = ["01_seed.sql", "02_app_schema.sql"]


def reset_database():
    """Şemayı silip seed'i ve uygulama şemasını baştan yükler."""
    with psycopg.connect(TEST_URL, autocommit=True) as conn:
        conn.execute("DROP SCHEMA IF EXISTS case_seed CASCADE")
        for name in SQL_FILES:
            conn.execute((SQL_DIR / name).read_text(encoding="utf-8"))


@pytest.fixture(autouse=True)
def clean_db():
    reset_database()
    yield