FROM python:3.10

WORKDIR /app

ENV PYTHONUNBUFFERED 1

# install dependencies
RUN pip install --upgrade pip
COPY ./requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 80

ENTRYPOINT ['gunicorn', 'wsgi:app', '--bind', '0.0.0.0:80', '--workers', '5', '--log-level=info', '--access-logfile', "'-'"]