FROM python:3-slim

RUN apt-get update && \
    apt-get install -y libxmlsec1-dev build-essential libxmlsec1 libxmlsec1-openssl && \
    pip install -U xmlsec && \
    apt-get remove -y libxmlsec1-dev build-essential && \
    apt-get autoclean -y && \
    apt-get clean && \
    apt-get autoremove -y

COPY requirements.txt .

RUN pip install -U -r requirements.txt

WORKDIR /app
COPY . /app
ENV FLASK_APP=app.py

CMD ["flask", "run", "--host=0.0.0.0"]
