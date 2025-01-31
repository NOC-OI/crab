FROM python:3.9.20-bookworm
WORKDIR /app
SHELL ["/bin/bash", "-c"]
RUN pip install boto3 requests pillow numpy pyjwt cryptography microtiff couchbeans pika
COPY src /app
WORKDIR /app
RUN mkdir -p temp
ENTRYPOINT ["python3 main.py"]
STOPSIGNAL SIGQUIT
