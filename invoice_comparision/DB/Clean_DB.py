"""
Utility script to drop ONLY the tables defined in SQLAlchemy models.
"""

from models import Base, get_engine


def drop_model_tables():
    """Drop only the tables that are mapped in SQLAlchemy models."""
    try:
        engine = get_engine()

        # This drops exactly the tables present in Base.metadata
        Base.metadata.drop_all(bind=engine)

        return True, "Model-defined tables dropped successfully."

    except Exception as e:
        error_msg = f"Failed to drop model-defined tables: {str(e)}"
        return False, error_msg


if __name__ == "__main__":
    drop_model_tables()
