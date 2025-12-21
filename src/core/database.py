"""
Database connection utilities for Wasteless.

Provides centralized database connection management
for all Wasteless modules.
"""

import os
import sys
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def get_db_connection():
    """
    Get a PostgreSQL database connection.

    Returns:
        psycopg2.connection: Database connection object

    Raises:
        ValueError: If required environment variables are missing
        psycopg2.Error: If connection fails
    """
    # Verify required environment variables
    required_vars = ['DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_USER', 'DB_PASSWORD']
    missing = [var for var in required_vars if not os.getenv(var)]

    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

    # Create connection
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST'),
        port=int(os.getenv('DB_PORT')),
        database=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD')
    )

    return conn


def execute_query(query, params=None, fetch_one=False, fetch_all=False):
    """
    Execute a SQL query with automatic connection management.

    Args:
        query (str): SQL query to execute
        params (tuple, optional): Query parameters
        fetch_one (bool): If True, return one result
        fetch_all (bool): If True, return all results

    Returns:
        Result of query (depends on fetch_one/fetch_all flags)

    Example:
        # Fetch all
        results = execute_query("SELECT * FROM waste_detected", fetch_all=True)

        # Fetch one
        result = execute_query("SELECT * FROM waste_detected WHERE id = %s", (1,), fetch_one=True)

        # Insert/Update (no fetch)
        execute_query("UPDATE recommendations SET status = %s WHERE id = %s", ('completed', 1))
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(query, params)

        if fetch_one:
            result = cursor.fetchone()
        elif fetch_all:
            result = cursor.fetchall()
        else:
            result = None

        conn.commit()
        return result

    except Exception as e:
        conn.rollback()
        raise e

    finally:
        cursor.close()
        conn.close()
