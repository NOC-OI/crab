import boto3
import couchbeans
import os
import re

s3_region = os.environ.get("S3_REGION")
s3_endpoint = os.environ.get("S3_ENDPOINT")
s3_bucket = os.environ.get("S3_BUCKET")
s3_access_key = os.environ.get("S3_ACCESS_KEY")
s3_secret_key = os.environ.get("S3_SECRET_KEY")

s3client = boto3.client("s3",
    endpoint_url=s3_endpoint,
    aws_access_key_id=s3_access_key,
    aws_secret_access_key=s3_secret_key,
    aws_session_token=None,
    config=boto3.session.Config(signature_version='s3v4'),
    verify=False
)

couch_user = os.environ.get("COUCHDB_ROOT_USER")
couch_password = os.environ.get("COUCHDB_ROOT_PASSWORD")
couch_host = os.environ.get("COUCHDB_HOST")
couch_port = os.environ.get("COUCHDB_PORT", 5984)
couch_base_uri = "http://" + couch_user + ":" + couch_password + "@" + couch_host + ":" + str(couch_port) + "/"

def get_couch_client():
    return couchbeans.CouchClient(couch_base_uri)

def get_s3_client(profile=None):
    return s3client

def get_s3_bucket_name(profile=None):
    return s3_bucket

def get_s3_bucket_uri(profile=None):
    return s3_endpoint + "/" + s3_bucket

def to_snake_case(str_in):
    str_out = re.sub("(?<!^)(?<![A-Z])(?=[A-Z]+)", "_", str_in).lower() # Prepend all strings of uppercase with an underscore
    str_out = re.sub("[^a-z0-9]", "_", str_out) # Replace all non-alphanumeric with underscore
    str_out = re.sub("_+", "_", str_out) # Clean up double underscores
    str_out = re.sub("(^_)|(_$)", "", str_out) # Clean up trailing or leading underscores
    return str_out
