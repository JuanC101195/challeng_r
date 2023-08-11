from apiclient import (
    discovery,
)
from concurrent.futures import (
    ThreadPoolExecutor,
)
from google.oauth2.credentials import (
    Credentials,
)
from itertools import (
    repeat,
)
import logging
import mysql.connector
from mysql.connector.connection import (
    MySQLConnection,
)
from mysql.connector.pooling import (
    MySQLConnectionPool,
)
from os import (
    cpu_count,
)
import os.path
from src.database import (
    get_connection,
    get_connection_pool,
)
from typing import (
    Any,
)

DISCOVERY_DOC = "https://forms.googleapis.com/$discovery/rest?version=v1"
LOGGER = logging.Logger("challeng")


def _get_user_files(
    connection: MySQLConnection, user_email: str
) -> list[dict[str, str]]:
    """
    Returns the path to the user's credentials file.
    """
    query = """
SELECT gdf.file_id, gdf.file_name, gdf.file_is_public, gdf.file_url
FROM google_drive_files AS gdf
JOIN google_drive_users AS gdu ON gdf.file_owner = gdu.user_email
WHERE gdu.user_email = %s;
"""

    # Execute the query
    cursor = connection.cursor(dictionary=True)
    cursor.execute(query, (user_email,))

    # Fetch and print the results
    return cursor.fetchall()


def _build_question_for_file(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "questionItem": {
            "question": {
                "required": True,
                "choiceQuestion": {
                    "type": "CHECKBOX",
                    "options": [
                        {
                            "value": "está relacionado con procesos legales o confidenciales?"
                        },
                        {
                            "value": "se comparte con partes externas a la organización?"
                        },
                        {
                            "value": "es necesario para la operación diaria de la empresa?"
                        },
                        {"value": "está en uso activo en proyectos actuales?"},
                        {
                            "value": "contiene información de uso común y conocida?"
                        },
                    ],
                    "shuffle": False,
                },
            }
        },
        "title": f'El archivo {item["file_name"]} -> {item["file_url"]}',
    }


def _add_form_record(
    connection: MySQLConnection,
    form_id: str,
    user_dest_email: str,
    responser_uri: str,
    *,
    user_me: str,
) -> bool:
    try:
        cursor = connection.cursor()
        query = (
            "INSERT INTO google_forms "
            "(form_id, user_to, responser_uri, user_from) "
            "VALUES (%s,%s,%s,%s)"
        )
        file_data = (form_id, user_dest_email, responser_uri, user_me)
        cursor.execute(query, file_data)
        connection.commit()
        cursor.close()
    except mysql.connector.Error as err:
        if err.errno not in (1062,):
            LOGGER.error("Failed to add form record: %s", err)
    return True


def get_user_forms(connection: MySQLConnection, user: str) -> dict[str, Any]:
    query = """
    SELECT user_to, form_id, responser_uri FROM google_forms WHERE user_from = %s;
    """
    cursor = connection.cursor(dictionary=True)
    cursor.execute(query, (user,))
    result = cursor.fetchall()
    cursor.close()
    return result


def _assign_file_to_form(
    pool: MySQLConnectionPool, form_id: str, file_id: str, question_id: str
) -> None:
    connection = pool.get_connection()
    try:
        cursor = connection.cursor()
        query = "INSERT INTO google_forms_files (form_id, file_id, question_id) VALUES (%s, %s, %s);"
        values = (form_id, file_id, question_id)

        # Execute the query
        cursor.execute(query, values)

        connection.commit()
        cursor.close()
    except mysql.connector.Error as err:
        if err.errno not in (1062,):
            LOGGER.error("Failed to add file to form: %s", err)
    connection.close()


def _file_exists_in_form(pool: MySQLConnectionPool, file_id: str) -> bool:
    connection = pool.get_connection()
    try:
        cursor = connection.cursor()
        query = "SELECT * FROM google_forms_files WHERE file_id = %s;"
        values = (file_id,)

        # Execute the query
        cursor.execute(query, values)

        result = cursor.fetchall()
        cursor.close()
    except mysql.connector.Error as err:
        if err.errno not in (1062,):
            LOGGER.error("Failed to check if file exists: %s", err)

    connection.close()
    return len(result) > 0


def create_form_for_user(
    credentials: Credentials,
    connection_pool: MySQLConnectionPool,
    user_email: str,
    *,
    me_email: str,
) -> None:
    form_service = discovery.build(
        "forms",
        "v1",
        credentials=credentials,
        discoveryServiceUrl=DISCOVERY_DOC,
        static_discovery=False,
    )
    with connection_pool.get_connection() as connection:
        user_files = _get_user_files(connection, user_email)

    with ThreadPoolExecutor() as executor:
        files_in_forms = dict(
            executor.map(
                lambda x: (
                    x["file_id"],
                    _file_exists_in_form(connection_pool, x["file_id"]),
                ),
                user_files,
            )
        )
    user_files = [
        file for file in user_files if not files_in_forms[file["file_id"]]
    ]
    if not user_files:
        LOGGER.warning("No hay archivos para el usuario %s", user_email)
        return

    # Build the form with the questions
    items = [_build_question_for_file(item) for item in user_files]
    result_new_form = (
        form_service.forms()
        .create(
            body={
                "info": {
                    "title": "Uso de archivos compartidos",
                }
            }
        )
        .execute()
    )

    result_update = (
        form_service.forms()
        .batchUpdate(
            formId=result_new_form["formId"],
            body={
                "requests": [
                    {
                        "createItem": {
                            "item": item,
                            "location": {"index": index},
                        }
                    }
                    for index, item in enumerate(items)
                ]
            },
        )
        .execute()
    )

    with connection_pool.get_connection() as connection:
        _add_form_record(
            connection,
            result_new_form["formId"],
            user_email,
            result_new_form["responderUri"],
            user_me=me_email,
        )

    question_ids = [
        reply["createItem"]["questionId"][0]
        for reply in result_update["replies"]
    ]
    with ThreadPoolExecutor() as executor:
        executor.map(
            _assign_file_to_form,
            repeat(connection_pool),
            repeat(result_new_form["formId"]),
            [file["file_id"] for file in user_files],
            question_ids,
        )


def get_form_response(credentials: Credentials, form_id: str) -> None:
    service = discovery.build(
        "forms",
        "v1",
        credentials=credentials,
        discoveryServiceUrl=DISCOVERY_DOC,
        static_discovery=False,
    )

    # Prints the title of the sample form:
    result = service.forms().responses().list(formId=form_id).execute()
    return result["responses"][0]["answers"]


def process_answers_severity(answers: list[dict[str, str]]) -> str:
    severities = []
    answers_map = {
        "está relacionado con procesos legales o confidenciales?": 4,
        "es necesario para la operación diaria de la empresa?": 3,
        "se comparte con partes externas a la organización?": 2,
        "está en uso activo en proyectos actuales?": 2,
        "contiene información de uso común y conocida?": 1,
    }
    severity_map = {
        4: "Critico",
        3: "Alto",
        2: "Medio",
        1: "Bajo",
        0: "Desconocido",
    }
    for answer in answers:
        if severity_value := answers_map.get(answer["value"]):
            severities.append(severity_value)

    return severity_map.get(
        (max(severities) if severities else 0), "Desconocido"
    )


def get_file_questions_in_form(
    connection: MySQLConnection, form_id: str
) -> list[dict[str, str]]:
    query = """
    SELECT * FROM google_forms_files WHERE form_id = %s;
    """
    cursor = connection.cursor(dictionary=True)
    cursor.execute(query, (form_id,))
    result = cursor.fetchall()
    cursor.close()
    return result
