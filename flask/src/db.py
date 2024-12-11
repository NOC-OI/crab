import boto3
import couchdb
import os

s3_region = os.environ.get("S3_REGION")
s3_endpoint = os.environ.get("S3_ENDPOINT")
s3_bucket = os.environ.get("S3_BUCKET")
s3_access_key = os.environ.get("S3_ACCESS_KEY")
s3_secret_key = os.environ.get("S3_SECRET_KEY")
s3 = boto3.resource("s3",
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
couch = couchdb.Server("http://" + couch_user + ":" + couch_password + "@" + couch_host + ":" + str(couch_port) + "/")

def get_couch():
    return couch

def get_bucket():
    return s3.Bucket(s3_bucket)

def get_bucket_uri():
    return s3_endpoint + "/" + s3_bucket
