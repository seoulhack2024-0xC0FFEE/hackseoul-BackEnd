FROM --platform=amd64 python:3.11-alpine

COPY . .
RUN pip install -r requirements.txt

ENTRYPOINT [ "python", "manage.py", "runserver", "0.0.0.0:8000" ]