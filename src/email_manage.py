import base64
from email.message import (
    EmailMessage,
)
from google.oauth2.credentials import (
    Credentials,
)
from googleapiclient.discovery import (
    build,
)
from googleapiclient.errors import (
    HttpError,
)
from typing import (
    Any,
)


def send_form_email(credentials: Credentials, user_to: str, form_link: str):
    try:
        # create gmail api client
        service = build("gmail", "v1", credentials=credentials)

        message = EmailMessage()

        message.set_content(f"Encuesta: {form_link}")

        message["To"] = user_to
        message["From"] = "gduser2@workspacesamples.dev"
        message[
            "Subject"
        ] = f"Encuesta para Determinar la Importancia de Archivos: Por favor, Participa"

        # encoded message
        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

        create_message = {"raw": encoded_message}
        # pylint: disable=E1101
        send_message = (
            service.users()
            .messages()
            .send(userId="me", body=create_message)
            .execute()
        )

        return send_message

    except HttpError as error:
        print(f"An error occurred: {error}")


def send_change_permission_email(
    credentials: Credentials, user_to: str, files: list[dict[str, str]]
):
    try:
        # create gmail api client
        service = build("gmail", "v1", credentials=credentials)

        message = EmailMessage()
        files_string = [
            f'{file["file_name"]} {file["file_url"]}' for file in files
        ]
        message.set_content(
            "A continuación, se enumeran los siguientes archivos públicos que, debido a su nivel de criticidad, es esencial que cambie los permisos a privados.\n"
            + "\n".join(files_string)
        )

        message["To"] = user_to
        message["From"] = "gduser2@workspacesamples.dev"
        message[
            "Subject"
        ] = "Actualizar configuración de privacidad de archivos"

        # encoded message
        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

        create_message = {"raw": encoded_message}
        # pylint: disable=E1101
        send_message = (
            service.users()
            .messages()
            .send(userId="me", body=create_message)
            .execute()
        )

        return send_message

    except HttpError as error:
        print(f"An error occurred: {error}")


def get_me(credentials: Any) -> dict[str, str]:
    service = build("gmail", "v1", credentials=credentials)
    return service.users().getProfile(userId="me").execute()
