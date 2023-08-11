CREATE TABLE google_drive_users (
    user_email VARCHAR(255) NOT NULL,
    user_name VARCHAR(100) NOT NULL,
    PRIMARY KEY (user_email)
);

CREATE TABLE google_drive_files (
    file_id VARCHAR(255) NOT NULL,
    file_url VARCHAR(255),
    file_name VARCHAR(255),
    file_extension VARCHAR(50),
    file_owner VARCHAR(255),
    file_is_public BOOLEAN,
    severity VARCHAR(50),
    PRIMARY KEY (file_id),
    FOREIGN KEY (file_owner) REFERENCES google_drive_users(user_email)
);

CREATE TABLE google_forms (
    form_id VARCHAR(255) NOT NULL,
    responser_uri VARCHAR(255),
    user_to VARCHAR(255),
    user_from VARCHAR(255),
    PRIMARY KEY (form_id),
    FOREIGN KEY (user_to) REFERENCES google_drive_users(user_email)
);

CREATE TABLE google_forms_files (
    form_id VARCHAR(255) NOT NULL,
    file_id VARCHAR(255) NOT NULL,
    question_id VARCHAR(15),
    FOREIGN KEY (form_id) REFERENCES google_forms(form_id),
    FOREIGN KEY (file_id) REFERENCES google_drive_files(file_id)
)
