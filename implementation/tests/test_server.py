import os
import json
import pytest
import sqlite3
import asyncio
from fastmcp import Client

# Add implementation directory to path to import db and mcp_server
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import SQLiteAdapter, ValidationError
from init_db import create_database
from mcp_server import mcp, adapter as server_adapter

# Use a separate test database for running tests
TEST_DB_NAME = "test_school.db"
test_db_path = None

@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    global test_db_path
    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    # Create the test database
    test_db_path = create_database(TEST_DB_NAME)
    yield
    # Clean up the test database file after tests complete
    if os.path.exists(test_db_path):
        os.remove(test_db_path)

@pytest.fixture
def adapter():
    return SQLiteAdapter(test_db_path)

@pytest.fixture
def mcp_client():
    # Configure mcp server adapter to use test db path temporarily
    original_db_path = server_adapter.db_path
    server_adapter.db_path = test_db_path
    client = Client(mcp)
    yield client
    # Restore original path
    server_adapter.db_path = original_db_path

# ==================== Database Adapter Tests ====================

def test_list_tables(adapter):
    tables = adapter.list_tables()
    assert set(tables) == {"students", "courses", "enrollments"}

def test_get_table_schema(adapter):
    schema = adapter.get_table_schema("students")
    assert "name" in schema
    assert "email" in schema
    assert "cohort" in schema
    assert "score" in schema
    
    with pytest.raises(ValidationError, match="Unknown table"):
        adapter.get_table_schema("non_existent_table")

def test_search_valid(adapter):
    # Retrieve all A1 cohort students
    res = adapter.search("students", filters={"cohort": "A1"}, order_by="name")
    assert res["count"] == 3
    names = [row["name"] for row in res["data"]]
    assert names == ["Alice Nguyen", "Bob Tran", "Eva Vu"]

def test_search_limit_offset(adapter):
    res = adapter.search("students", limit=2, offset=1)
    assert len(res["data"]) == 2
    assert res["limit"] == 2
    assert res["offset"] == 1

def test_search_invalid_table(adapter):
    with pytest.raises(ValidationError, match="Unknown table"):
        adapter.search("teachers")

def test_search_invalid_column(adapter):
    with pytest.raises(ValidationError, match="Unknown column"):
        adapter.search("students", filters={"unknown_col": "val"})

def test_search_unsupported_operator(adapter):
    with pytest.raises(ValidationError, match="Unsupported filter operator"):
        adapter.search("students", filters=[{"column": "score", "operator": "BETWEEN", "value": [10, 20]}])

def test_insert_valid(adapter):
    new_student = {
        "name": "Jack Sparrow",
        "email": "jack@example.com",
        "cohort": "C3",
        "score": 88.5
    }
    inserted = adapter.insert("students", new_student)
    assert inserted["id"] is not None
    assert inserted["name"] == "Jack Sparrow"
    assert inserted["email"] == "jack@example.com"
    
    # Confirm it actually got saved
    res = adapter.search("students", filters={"email": "jack@example.com"})
    assert res["count"] == 1
    assert res["data"][0]["name"] == "Jack Sparrow"

def test_insert_invalid_table(adapter):
    with pytest.raises(ValidationError, match="Unknown table"):
        adapter.insert("teachers", {"name": "Test"})

def test_insert_invalid_column(adapter):
    with pytest.raises(ValidationError, match="Unknown column"):
        adapter.insert("students", {"name": "Test", "non_existent": "Val"})

def test_insert_integrity_error(adapter):
    # Insert existing email
    dup_student = {
        "name": "Alice Dup",
        "email": "alice@example.com",  # Already seeded in database
        "cohort": "A1"
    }
    with pytest.raises(ValidationError, match="Database Integrity Error"):
        adapter.insert("students", dup_student)

def test_aggregate_valid(adapter):
    # Avg score of students in cohort A1
    res = adapter.aggregate("students", "avg", "score", filters={"cohort": "A1"})
    assert res["metric"] == "avg"
    assert len(res["data"]) == 1
    # Seed values: Alice: 85.5, Bob: 72.0, Eva: 88.0. Avg: (85.5 + 72 + 88)/3 = 81.83
    assert abs(res["data"][0]["value"] - 81.833) < 0.01

def test_aggregate_group_by(adapter):
    res = adapter.aggregate("students", "count", "*", group_by="cohort")
    assert res["group_by"] == "cohort"
    assert len(res["data"]) >= 2

def test_aggregate_invalid_column(adapter):
    with pytest.raises(ValidationError, match="Column is required"):
        adapter.aggregate("students", "avg")
        
    with pytest.raises(ValidationError, match="Unknown column"):
        adapter.aggregate("students", "avg", "non_existent_column")

# ==================== MCP Server Client End-to-End Tests ====================

def test_mcp_list_tools(mcp_client):
    async def run():
        async with mcp_client:
            tools = await mcp_client.list_tools()
            names = [t.name for t in tools]
            assert "search" in names
            assert "insert" in names
            assert "aggregate" in names
    asyncio.run(run())

def test_mcp_tool_search(mcp_client):
    async def run():
        async with mcp_client:
            result = await mcp_client.call_tool("search", {
                "table": "students",
                "filters": {"cohort": "B2"}
            })
            data = json.loads(result.content[0].text)
            assert data["table"] == "students"
            assert len(data["data"]) == 2
    asyncio.run(run())

def test_mcp_tool_insert(mcp_client):
    async def run():
        async with mcp_client:
            result = await mcp_client.call_tool("insert", {
                "table": "students",
                "values": {
                    "name": "Grace Hopper",
                    "email": "grace@example.com",
                    "cohort": "A1",
                    "score": 99.0
                }
            })
            resp = json.loads(result.content[0].text)
            assert "successfully inserted" in resp["message"]
            assert resp["inserted_row"]["name"] == "Grace Hopper"
    asyncio.run(run())

def test_mcp_tool_aggregate(mcp_client):
    async def run():
        async with mcp_client:
            result = await mcp_client.call_tool("aggregate", {
                "table": "courses",
                "metric": "sum",
                "column": "credits"
            })
            resp = json.loads(result.content[0].text)
            # Courses seeded: Python (3), Database (4), Machine Learning (3). Sum = 10
            assert resp["data"][0]["value"] == 10
    asyncio.run(run())

def test_mcp_resource_database_schema(mcp_client):
    async def run():
        async with mcp_client:
            resources = await mcp_client.read_resource("schema://database")
            resp = json.loads(resources[0].text)
            assert resp["schema_type"] == "full_database"
            assert "students" in resp["tables"]
            assert "courses" in resp["tables"]
            assert "enrollments" in resp["tables"]
    asyncio.run(run())

def test_mcp_resource_table_schema(mcp_client):
    async def run():
        async with mcp_client:
            resources = await mcp_client.read_resource("schema://table/courses")
            resp = json.loads(resources[0].text)
            assert resp["schema_type"] == "single_table"
            assert resp["table"] == "courses"
            assert resp["columns"]["credits"] == "INTEGER"
    asyncio.run(run())
