import psycopg2
from psycopg2 import sql
from datetime import datetime
from typing import List, Optional

db_config = {
    "host": "behelp.c7cg6ews0pdl.ap-south-1.rds.amazonaws.com",
    "dbname": "Invoice_Pipeline",
    "user": "postgres",
    "password": "Aust1n24$"
}


class ActivityLogger:
    def __init__(self, db_config: dict = db_config, agent_name: str = None):
        """
        Initialize the ActivityLogger with database configuration and agent name.

        :param db_config: A dictionary containing database connection parameters.
        :param agent_name: Name of the agent (e.g., 'email', 'upload', 'gdrive').
        """
        self.db_config = db_config
        self.agent_name = agent_name
        self.table_name = f"{self.agent_name}_log" if agent_name else "activity_log"
        self.table_schema = self.get_table_schema_dict(self.table_name)
        self._ensure_table_exists()

    def _get_connection(self):
        """Establish a new database connection."""

        return psycopg2.connect(**self.db_config)

    def get_table_schema_dict(self, table_name: str) -> dict:
        """
        Retrieve the column names and data types for a given table.
        :param table_name: Name of the table to inspect.
        :return: Dictionary with column names as keys and data types as values.
        """
        query = """
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = %s
        ORDER BY ordinal_position;
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (table_name,))
                rows = cur.fetchall()
                schema = {column: dtype for column, dtype in rows}
        return schema

    def insert_log(self, log_data: dict):
        """
        Insert a log entry into the agent-specific log table using a dictionary.

        :param log_data: A dictionary where keys are column names (excluding 'id'),
                        and values are the corresponding data to insert.
        :raises ValueError: If the dictionary contains unknown columns.
        """
        schema = self.table_schema
        schema_keys = set(schema.keys()) - {'id'}
        input_keys = set(log_data.keys())

        # 1. Check for unknown keys
        unknown_keys = input_keys - schema_keys
        if unknown_keys:
            raise ValueError(
                f"Unknown column(s) in input: {', '.join(unknown_keys)}, expected: {', '.join(schema_keys)}")

        # 2. Type validation map (PostgreSQL → Python types)
        pg_to_py_types = {
            'text': str,
            'character varying': str,
            'integer': int,
            'bigint': int,
            'float': float,
            'real': float,
            'double precision': float,
            'numeric': float,
            'timestamp without time zone': datetime,
            'timestamp with time zone': datetime,
            'boolean': bool
        }

        # 3. Validate data types
        for key in input_keys:
            expected_pg_type = schema[key]
            expected_py_type = pg_to_py_types.get(expected_pg_type.lower())

            if expected_py_type and not isinstance(log_data[key], expected_py_type):
                raise ValueError(
                    f"Invalid type for '{key}': expected {expected_py_type.__name__}, got {type(log_data[key]).__name__}"
                )

        # 4. Build insert query
        insert_cols = list(input_keys)
        values = [log_data[col] for col in insert_cols]
        placeholders = ', '.join(['%s'] * len(insert_cols))
        columns_str = ', '.join(f'"{col}"' for col in insert_cols)

        insert_query = sql.SQL(f"""
            INSERT INTO {self.table_name} ({columns_str})
            VALUES ({placeholders})
            RETURNING id;
        """)

        print(insert_query)

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(insert_query, values)
                inserted = cur.fetchone()
                conn.commit()
        # current row ID
        return inserted[0]

    def insert_items(self, log_id: int, category: str):
        item_table_name = "invoice_mismatch_items"
        item_column = "log_id, item_name"
        item_placeholders = ', '.join(['%s'] * 2)
        item_values = [log_id, category]

        # query, returns current inserted item id
        item_query = sql.SQL(f"""
                                INSERT INTO {item_table_name} ({item_column})
                                VALUES ({item_placeholders})
                                RETURNING id;
                            """)
        item_id = self.insert_into(item_query, item_values)
        return item_id

    def insert_fields(self, doc_type: str, log_id: int, items: dict):
        CALL = {
            "Contract": self.insert_contract_fields,
            "PO": self.insert_po_fields
        }

        for item in items["mismatches"]:
            category = item["Issue_category"]
            keys = item[category].keys()

            item_id = self.insert_items(log_id, category)

            for key in keys:
                print(f"{category}: {key}")
                sub_item = item[category][key]

                CALL[doc_type](item_id, sub_item, key)

    def insert_contract_fields(self, item_id, sub_item, key):
        contract_value = sub_item["Contract"]
        invoice_value = sub_item["Invoice"]

        field_table_name = "invoice_mismatch_contract_fields"
        field_column = "item_id, field_name, contract_value, invoice_value"
        field_placeholders = ', '.join(['%s'] * 4)
        field_values = [item_id, key, contract_value, invoice_value]

        print(f"contract value: {contract_value}, invoice value: {invoice_value}", end="\n\n")

        field_query = sql.SQL(f"""
                            INSERT INTO {field_table_name} ({field_column})
                            VALUES ({field_placeholders})
                            RETURNING id;
                        """)
        self.insert_into(field_query, field_values)

    def insert_po_fields(self, item_id, sub_item, key):
        contract_value = sub_item["PO_value"]
        invoice_value = sub_item["Invoice"]

        field_table_name = "invoice_mismatch_po_fields"
        field_column = "item_id, field_name, po_value, invoice_value"
        field_placeholders = ', '.join(['%s'] * 4)
        field_values = [item_id, key, contract_value, invoice_value]

        print(f"contract value: {contract_value}, invoice value: {invoice_value}", end="\n\n")

        field_query = sql.SQL(f"""
                            INSERT INTO {field_table_name} ({field_column})
                            VALUES ({field_placeholders})
                            RETURNING id;
                        """)
        self.insert_into(field_query, field_values)

    def insert_into(self, query, values) -> int | None:
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, values)
                    inserted = cur.fetchone()
                    conn.commit()

            # current row ID
            return inserted[0]
        except Exception as e:
            print(f"error is: {e}")
            return None

    def _ensure_table_exists(self):
        """
        Ensure that the activity_log table exists in the database.
        """
        create_table_query = """
        CREATE TABLE IF NOT EXISTS activity_log (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMP NOT NULL,
            event TEXT NOT NULL,
            status TEXT NOT NULL,
            details TEXT
        );
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(create_table_query)
                conn.commit()

        query = """
        CREATE TABLE IF NOT EXISTS invoice_mismatch_items (
            id SERIAL PRIMARY KEY,
            log_id INT NOT NULL,
            item_name VARCHAR(255) NOT NULL,
            CONSTRAINT fk_log
                FOREIGN KEY (log_id) 
                REFERENCES invoice_mismatch_log(id)
                ON DELETE CASCADE
        );        
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query)
                conn.commit()

        query = """
        CREATE TABLE IF NOT EXISTS invoice_mismatch_contract_fields (
            id SERIAL PRIMARY KEY,
            item_id INT NOT NULL,
            field_name VARCHAR(100) NOT NULL,
            contract_value TEXT,
            invoice_value TEXT,
            CONSTRAINT fk_item
                FOREIGN KEY (item_id)
                REFERENCES invoice_mismatch_items(id)
                ON DELETE CASCADE
        );
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query)
                conn.commit()

        query = """
                CREATE TABLE IF NOT EXISTS invoice_mismatch_po_fields (
                    id SERIAL PRIMARY KEY,
                    item_id INT NOT NULL,
                    field_name VARCHAR(100) NOT NULL,
                    po_value TEXT,
                    invoice_value TEXT,
                    CONSTRAINT fk_item
                        FOREIGN KEY (item_id)
                        REFERENCES invoice_mismatch_items(id)
                        ON DELETE CASCADE
                );
                """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query)
                conn.commit()

    # def _truncate_pending_due_table(self):
    #     """
    #     Ensure that the mismatch_log table exists in the database.
    #     """
    #     create_table_query = """
    #     TRUNCATE TABLE invoice_pending_due_dtl;
    #     """
    #     with self._get_connection() as conn:
    #         with conn.cursor() as cur:
    #             cur.execute(create_table_query)
    #             conn.commit()

    def log_event(self, event: str, status: str, details: str):
        """
        Internal method to log an event to the database.

        :param event: The type/category of the event.
        :param details: Detailed description of the event.
        """
        insert_query = """
        INSERT INTO activity_log (timestamp, event, status, details)
        VALUES (%s, %s, %s, %s);
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(insert_query, (datetime.now(), event, status, details))
                conn.commit()

    def fetch_logs_from_table(self) -> list[dict]:
        """
        Fetch all logs from the agent-specific table using its schema.

        :return: A list of dictionaries, each representing a row from the log table.
        """
        columns = list(self.table_schema.keys())
        columns_str = ', '.join(columns)

        query = sql.SQL(f"""
            SELECT {columns_str} FROM {self.table_name};
        """)

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query)
                rows = cur.fetchall()

        # Convert each row to a dictionary using schema order
        logs = [dict(zip(columns, row)) for row in rows]
        print(logs)
        if not logs:
            print("📭 No logs found.")
        else:
            print("\n📋 Retrieved Logs:")
            print("-" * 80)

            # Calculate max width for key alignment
            max_key_len = max(len(key) for key in logs[0].keys())

            for log in logs:
                for key, value in log.items():
                    padded_key = f"{key.replace('_', ' ').capitalize():<{max_key_len}}"
                    print(f"{padded_key} : {value}")
                print("-" * 80)

        return logs

    def fetch_logs(self, event: Optional[str] = None, display: bool = True) -> List[dict]:
        """
        Fetch logs from the database and optionally display them in a readable format.

        :param event: Specific event type to filter logs. If None, fetches all logs.
        :param display: Whether to print the logs in a user-friendly way.
        :return: List of log entries as dictionaries.
        """
        select_query = """
        SELECT id, timestamp, event, status, details
        FROM activity_log
        {where_clause}
        ORDER BY timestamp ASC;
        """
        where_clause = sql.SQL("")
        params = ()

        if event:
            where_clause = sql.SQL("WHERE event = %s")
            params = (event,)

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql.SQL(select_query).format(where_clause=where_clause), params)
                rows = cur.fetchall()
                logs = []
                for row in rows:
                    logs.append({
                        'id': row[0],
                        'timestamp': row[1],
                        'event': row[2],
                        'status': row[3],
                        'details': row[4]
                    })

                if display:
                    if not logs:
                        print("📭 No logs found.")
                    else:
                        print("\n📝 Activity Logs:")
                        print("-" * 80)
                        for log in logs:
                            print(f"🆔 ID: {log['id']}")
                            print(f"🕰️  Timestamp: {log['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
                            print(f"📋 Event: {log['event']}")
                            print(f"✅ Status: {log['status']}")
                            print(f"🖋️  Details: {log['details']}")
                            print("-" * 80)

                return logs

    def fetch_file_download_logs(self) -> List[dict]:
        """
        Fetch logs related to file downloads or receipts.

        :return: List of file download log entries.
        """
        return self.fetch_logs(event='FILE_DOWNLOAD')

    def fetch_info_logs(self) -> List[dict]:
        """
        Fetch logs related to information additions and modifications.

        :return: List of information-related log entries.
        """
        info_added_logs = self.fetch_logs(event='INFO_ADDED')
        info_modified_logs = self.fetch_logs(event='INFO_MODIFIED')
        return info_added_logs + info_modified_logs

    def clear_logs(self):
        """
        Clear all logs from the activity_log table.
        """
        delete_query = "DELETE FROM activity_log;"
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(delete_query)
                conn.commit()
        print("🧹 All activity logs have been cleared.")


if __name__ == "__main__":
    logger = ActivityLogger(agent_name='parser')
    logger.fetch_logs_from_table()
    #logger._ensure_table_exists()
    #logger.describe_table()
