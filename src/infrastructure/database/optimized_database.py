"""Optimized database manager with connection pooling and query optimization."""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy import create_engine, event, pool, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.infrastructure.database.database import DatabaseManager

logger = logging.getLogger(__name__)


class OptimizedDatabaseManager(DatabaseManager):
    """Enhanced database manager with performance optimizations."""

    def __init__(self, db_path: str = "data/trainer.db"):
        """Initialize optimized database manager.

        Args:
            db_path: Path to SQLite database
        """
        super().__init__(db_path)

        # Configure connection pool for better performance
        self.engine = create_engine(
            f"sqlite:///{self.db_path}",
            connect_args={
                "check_same_thread": False,
                "timeout": 30,  # 30 second timeout
            },
            poolclass=pool.QueuePool,
            pool_size=10,  # Number of connections to maintain
            max_overflow=20,  # Maximum overflow connections
            pool_pre_ping=True,  # Verify connections before use
            echo=False,
        )

        # Re-enable foreign keys and add performance pragmas
        @event.listens_for(self.engine, "connect")
        def set_sqlite_pragma(dbapi_connection: Any, _: Any) -> None:
            cursor = dbapi_connection.cursor()
            # Performance optimizations
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging
            cursor.execute("PRAGMA synchronous=NORMAL")  # Faster writes
            cursor.execute("PRAGMA cache_size=10000")  # Larger cache (10MB)
            cursor.execute("PRAGMA temp_store=MEMORY")  # Use memory for temp tables
            cursor.execute("PRAGMA mmap_size=268435456")  # 256MB memory-mapped I/O
            cursor.close()

        # Create async engine for async operations
        self.async_engine = create_async_engine(
            f"sqlite+aiosqlite:///{self.db_path}",
            connect_args={
                "check_same_thread": False,
                "timeout": 30,
            },
            pool_pre_ping=True,
            echo=False,
        )

        self.async_session_maker = async_sessionmaker(
            self.async_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        # Create indexes for better query performance
        self._create_indexes()

        logger.info(f"Optimized database initialized at {self.db_path}")

    def _create_indexes(self) -> None:
        """Create database indexes for better query performance."""
        with self.engine.begin() as conn:
            # Question indexes
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_questions_category "
                    "ON questions(category)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_questions_state ON questions(state)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_questions_type_state "
                    "ON questions(question_type, state)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_questions_image "
                    "ON questions(is_image_question)"
                )
            )

            # FSRS card indexes
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_fsrs_cards_user_review "
                    "ON fsrs_cards(user_id, next_review_date)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_fsrs_cards_question_user "
                    "ON fsrs_cards(question_id, user_id)"
                )
            )

            # Session indexes
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_sessions_user_status "
                    "ON practice_sessions(user_id, status)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_sessions_started "
                    "ON practice_sessions(started_at)"
                )
            )

            # Question attempts index
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_attempts_session "
                    "ON question_attempts(session_id)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_attempts_question "
                    "ON question_attempts(question_id)"
                )
            )

            # User settings index
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_user_settings_user "
                    "ON user_settings(user_id)"
                )
            )

            logger.info("Database indexes created/verified")

    @asynccontextmanager
    async def get_async_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get async database session for high-performance operations.

        Yields:
            Async database session
        """
        async with self.async_session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    def analyze_database(self) -> None:
        """Run ANALYZE to update SQLite query planner statistics."""
        with self.engine.begin() as conn:
            conn.execute(text("ANALYZE"))
            logger.info("Database statistics updated")

    def vacuum_database(self) -> None:
        """Vacuum database to reclaim space and optimize structure."""
        # Note: VACUUM cannot be run within a transaction
        with self.engine.connect() as conn:
            conn.execute(text("VACUUM"))
            logger.info("Database vacuumed")

    def get_database_stats(self) -> dict[str, Any]:
        """Get database performance statistics.

        Returns:
            Dictionary of database statistics
        """
        stats = {}

        with self.engine.begin() as conn:
            # Get page count and size
            result = conn.execute(text("PRAGMA page_count"))
            page_count = result.scalar()

            result = conn.execute(text("PRAGMA page_size"))
            page_size = result.scalar()

            # Get cache statistics
            result = conn.execute(text("PRAGMA cache_size"))
            cache_size = result.scalar()

            # Get table sizes
            result = conn.execute(
                text(
                    """
                    SELECT
                        name as table_name,
                        SUM(pgsize) as size_bytes
                    FROM dbstat
                    GROUP BY name
                    ORDER BY size_bytes DESC
                    """
                )
            )
            table_sizes = {row[0]: row[1] for row in result}

            stats.update(
                {
                    "database_size_mb": round(
                        (page_count * page_size) / 1024 / 1024, 2
                    ),
                    "page_count": page_count,
                    "page_size": page_size,
                    "cache_pages": abs(cache_size),  # Negative means KB
                    "table_sizes": table_sizes,
                }
            )

        return stats

    def optimize_query(self, query: str) -> list[dict[str, Any]]:
        """Analyze query execution plan for optimization.

        Args:
            query: SQL query to analyze

        Returns:
            Query execution plan
        """
        with self.engine.begin() as conn:
            result = conn.execute(text(f"EXPLAIN QUERY PLAN {query}"))
            plan = [dict(row._mapping) for row in result]
            return plan
