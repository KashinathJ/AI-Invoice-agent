from sqlalchemy import text
from DB.models import (
    get_engine,
    get_session_local,
    Base,
)


# Database functions
def test_database_connection():
    """Test database connection and return connection status"""
    try:

        # Get the engine (this will create it if it doesn't exist)
        engine = get_engine()

        # Test basic connection
        with engine.connect() as connection:
            # Test if we can execute a simple query
            result = connection.execute(text("SELECT 1"))

            # Get database info
            if hasattr(engine, 'url'):
                db_url = str(engine.url)
                # Mask sensitive information in logs
                if 'password' in db_url:
                    db_url = db_url.replace(db_url.split('@')[0].split(':')[-1], '***')
            return True, "Database connection successful"

    except Exception as e:
        error_msg = f"Database connection failed: {str(e)}"
        return False, error_msg


def get_db():
    SessionLocal = get_session_local()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """Create all tables with connection testing and schema handling"""
    try:
        engine = get_engine()

        # First test the connection
        connection_success, connection_message = test_database_connection()
        if not connection_success:
            return False, connection_message

        # Handle PostgreSQL schema creation only when using PostgreSQL
        if 'postgresql' in str(engine.url).lower():
            try:
                with engine.connect() as connection:
                    # Create schema if it doesn't exist
                    connection.execute(text("CREATE SCHEMA IF NOT EXISTS public"))
                    connection.commit()

                    # Set search path for this connection
                    connection.execute(text("SET search_path TO public"))
                    connection.commit()

            except Exception as e:
                raise Exception(f"Schema setup warning: {str(e)}")

        # Create all tables
        Base.metadata.create_all(bind=engine)

        # Verify tables were created by checking if they exist
        inspector = engine.dialect.inspector(engine)

        # For PostgreSQL, check in the correct schema
        if 'postgresql' in str(engine.url).lower():
            try:
                with engine.connect() as connection:
                    connection.execute(text("SET search_path TO public"))
                    connection.commit()

                    # Check tables in hkms schema
                    result = connection.execute(text("""
                        SELECT table_name 
                        FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name IN ('mismatch_contract')
                    """))
                    existing_tables = [row[0] for row in result]

            except Exception as e:
                # Fallback to general inspector
                existing_tables = inspector.get_table_names()
        else:
            # For SQLite and other databases, use standard inspector
            existing_tables = inspector.get_table_names()

        expected_tables = ["mismatch_contract"]

        missing_tables = [table for table in expected_tables if table not in existing_tables]

        if missing_tables:
            return False, f"Tables not created: {missing_tables}"

        return True, "Database tables created and tested successfully"

    except Exception as e:
        error_msg = f"Failed to create database tables: {str(e)}"
        return False, error_msg

