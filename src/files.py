from contextlib import (
    suppress,
)
import logging
import mysql.connector
from mysql.connector.connection import (
    MySQLConnection,
)
from mysql.connector.pooling import (
    MySQLConnectionPool,
)
from requests import (
    HTTPError,
)
from src.database import (
    get_connection,
)
from typing import (
    Any,
    NamedTuple,
)

LOGGER = logging.Logger("challeng")


class File(NamedTuple):
    id_: str
    name: str
    extension: str
    owner: str
    is_public: bool
    url: str


def add_file_record(connection_pool: MySQLConnectionPool, file: File) -> None:
    connection = connection_pool.get_connection()
    try:
        cursor = connection.cursor()
        add_file_query = (
            "INSERT INTO google_drive_files "
            "(file_id, file_name, file_extension, file_owner, file_is_public, file_url) "
            "VALUES (%s,%s, %s, %s, %s, %s)"
        )
        file_data = (
            file.id_,
            file.name,
            file.extension,
            file.owner,
            file.is_public,
            file.url,
        )
        cursor.execute(add_file_query, file_data)
        connection.commit()

        cursor.close()
    except mysql.connector.Error as err:
        if err.errno not in (1062,):
            LOGGER.error("Failed to add file record: %s", err)
    connection.close()


def set_file_severity(
    connection_pool: MySQLConnectionPool, question_id: str, new_severity: str
) -> None:
    connection = connection_pool.get_connection()
    try:
        cursor = connection.cursor()
        query = """
            UPDATE google_drive_files AS gdf
            JOIN google_forms_files AS gff ON gdf.file_id = gff.file_id
            SET gdf.severity = %s
            WHERE gff.question_id = %s;
        """
        values = (new_severity, question_id)

        cursor.execute(query, values)

        connection.commit()

        cursor.close()
    except mysql.connector.Error as err:
        if err.errno not in (1062,):
            LOGGER.error("Failed to set file severity: %s", err)
    connection.close()


def file_is_public(permissions: list[dict[str, Any]]) -> bool:
    return any(p["type"] == "anyone" for p in permissions)


def remove_public_permissions(service: Any, file_id: str) -> None:
    file = (
        service.files()
        .get(
            fileId=file_id,
            fields="id, name, owners, fullFileExtension, originalFilename, permissions",
        )
        .execute()
    )
    bad_permission = next(
        (p["id"] for p in file["permissions"] if p["type"] == "anyone"), None
    )
    if not bad_permission:
        return
    try:
        result = (
            service.permissions()
            .delete(fileId=file_id, permissionId=bad_permission)
            .execute()
        )
    except HTTPError as e:
        LOGGER.exception(e)
    return result


def get_all_pubic_files_by_severity(
    connection_pool: MySQLConnectionPool, severity: str
) -> None:
    connection = connection_pool.get_connection()
    result = []
    try:
        cursor = connection.cursor(dictionary=True)
        query = """
            SELECT * from google_drive_files where severity = %s AND file_is_public = TRUE;
            """
        values = (severity,)
        cursor.execute(query, values)
        connection.commit()
        cursor.close()
    except mysql.connector.Error as err:
        if err.errno not in (1062,):
            LOGGER.error("Failed to get all public files by severity: %s", err)
    with suppress(mysql.connector.errors.InterfaceError):
        result = cursor.fetchall()
    connection.close()
    return result
