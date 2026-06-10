#!/bin/sh

# update database version
.venv/bin/alembic -c ./chatapi/alembic.ini upgrade head

.venv/bin/python main.py
