FROM python:3.10-slim-buster

LABEL maintainer="vuanhtien0208@gmail.com"

ENV PYTHONUNBUFFERED=1

WORKDIR /usr/src/app

COPY requirements.txt .

RUN pip3 install --upgrade pip
RUN pip3 install -r requirements.txt

COPY ./core .

CMD ["sh", "-c", "python manage.py makemigrations && python manage.py migrate && python manage.py runserver 0.0.0.0:8000"]
