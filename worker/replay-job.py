#!/usr/bin/env python
import pika
import os
import uuid
import sys

credentials = pika.PlainCredentials(os.environ.get("RABBITMQ_DEFAULT_USER"), os.environ.get("RABBITMQ_DEFAULT_PASS"))
connection = pika.BlockingConnection(pika.ConnectionParameters("localhost", 5672, "/", credentials))
channel = connection.channel()
channel.queue_declare(queue="crab_jobs")
uuid_str = sys.argv[1]
channel.basic_publish(exchange="", routing_key="crab_jobs", body=uuid_str)
print("Replaying job " + uuid_str + "")
connection.close()
