from sqlalchemy import column
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector

from src.main import build_vector_search_stmt

EMBEDDING_DIM = 768


def _vector_stmt(limit: int = 100):
    # The model column is JSON when DATABASE_URL is not PostgreSQL (as in the
    # test suite), so the pgvector expression is compiled against an equivalent
    # Vector-typed column. The statement under test is the production helper.
    return build_vector_search_stmt(
        [0.01] * EMBEDDING_DIM,
        limit,
        embedding_column=column("embedding", Vector(EMBEDDING_DIM)),
    )


def _compiled_sql(limit: int = 100) -> str:
    return str(_vector_stmt(limit).compile(dialect=postgresql.dialect()))


def test_vector_candidates_are_ordered_by_ascending_cosine_distance():
    """Regression: dropping the ORDER BY would return arbitrary rows for LIMIT."""
    sql = _compiled_sql()

    assert "ORDER BY" in sql
    assert "LIMIT" in sql

    order_index = sql.index("ORDER BY")
    limit_index = sql.index("LIMIT")
    assert order_index < limit_index, "the ORDER BY must be applied before the LIMIT"

    order_clause = sql[order_index:limit_index]
    assert "<=>" in order_clause, "the distance operator must drive the ordering"
    assert "ASC" in order_clause, "cosine distance ascending means closest first"


def test_vector_candidate_query_does_not_eager_load_price_history():
    """Regression: selectinload(price_snapshots) loaded full history for nothing."""
    stmt = _vector_stmt()
    assert not stmt._with_options
    assert "price_snapshots" not in _compiled_sql()


def test_vector_candidates_apply_facet_filters_before_the_limit():
    """Regression: facets applied after the global LIMIT starved narrow facets."""
    sql = str(
        build_vector_search_stmt(
            [0.01] * EMBEDDING_DIM,
            100,
            embedding_column=column("embedding", Vector(EMBEDDING_DIM)),
            store="gmo",
            category="lentes_opticos",
            brand="ray",
        ).compile(dialect=postgresql.dialect())
    )

    where_index = sql.index("WHERE")
    order_index = sql.index("ORDER BY")
    limit_index = sql.index("LIMIT")

    assert where_index < order_index < limit_index
    where_clause = sql[where_index:order_index]
    assert "products.store =" in where_clause
    assert "products.category =" in where_clause
    assert "products.brand ILIKE" in where_clause
    # Rows without an embedding must never be candidates.
    assert "products.embedding IS NOT NULL" in where_clause


def test_vector_candidates_without_filters_only_exclude_null_embeddings():
    sql = _compiled_sql()
    where_index = sql.index("WHERE")
    order_index = sql.index("ORDER BY")
    where_clause = sql[where_index:order_index]

    assert "products.embedding IS NOT NULL" in where_clause
    assert "products.store =" not in where_clause
    assert "products.category =" not in where_clause
    assert "ILIKE" not in where_clause
