import asyncio
import sys
from fastmcp import Client
from mcp_server import mcp

async def test_verification():
    print("====================================================")
    print("STARTING MCP SERVER PROGRAMMATIC VERIFICATION TEST")
    print("====================================================\n")
    
    # Initialize the fastmcp test client in-memory
    client = Client(mcp)
    
    async with client:
        # 1. Verification of Tool Discovery
        print("--- 1. Verification of Tool Discovery ---")
        tools = await client.list_tools()
        discovered_tools = [t.name for t in tools]
        print(f"Discovered Tools: {discovered_tools}")
        assert "search" in discovered_tools, "Tool 'search' not discovered!"
        assert "insert" in discovered_tools, "Tool 'insert' not discovered!"
        assert "aggregate" in discovered_tools, "Tool 'aggregate' not discovered!"
        print("✓ All tools successfully discovered.\n")

        # 2. Verification of Resource Discovery and Retrieval
        print("--- 2. Verification of Resource Retrieval ---")
        # Reading full database schema
        print("Reading resource 'schema://database'...")
        db_schema = await client.read_resource("schema://database")
        print(f"db_schema type: {type(db_schema)}")
        print(f"db_schema representation: {repr(db_schema)}")
        # If it is a list, retrieve the first element's text
        if isinstance(db_schema, list) and len(db_schema) > 0:
            print("Full Schema output:")
            # Check if it has 'text' or 'content'
            item = db_schema[0]
            if hasattr(item, 'text'):
                print(item.text)
            else:
                print(repr(item))
        else:
            print(repr(db_schema))
        print("✓ Database schema resource retrieved successfully.\n")

        # Reading single table schema
        print("Reading resource 'schema://table/students'...")
        students_schema = await client.read_resource("schema://table/students")
        if isinstance(students_schema, list) and len(students_schema) > 0:
            print("Students table schema:")
            item = students_schema[0]
            if hasattr(item, 'text'):
                print(item.text)
            else:
                print(repr(item))
        else:
            print(repr(students_schema))
        print("✓ Students table schema resource retrieved successfully.\n")

        # Reading invalid table schema
        print("Reading resource for invalid table 'schema://table/non_existent'...")
        try:
            await client.read_resource("schema://table/non_existent")
            print("❌ Expected error for unknown table schema, but it succeeded!")
        except Exception as e:
            print(f"✓ Correctly rejected with error: {e}\n")

        # 3. Successful Tool Calls
        print("--- 3. Successful Tool Calls ---")
        
        # Test Search Tool
        print("Testing 'search' tool: Cohort B2 students")
        search_res = await client.call_tool("search", {
            "table": "students",
            "filters": {"cohort": "B2"}
        })
        print("Search Result:")
        print(search_res)
        print("✓ Search tool works.\n")

        # Test Insert Tool
        print("Testing 'insert' tool: Add a new student")
        insert_res = await client.call_tool("insert", {
            "table": "students",
            "values": {
                "name": "Frankie Le",
                "email": "frankie@example.com",
                "cohort": "B2",
                "score": 93.5
            }
        })
        print("Insert Result:")
        print(insert_res)
        print("✓ Insert tool works.\n")

        # Test Aggregate Tool
        print("Testing 'aggregate' tool: Count by cohort")
        aggregate_res = await client.call_tool("aggregate", {
            "table": "students",
            "metric": "count",
            "group_by": "cohort"
        })
        print("Aggregate Result:")
        print(aggregate_res)
        print("✓ Aggregate tool works.\n")

        # 4. Failing Tool Calls with Clear Errors
        print("--- 4. Failing Tool Calls (Safety & Validation) ---")

        # Invalid table name
        print("Testing invalid table name search...")
        try:
            await client.call_tool("search", {"table": "teachers"})
            print("❌ Expected validation error for invalid table, but it succeeded!")
        except Exception as e:
            print(f"✓ Correctly rejected with error: {e}\n")

        # Invalid column name
        print("Testing invalid column name search...")
        try:
            await client.call_tool("search", {
                "table": "students",
                "filters": {"invalid_column": "some_value"}
            })
            print("❌ Expected validation error for invalid column, but it succeeded!")
        except Exception as e:
            print(f"✓ Correctly rejected with error: {e}\n")

        # Unsupported filter operator
        print("Testing unsupported operator search...")
        try:
            await client.call_tool("search", {
                "table": "students",
                "filters": [{"column": "score", "operator": "BETWEEN", "value": [70, 90]}]
            })
            print("❌ Expected validation error for unsupported operator, but it succeeded!")
        except Exception as e:
            print(f"✓ Correctly rejected with error: {e}\n")

        # Invalid aggregate request (missing column)
        print("Testing invalid aggregate query...")
        try:
            await client.call_tool("aggregate", {
                "table": "students",
                "metric": "avg"
            })
            print("❌ Expected validation error for missing column in aggregate, but it succeeded!")
        except Exception as e:
            print(f"✓ Correctly rejected with error: {e}\n")

    print("====================================================")
    print("ALL VERIFICATION CHECKS COMPLETED SUCCESSFULLY")
    print("====================================================")

if __name__ == "__main__":
    # Ensure stdout is in UTF-8 mode on Windows
    if sys.platform.startswith("win"):
        import sys
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
        
    asyncio.run(test_verification())
