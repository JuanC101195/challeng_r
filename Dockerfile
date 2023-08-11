FROM python:3.11
RUN apt update
RUN apt install ccrypt
RUN mkdir /app

COPY src/ /app/src/
COPY requirements.txt /app
COPY credentials.json.cpt /app
COPY README.md /app
COPY run.sh /app

WORKDIR /app

ENV PYTHONPATH=${PYTHONPATH}:${PWD}

RUN chmod +x run.sh
RUN pip3 install -r requirements.txt

ENTRYPOINT ["./run.sh"]
