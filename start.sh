#!/bin/bash

gunicorn wsgi:app --bind 0.0.0.0:80  --workers 2 --log-level=info --access-logfile '-'