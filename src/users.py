from __future__ import (
    print_function,
)

from concurrent.futures import (
    ThreadPoolExecutor,
)
import logging
import mysql.connector
from mysql.connector.connection import (
    MySQLConnection,
)
from src.database import (
    get_connection,
)
from typing import (
    Any,
    Dict,
    List,
)

LOGGER = logging.Logger("challeng")


def add_user_record(
    connection: MySQLConnection | None,
    user_email: str,
    user_name: str,
) -> bool:
    connection = connection or get_connection()
    try:
        cursor = connection.cursor()
        add_file_query = (
            "INSERT INTO google_drive_users "
            "(user_email, user_name) "
            "VALUES (%s,%s)"
        )
        file_data = (user_email, user_name)
        cursor.execute(add_file_query, file_data)
        connection.commit()

        cursor.close()
    except mysql.connector.Error as err:
        if err.errno not in (1062,):
            LOGGER.error("Failed to add user record: %s", err)


def get_user_files(service: Any) -> List[dict[str, Any]]:
    request = service.files().list(
        pageSize=10,
        fields="nextPageToken, files(id, name, owners, fullFileExtension, originalFilename, permissions, webViewLink)",
    )
    results = request.execute()
    items: List[Dict[str, Any]] = results.get("files", [])

    while True:
        if "nextPageToken" in results:
            request = service.files().list_next(
                previous_request=request, previous_response=results
            )
            results = request.execute()
            items.extend(results.get("files", []))
            break
        else:
            break
    return items


def create_users(files_raw: list[dict[str, Any]]) -> None:
    users: dict[str, str] = {}
    for file in files_raw:
        for owner in file["owners"]:
            if owner["emailAddress"] in users:
                continue
            users[owner["emailAddress"]] = owner["displayName"]

    with ThreadPoolExecutor() as worker:
        worker.map(
            add_user_record, [None] * len(users), users.keys(), users.values()
        )


def get_all_users(connection: MySQLConnection) -> list[str]:
    """
    Returns the path to the user's credentials file.
    """
    query = """
    SELECT user_email
    FROM google_drive_users
    """

    # Execute the query
    cursor = connection.cursor(dictionary=True)
    cursor.execute(query)

    # Fetch and print the results
    result = cursor.fetchall()

    cursor.close()

    return result
