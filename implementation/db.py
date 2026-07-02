import os
import sqlite3

class ValidationError(Exception):
    """Raised when a request cannot be safely executed or validation fails."""
    pass

class SQLiteAdapter:
    """
    Handles SQLite database operations with strict safety checks to prevent SQL Injection.
    """
    def __init__(self, db_path=None):
        if db_path is None:
            # Default to school.db in the same directory as this file
            script_dir = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.join(script_dir, "school.db")
        self.db_path = db_path
        self.allowed_operators = {"=", "!=", ">", ">=", "<", "<=", "LIKE", "IN"}
        self.allowed_metrics = {"count", "avg", "sum", "min", "max"}

    def connect(self):
        """Returns a connection to the SQLite database with Row factory enabled."""
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Database file not found at: {self.db_path}")
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def list_tables(self):
        """Returns a list of user-defined tables in the database."""
        conn = self.connect()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"
            )
            tables = [row["name"] for row in cursor.fetchall()]
            return tables
        finally:
            conn.close()

    def get_table_schema(self, table):
        """
        Returns a dictionary mapping column names to their types for a given table.
        Raises ValidationError if the table does not exist.
        """
        tables = self.list_tables()
        if table not in tables:
            raise ValidationError(f"Unknown table: '{table}'. Available tables: {', '.join(tables)}")

        conn = self.connect()
        try:
            cursor = conn.cursor()
            # PRAGMA table_info is safe when the table name has been checked against list_tables()
            cursor.execute(f"PRAGMA table_info({table});")
            columns = {row["name"]: row["type"] for row in cursor.fetchall()}
            return columns
        finally:
            conn.close()

    def _validate_table_and_columns(self, table, columns_to_check):
        """
        Validates table and columns against database schema.
        Raises ValidationError if invalid.
        """
        schema = self.get_table_schema(table)
        for col in columns_to_check:
            if col not in schema:
                available = ", ".join(schema.keys())
                raise ValidationError(
                    f"Unknown column '{col}' in table '{table}'. Available columns: {available}"
                )
        return schema

    def search(self, table, columns=None, filters=None, limit=20, offset=0, order_by=None, descending=False):
        """
        Safely searches a table with optional columns, filters, sorting, and pagination.
        
        filters can be:
        - A dict of equality checks: {"cohort": "A1"}
        - A list of structured filter dicts: [{"column": "score", "operator": ">", "value": 80.0}]
        """
        # Validate limit and offset
        if not isinstance(limit, int) or limit < 0:
            raise ValidationError("Limit must be a non-negative integer.")
        if not isinstance(offset, int) or offset < 0:
            raise ValidationError("Offset must be a non-negative integer.")

        # 1. Validate table and build base columns
        schema = self.get_table_schema(table)
        
        if columns:
            if not isinstance(columns, list):
                raise ValidationError("Columns parameter must be a list of strings.")
            self._validate_table_and_columns(table, columns)
            cols_str = ", ".join(columns)
        else:
            cols_str = "*"

        # 2. Build WHERE clause safely
        where_clauses = []
        params = []

        if filters:
            # Handle list of structured filters: [{"column": "col", "operator": "op", "value": val}]
            if isinstance(filters, list):
                for f in filters:
                    if not isinstance(f, dict) or "column" not in f or "operator" not in f or "value" not in f:
                        raise ValidationError(
                            "Each filter in a list must be a dict containing 'column', 'operator', and 'value'."
                        )
                    col = f["column"]
                    op = f["operator"].upper()
                    val = f["value"]

                    self._validate_table_and_columns(table, [col])
                    if op not in self.allowed_operators:
                        raise ValidationError(
                            f"Unsupported filter operator: '{op}'. Supported operators: {', '.join(self.allowed_operators)}"
                        )

                    if op == "IN":
                        if not isinstance(val, (list, tuple)):
                            raise ValidationError("Value for 'IN' operator must be a list or tuple.")
                        if not val:
                            raise ValidationError("Value list for 'IN' operator cannot be empty.")
                        placeholders = ", ".join(["?"] * len(val))
                        where_clauses.append(f"{col} IN ({placeholders})")
                        params.extend(val)
                    else:
                        where_clauses.append(f"{col} {op} ?")
                        params.append(val)
                        
            # Handle simple equality dictionary: {"cohort": "A1"}
            elif isinstance(filters, dict):
                for col, val in filters.items():
                    self._validate_table_and_columns(table, [col])
                    where_clauses.append(f"{col} = ?")
                    params.append(val)
            else:
                raise ValidationError("Filters must be a dictionary or a list of filter dicts.")

        where_str = ""
        if where_clauses:
            where_str = " WHERE " + " AND ".join(where_clauses)

        # 3. Build ORDER BY safely
        order_str = ""
        if order_by:
            self._validate_table_and_columns(table, [order_by])
            direction = "DESC" if descending else "ASC"
            order_str = f" ORDER BY {order_by} {direction}"

        # 4. Assemble query
        query = f"SELECT {cols_str} FROM {table}{where_str}{order_str} LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        conn = self.connect()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = [dict(row) for row in cursor.fetchall()]
            return {
                "table": table,
                "limit": limit,
                "offset": offset,
                "count": len(rows),
                "data": rows
            }
        finally:
            conn.close()

    def insert(self, table, values):
        """
        Inserts a row into the specified table and returns the inserted payload.
        """
        if not isinstance(values, dict) or not values:
            raise ValidationError("Values must be a non-empty dictionary.")

        # Validate table and keys as valid columns
        self._validate_table_and_columns(table, values.keys())

        cols = list(values.keys())
        placeholders = ", ".join(["?"] * len(cols))
        query = f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({placeholders});"
        params = list(values.values())

        conn = self.connect()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            last_id = cursor.lastrowid
            conn.commit()
            
            # Fetch the newly inserted row to return it
            # We assume tables have an auto-incrementing primary key 'id'
            # Let's check if 'id' is in the schema
            schema = self.get_table_schema(table)
            if "id" in schema and last_id is not None:
                cursor.execute(f"SELECT * FROM {table} WHERE id = ?;", (last_id,))
                new_row = cursor.fetchone()
                return dict(new_row) if new_row else values
            return values
        except sqlite3.IntegrityError as e:
            conn.rollback()
            raise ValidationError(f"Database Integrity Error: {e}")
        finally:
            conn.close()

    def aggregate(self, table, metric, column=None, filters=None, group_by=None):
        """
        Runs aggregation queries like count, avg, sum, min, max.
        """
        metric_lower = metric.lower()
        if metric_lower not in self.allowed_metrics:
            raise ValidationError(
                f"Unsupported metric: '{metric}'. Supported metrics: {', '.join(self.allowed_metrics)}"
            )

        # Validate table
        schema = self.get_table_schema(table)

        # Validate column
        if metric_lower == "count" and (column is None or column == "*"):
            col_expr = "*"
        else:
            if not column:
                raise ValidationError(f"Column is required for metric '{metric}'.")
            self._validate_table_and_columns(table, [column])
            col_expr = column

        # Build SELECT clause
        select_clause = f"{metric_lower.upper()}({col_expr}) AS value"
        
        # Validate and add GROUP BY
        group_by_str = ""
        if group_by:
            self._validate_table_and_columns(table, [group_by])
            select_clause = f"{group_by}, {select_clause}"
            group_by_str = f" GROUP BY {group_by}"

        # Validate and build WHERE
        where_clauses = []
        params = []
        if filters:
            if isinstance(filters, dict):
                for col, val in filters.items():
                    self._validate_table_and_columns(table, [col])
                    where_clauses.append(f"{col} = ?")
                    params.append(val)
            elif isinstance(filters, list):
                for f in filters:
                    col = f["column"]
                    op = f["operator"].upper()
                    val = f["value"]
                    self._validate_table_and_columns(table, [col])
                    if op not in self.allowed_operators:
                        raise ValidationError(f"Unsupported operator: {op}")
                    
                    if op == "IN":
                        placeholders = ", ".join(["?"] * len(val))
                        where_clauses.append(f"{col} IN ({placeholders})")
                        params.extend(val)
                    else:
                        where_clauses.append(f"{col} {op} ?")
                        params.append(val)
            else:
                raise ValidationError("Filters must be a dict or structured list.")

        where_str = ""
        if where_clauses:
            where_str = " WHERE " + " AND ".join(where_clauses)

        query = f"SELECT {select_clause} FROM {table}{where_str}{group_by_str}"

        conn = self.connect()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = [dict(row) for row in cursor.fetchall()]
            return {
                "table": table,
                "metric": metric_lower,
                "column": column,
                "group_by": group_by,
                "data": rows
            }
        finally:
            conn.close()
