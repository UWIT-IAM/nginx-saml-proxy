FROM python:3.12-slim

# for dependabot
LABEL org.opencontainers.image.source="https://github.com/docker-library/python/tree/master/3.11/slim-bullseye"

RUN apt-get update && \
    apt-get install -y libxmlsec1-dev build-essential libxmlsec1 libxmlsec1-openssl pkg-config && \
    pip install -U xmlsec && \
    apt-get remove -y libxmlsec1-dev build-essential && \
    apt-get autoclean -y && \
    apt-get clean && \
    apt-get autoremove -y

COPY requirements.txt .

RUN pip install -U -r requirements.txt

# patch for gunicorn and eventlet
COPY new_geventlet.py /usr/local/lib/python3.11/site-packages/gunicorn/workers/geventlet.py

WORKDIR /app
COPY . /app
ENV FLASK_APP=app.py

CMD ["gunicorn", "--worker-class", "eventlet", "--bind", ":5000", "app:app"]
