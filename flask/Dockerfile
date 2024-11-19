FROM python:3.9.20-bookworm
WORKDIR /app
SHELL ["/bin/bash", "-c"]
RUN pip install flask gunicorn boto3 couchdb
COPY src /app
WORKDIR /app
ENTRYPOINT ["gunicorn -w 4 -b 0.0.0.0 'main:app'"]
STOPSIGNAL SIGQUIT
