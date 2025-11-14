import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import SimpleConnectionPool
from contextlib import contextmanager
from app.config import settings
import logging

logger = logging.getLogger(__name__)

# Connection pool
pool: SimpleConnectionPool = None


def init_db():
    """Initialize database connection pool"""
    global pool
    try:
        pool = SimpleConnectionPool(
            minconn=1,
            maxconn=10,
            host=settings.postgres_host,
            port=settings.postgres_port,
            database=settings.postgres_db,
            user=settings.postgres_user,
            password=settings.postgres_password,
        )
        logger.info("Database connection pool created")
    except Exception as e:
        logger.error(f"Error creating connection pool: {e}")
        raise


def close_db():
    """Close all database connections"""
    global pool
    if pool:
        pool.closeall()
        logger.info("Database connection pool closed")


@contextmanager
def get_db():
    """Get database connection from pool"""
    conn = None
    try:
        conn = pool.getconn()
        yield conn
        conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        if conn:
            pool.putconn(conn)

