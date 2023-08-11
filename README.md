# Instrucciones de Uso

## Requisitos Previos

- Python 3.10 o superior
- Docker y docker-compose
- [Poetry](https://python-poetry.org/) (opcional, pero recomendado para la gestión de dependencias)

## Configuración de la Base de Datos

La base de datos se inicializa y despliega usando Docker y docker-compose.

Para desplegar la base de datos, ejecute:

```bash
docker-compose up
```

La primera vez que se inicie el contenedor, se creará automáticamente la base de datos con las tablas necesarias. Las credenciales predeterminadas para la base de datos se encuentran en el archivo [docker-compose.yaml](docker-compose.yaml). Estas credenciales son para fines demostrativos; si decide cambiarlas, asegúrese de actualizarlas en el archivo [.env](.env) también. Docker-compose también establecerá una red de Docker necesaria para ejecutar la aplicación desde el contenedor.

## Gestión de Credenciales

Las credenciales para acceder a la base de datos se encuentran en el archivo [.env](.env), utilizado para fines de demostración.

## Construcción de la Aplicación

### Mediante Docker

#### Construcción de la Imagen Docker

Ejecute el siguiente comando:

```bash
docker build -t challeng-r .
```

Esto creará una imagen de Docker denominada "challeng-r".

### Ejecución Local (sin Docker)

#### Requisitos

- Python 3.10 o superior
- pip
- [Poetry](https://python-poetry.org/) (opcional)

Instale las dependencias con:

```bash
pip install -r requirements.txt
```

Si está usando Poetry:

```bash
poetry install
```

Esto instalará las dependencias necesarias y también un script llamado `drive-m`.

## Ejecución de la Aplicación

La aplicación tiene una interfaz de línea de comandos (CLI) con tres opciones:

- `--scan`: Escanea todos los archivos del usuario y los guarda en la base de datos.
- `--send-forms`: Envía formularios a los propietarios de los archivos.
- `--process-forms`: Analiza las respuestas de los formularios y envía un correo para que el usuario modifique los permisos.

### Mediante Docker

Ejecute:

```bash
docker run \
  --rm \
  -it \
  --network challeng_r_challeng \
  -p 8081:8081 \
  --env-file ./.env \
  --env CRED_KEY="<YOUR-CRED-KEY>" \
  challeng-r --scan
```

Donde:

- `--env-file ./.env`: Suministra las variables para la conexión a la base de datos.
- `--network challeng_r_challeng`: Conecta el contenedor a la red donde se ejecuta la base de datos.
- Reemplace `<YOUR-CRED-KEY>`: Es necesario para descifrar las credenciales del API de Google.
- `challeng-r`: Es el nombre de la imagen de Docker previamente construida.
- `--scan`: Indica la acción a realizar por la aplicación.

### Mediante Python

Para ejecutar con Python, primero descifre el archivo de credenciales para el API de Google usando el programa `ccrypt` ([Guía de instalación](https://ccrypt.sourceforge.net/#downloading)). Además, modifique el valor de `MYSQL_HOST` en el archivo [.env](.env) a `127.0.0.1` o `localhost`.

Descifre el archivo:

```bash
ccrypt -d --key "<YOUR-CRED-KEY>" credentials.json.cpt
```

Ejecución con Poetry:

```bash
poetry run drive-m --scan
```

Ejecución directa con Python:

```bash
python3 src/__init__.py
```

## Consideraciones Adicionales

- Detección de archivos públicos: El único permiso que puede detectarse como público es aquel que permite el acceso a cualquier persona con el enlace.
