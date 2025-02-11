import boto3
import couchbeans
import os
import re
import json

config_file_loc = os.environ.get("CRAB_CONFIG_FILE", "config.json")
crab_config = {}
with open(config_file_loc, "r") as f:
    crab_config = json.load(f)

def try_get_config_prop(property_name, alternate=None):
    if property_name in crab_config:
        return crab_config["property_name"]
    return alternate

couch_user = os.environ.get("COUCHDB_ROOT_USER")
couch_password = os.environ.get("COUCHDB_ROOT_PASSWORD")
couch_host = os.environ.get("COUCHDB_HOST")
couch_port = os.environ.get("COUCHDB_PORT", 5984)
couch_base_uri = "http://" + couch_user + ":" + couch_password + "@" + couch_host + ":" + str(couch_port) + "/"

def get_couch_client():
    return couchbeans.CouchClient(couch_base_uri)

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

def to_snake_case(str_in):
    str_out = re.sub("(?<!^)(?<![A-Z])(?=[A-Z]+)", "_", str_in).lower() # Prepend all strings of uppercase with an underscore
    str_out = re.sub("[^a-z0-9]", "_", str_out) # Replace all non-alphanumeric with underscore
    str_out = re.sub("_+", "_", str_out) # Clean up double underscores
    str_out = re.sub("(^_)|(_$)", "", str_out) # Clean up trailing or leading underscores
    return str_out
