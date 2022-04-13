#! /bin/bash

gunicorn wsgi:app --bind 0.0.0.0:80  --workers 5 --log-level=info --access-logfile '-'