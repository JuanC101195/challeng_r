from __future__ import (
    print_function,
)

import argparse
from concurrent.futures import (
    ThreadPoolExecutor,
)
from dotenv import (
    load_dotenv,
)
from google.auth.transport.requests import (
    Request,
)
from google.oauth2.credentials import (
    Credentials,
)
from google_auth_oauthlib.flow import (
    InstalledAppFlow,
)
from googleapiclient.discovery import (
    build,
)
from googleapiclient.errors import (
    HttpError,
)
from itertools import (
    repeat,
)
import logging
import os.path
from pathlib import (
    Path,
)
from src.database import (
    get_connection,
    get_connection_pool,
)
from src.email_manage import (
    get_me,
    send_change_permission_email,
    send_form_email,
)
from src.files import (
    add_file_record,
    File,
    file_is_public,
    get_all_pubic_files_by_severity,
    set_file_severity,
)
from src.forms import (
    create_form_for_user,
    get_file_questions_in_form,
    get_form_response,
    get_user_forms,
    process_answers_severity,
)
from src.users import (
    create_users,
    get_all_users,
    get_user_files,
)
from typing import (
    Optional,
)

load_dotenv()

LOGGER = logging.Logger("challeng")

# If modifying these scopes, delete the file token.json.
SCOPES = [
    "https://www.googleapis.com/auth/drive.metadata.readonly",
    # "https://www.googleapis.com/auth/drive",
    # "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/forms.body",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/forms.responses.readonly",
]
DISCOVERY_DOC = "https://forms.googleapis.com/$discovery/rest?version=v1"


def get_user_credentials() -> Optional[Credentials]:
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists(Path("token.json")):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                Path("credentials.json"),
                SCOPES,
            )
            creds = flow.run_local_server(
                port=8081, bind_addr="0.0.0.0", open_browser=False
            )
        # Save the credentials for the next run
        with open("token.json", "w", encoding="utf-8") as token:
            token.write(creds.to_json())
    return creds


def send_severity_forms() -> None:
    connection_pool = get_connection_pool()
    with connection_pool.get_connection() as connection:
        all_users = get_all_users(connection)
    credentials = get_user_credentials()
    user_me = get_me(credentials)
    all_users = [
        user
        for user in all_users
        if user["user_email"] == "juan.cardozor@udea.edu.co"
    ]
    with ThreadPoolExecutor() as executor:
        executor.map(
            lambda user: create_form_for_user(
                credentials,
                connection_pool,
                user["user_email"],
                me_email=user_me["emailAddress"],
            ),
            all_users,
        )
    # send all forms to all users
    with connection_pool.get_connection() as connection:
        all_forms = get_user_forms(connection, user_me["emailAddress"])

    all_forms = [
        form
        for form in all_forms
        if form["user_to"] == "juan.cardozor@udea.edu.co"
    ]

    with ThreadPoolExecutor() as executor:
        executor.map(
            lambda form: send_form_email(
                credentials, form["user_to"], form["responser_uri"]
            ),
            all_forms,
        )


def scan_user_files() -> None:
    pool = get_connection_pool()
    credentials = get_user_credentials()

    if not credentials:
        LOGGER.error("Credentials not found")
        return
    try:
        service = build("drive", "v3", credentials=credentials)

        files_raw = get_user_files(service)
        files = [
            File(
                id_=item["id"],
                name=item["name"],
                extension=item.get("fullFileExtension", None),
                owner=item["owners"][0]["emailAddress"],
                is_public=file_is_public(item.get("permissions", [])),
                url=item["webViewLink"],
            )
            for item in files_raw
        ]

        create_users(files_raw)

        with ThreadPoolExecutor() as worker:
            worker.map(add_file_record, repeat(pool), files)

    except HttpError as error:
        print(f"An error occurred: {error}")


def process_results() -> None:
    connection_pool = get_connection_pool()
    connection = connection_pool.get_connection()
    credentials = get_user_credentials()
    user_me = get_me(credentials)
    with connection_pool.get_connection() as connection:
        all_forms = get_user_forms(connection, user_me["emailAddress"])
    for form in all_forms:
        form_response = get_form_response(
            get_user_credentials(), form["form_id"]
        )
        if not form_response:
            continue

        with connection_pool.get_connection() as connection:
            questions_dict = {
                question["question_id"]: {
                    **question,
                    **(
                        {
                            "severity": process_answers_severity(
                                form_response[question["question_id"]][
                                    "textAnswers"
                                ]["answers"]
                            )
                        }
                        if question["question_id"] in form_response
                        else {}
                    ),
                }
                for question in get_file_questions_in_form(
                    connection, form["form_id"]
                )
            }
    with ThreadPoolExecutor() as worker:
        worker.map(
            set_file_severity,
            repeat(connection_pool),
            [
                key
                for key, value in questions_dict.items()
                if "severity" in value
            ],
            [
                value["severity"]
                for value in questions_dict.values()
                if "severity" in value
            ],
        )
    public_files = [
        *get_all_pubic_files_by_severity(connection_pool, "Critico"),
        *get_all_pubic_files_by_severity(connection_pool, "Alto"),
    ]
    with ThreadPoolExecutor() as worker:
        files_by_user_dict: dict[str, list[dict[str, str]]] = {}
        for file in public_files:
            files_by_user_dict.setdefault(file["file_owner"], []).append(file)
        worker.map(
            send_change_permission_email,
            repeat(credentials),
            files_by_user_dict.keys(),
            files_by_user_dict.values(),
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="A simple CLI for managing Google Drive files and forms."
    )
    parser.add_argument(
        "--scan",
        help="Scan user files, shared files with user",
        action="store_true",
    )
    parser.add_argument(
        "--send-forms",
        help="Send forms severity to users",
        action="store_true",
    )
    parser.add_argument(
        "--process-forms", help="Process forms results", action="store_true"
    )

    args = parser.parse_args()
    if args.scan:
        scan_user_files()
    elif args.send_forms:
        send_severity_forms()
    elif args.process_forms:
        process_results()
    else:
        LOGGER.warning("You must provide a valid argument")


if __name__ == "__main__":
    main()
