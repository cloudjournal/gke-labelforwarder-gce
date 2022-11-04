from alpine:latest

WORKDIR /app/
ADD . /app/

RUN apk update && apk upgrade --available
RUN apk add --update python3 py3-pip
RUN pip install -r /app/requirements.txt
ENTRYPOINT python3 main.py