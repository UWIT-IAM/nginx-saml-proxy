FROM python:3.7
RUN apt-get update && \
    apt-get install -y libxmlsec1-dev && \
    apt-get clean

COPY requirements.txt .

RUN pip install -r requirements.txt

WORKDIR /app
COPY . /app
ENV FLASK_APP=app.py

CMD ["flask", "run", "--host=0.0.0.0"]
