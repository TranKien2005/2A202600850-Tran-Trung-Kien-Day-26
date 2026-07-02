import os
import json
from typing import Union, List, Dict, Any, Optional
from fastmcp import FastMCP
from db import SQLiteAdapter, ValidationError

# Initialize the FastMCP server
mcp = FastMCP("SQLite Lab Server")

# Instantiate the SQLite Adapter pointing to school.db in the same directory
script_dir = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(script_dir, "school.db")
adapter = SQLiteAdapter(db_path)

@mcp.tool(name="search")
def search(
    table: str,
    filters: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]] = None,
    columns: Optional[List[str]] = None,
    limit: int = 20,
    offset: int = 0,
    order_by: Optional[str] = None,
    descending: bool = False
) -> str:
    """
    Search database records safely with support for filtering, ordering, and pagination.

    Args:
        table: The table name to search ('students', 'courses', 'enrollments').
        filters: Optional criteria. A simple dict (e.g. {"cohort": "A1"}) or structured list (e.g. [{"column": "score", "operator": ">", "value": 80.0}]).
        columns: Optional list of specific columns to retrieve. If None, retrieves all columns.
        limit: Max number of rows to return (default 20).
        offset: Number of rows to skip (default 0).
        order_by: Optional column name to sort results by.
        descending: Set to True for descending sort, False for ascending (default False).
    """
    try:
        # Handle string input if LLM passes filters as JSON string
        if isinstance(filters, str):
            try:
                filters = json.loads(filters)
            except json.JSONDecodeError:
                raise ValidationError("Filters parameter was passed as an invalid JSON string.")

        result = adapter.search(
            table=table,
            columns=columns,
            filters=filters,
            limit=limit,
            offset=offset,
            order_by=order_by,
            descending=descending
        )
        return json.dumps(result, indent=2, ensure_ascii=False)
    except ValidationError as e:
        raise ValueError(f"Validation Error: {e}")
    except Exception as e:
        raise RuntimeError(f"Internal Server Error: {e}")

@mcp.tool(name="insert")
def insert(table: str, values: Dict[str, Any]) -> str:
    """
    Insert a new row into the specified database table. Returns the inserted payload.

    Args:
        table: The table name to insert into ('students', 'courses', 'enrollments').
        values: A dictionary of column names to values to be inserted.
    """
    try:
        # Handle string input if LLM passes values as JSON string
        if isinstance(values, str):
            try:
                values = json.loads(values)
            except json.JSONDecodeError:
                raise ValidationError("Values parameter was passed as an invalid JSON string.")

        result = adapter.insert(table=table, values=values)
        return json.dumps({
            "message": "Row successfully inserted.",
            "inserted_row": result
        }, indent=2, ensure_ascii=False)
    except ValidationError as e:
        raise ValueError(f"Validation Error: {e}")
    except Exception as e:
        raise RuntimeError(f"Internal Server Error: {e}")

@mcp.tool(name="aggregate")
def aggregate(
    table: str,
    metric: str,
    column: Optional[str] = None,
    filters: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]] = None,
    group_by: Optional[str] = None
) -> str:
    """
    Perform aggregation queries (COUNT, AVG, SUM, MIN, MAX) on a database table.

    Args:
        table: The table name to aggregate ('students', 'courses', 'enrollments').
        metric: The aggregation function to apply ('count', 'avg', 'sum', 'min', 'max').
        column: The target column for aggregation (required for all except 'count').
        filters: Optional criteria. A simple dict or structured list of filters.
        group_by: Optional column name to group results by.
    """
    try:
        # Handle string input if LLM passes filters as JSON string
        if isinstance(filters, str):
            try:
                filters = json.loads(filters)
            except json.JSONDecodeError:
                raise ValidationError("Filters parameter was passed as an invalid JSON string.")

        result = adapter.aggregate(
            table=table,
            metric=metric,
            column=column,
            filters=filters,
            group_by=group_by
        )
        return json.dumps(result, indent=2, ensure_ascii=False)
    except ValidationError as e:
        raise ValueError(f"Validation Error: {e}")
    except Exception as e:
        raise RuntimeError(f"Internal Server Error: {e}")

@mcp.resource("schema://database")
def database_schema() -> str:
    """
    Retrieve the full database schema detailing all tables, columns, and their data types.
    """
    try:
        tables = adapter.list_tables()
        full_schema = {}
        for table in tables:
            full_schema[table] = adapter.get_table_schema(table)
        
        return json.dumps({
            "schema_type": "full_database",
            "tables": full_schema
        }, indent=2, ensure_ascii=False)
    except Exception as e:
        raise RuntimeError(f"Error fetching database schema: {e}")

@mcp.resource("schema://table/{table_name}")
def table_schema(table_name: str) -> str:
    """
    Retrieve the schema details for a specific table in the database.

    Args:
        table_name: The name of the table ('students', 'courses', or 'enrollments').
    """
    try:
        schema = adapter.get_table_schema(table_name)
        return json.dumps({
            "schema_type": "single_table",
            "table": table_name,
            "columns": schema
        }, indent=2, ensure_ascii=False)
    except ValidationError as e:
        raise ValueError(f"Validation Error: {e}")
    except Exception as e:
        raise RuntimeError(f"Error fetching table schema: {e}")

if __name__ == "__main__":
    mcp.run()
