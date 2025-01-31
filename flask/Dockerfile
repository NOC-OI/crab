FROM python:3.9.20-bookworm
WORKDIR /app
SHELL ["/bin/bash", "-c"]
RUN pip install flask markdown gunicorn boto3 couchdb requests pillow numpy pyjwt cryptography pygments flasgger microtiff couchbeans pika
COPY src /app
WORKDIR /app
RUN mkdir -p temp
ENTRYPOINT ["gunicorn -w 4 -b 0.0.0.0 'main:app'"]
STOPSIGNAL SIGQUIT
