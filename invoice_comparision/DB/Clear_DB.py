"""
Utility script to delete ONLY the records from tables defined in SQLAlchemy models,
but keep the tables/schema intact.
"""

from .models import Base, get_engine, get_session_local


def clear_model_tables():
    """Delete all rows from tables defined in SQLAlchemy models without dropping tables."""
    session = None
    try:
        engine = get_engine()
        SessionLocal = get_session_local()
        session = SessionLocal()

        # Delete in reverse dependency order (avoids FK issues)
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(table.delete())

        session.commit()
        return True, "All records deleted successfully."

    except Exception as e:
        if session:
            session.rollback()
        error_msg = f"Failed to delete records: {str(e)}"
        return False, error_msg

    finally:
        if session:
            session.close()


if __name__ == "__main__":
    clear_model_tables()
