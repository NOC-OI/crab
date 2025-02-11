import boto3
import couchdb
import couchbeans
import os
import pika
import uuid
import sys
import json

config_file_loc = os.environ.get("CRAB_CONFIG_FILE", "config.json")
crab_config = {}
with open(config_file_loc, "r") as f:
    crab_config = json.load(f)

def try_get_config_prop(property_name, alternate=None):
    if property_name in crab_config:
        return crab_config["property_name"]
    return alternate

couch_user = os.environ.get("COUCHDB_ROOT_USER", try_get_config_prop("couchdb_user"))
couch_password = os.environ.get("COUCHDB_ROOT_PASSWORD", try_get_config_prop("couchdb_password"))
couch_host = os.environ.get("COUCHDB_HOST", try_get_config_prop("couchdb_host", "localhost"))
couch_port = os.environ.get("COUCHDB_PORT", try_get_config_prop("couchdb_port", 5984))
couch_base_uri = "http://" + couch_user + ":" + couch_password + "@" + couch_host + ":" + str(couch_port) + "/"
couch = couchdb.Server(couch_base_uri)

rabbitmq_credentials = pika.PlainCredentials(os.environ.get("RABBITMQ_DEFAULT_USER", try_get_config_prop("rabbitmq_user")), os.environ.get("RABBITMQ_DEFAULT_PASS", try_get_config_prop("rabbitmq_password")))
rabbitmq_host = os.environ.get("RABBITMQ_HOST", try_get_config_prop("rabbitmq_host", "localhost"))
rabbitmq_port = os.environ.get("RABBITMQ_PORT", try_get_config_prop("rabbitmq_port", 5672))

# Provided for backwards compatibility
# References to these functions should be removed as code is updated
def get_couch():
    return couch
def get_couchpotato():
    return couchbeans.CouchClient(couch_base_uri)
def get_s3_resource(profile=None):
    profile = get_s3_profile(profile)
    resource = boto3.resource("s3",
        endpoint_url=profile["endpoint"],
        aws_access_key_id=profile["access_key"],
        aws_secret_access_key=profile["secret_key"],
        aws_session_token=None,
        config=boto3.session.Config(signature_version='s3v4'),
        verify=False
    )
    return resource
def get_bucket():
    return get_s3_resource().Bucket(get_s3_bucket_name())
def get_bucket_object(full_path = None, path = None):
    return get_s3_client().get_object(Bucket=get_s3_bucket_name(), Key=path)
def get_bucket_name():
    return get_s3_bucket_name()
def get_bucket_uri():
    return get_s3_bucket_uri()
def get_couch_base_uri():
    return couch_base_uri



def get_couch_client():
    return couchbeans.CouchClient(couch_base_uri)

def advertise_job(job_id):
    connection = pika.BlockingConnection(pika.ConnectionParameters(rabbitmq_host, rabbitmq_port, "/", rabbitmq_credentials))
    channel = connection.channel()
    channel.queue_declare(queue="crab_jobs")
    channel.basic_publish(exchange="", routing_key="crab_jobs", body=job_id)
    connection.close()

def get_s3_client(profile=None):
    profile = get_s3_profile(profile)
    client = boto3.client("s3",
        endpoint_url=profile["endpoint"],
        aws_access_key_id=profile["access_key"],
        aws_secret_access_key=profile["secret_key"],
        aws_session_token=None,
        config=boto3.session.Config(signature_version='s3v4'),
        verify=False
    )
    return client

def get_default_s3_profile_name():
    return crab_config["default_s3_bucket"]

def get_s3_profiles():
    return crab_config["s3_buckets"]

def get_s3_profile(profile=None):
    if profile == None:
        profile = crab_config["default_s3_bucket"]
    if len(profile) == 0:
        profile = crab_config["default_s3_bucket"]
    if profile in crab_config["s3_buckets"]:
        return crab_config["s3_buckets"][profile]
    raise KeyError("Missing S3 profile: " + str(profile))

def get_s3_bucket_name(profile=None):
    return get_s3_profile(profile)["bucket"]

def get_s3_bucket_endpoint(profile=None):
    return get_s3_profile(profile)["endpoint"]

def get_s3_bucket_uri(profile=None):
    return get_s3_bucket_endpoint(profile) + "/" + get_s3_bucket_name(profile)
