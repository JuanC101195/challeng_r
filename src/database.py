import mysql.connector
from mysql.connector.connection import (
    MySQLConnection,
)
from mysql.connector.pooling import (
    MySQLConnectionPool,
)
import os
import os.path


def get_connection() -> MySQLConnection:
    return mysql.connector.connect(
        host=os.environ["MYSQL_HOST"],
        user=os.environ["MYSQL_USER"],
        password=os.environ["MYSQL_PASSWORD"],
        database=os.environ["MYSQL_DATABASE"],
    )


def get_connection_pool(pool_size: int | None = None) -> MySQLConnectionPool:
    pool_size = pool_size or (os.cpu_count() or 8) + 2
    dbconfig = {
        "host": os.environ["MYSQL_HOST"],
        "user": os.environ["MYSQL_USER"],
        "password": os.environ["MYSQL_PASSWORD"],
        "database": os.environ["MYSQL_DATABASE"],
    }

    # Create a connection pool with 5 connections
    return MySQLConnectionPool(
        pool_name="concurrent", pool_size=pool_size, **dbconfig
    )
