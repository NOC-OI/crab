import boto3
import couchbeans
import os
import re
import json
import pika
import pyarrow.fs

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

rabbitmq_credentials = pika.PlainCredentials(os.environ.get("RABBITMQ_DEFAULT_USER", try_get_config_prop("rabbitmq_user")), os.environ.get("RABBITMQ_DEFAULT_PASS", try_get_config_prop("rabbitmq_password")))
rabbitmq_host = os.environ.get("RABBITMQ_HOST", try_get_config_prop("rabbitmq_host", "localhost"))
rabbitmq_port = os.environ.get("RABBITMQ_PORT", try_get_config_prop("rabbitmq_port", 5672))

def get_rabbitmq_connection():
    print("Connecting to RabbitMQ server at " + str(rabbitmq_host) + ":" + str(int(rabbitmq_port)))
    return pika.BlockingConnection(pika.ConnectionParameters(rabbitmq_host, int(rabbitmq_port), "/", rabbitmq_credentials))

def get_couch_client():
    return couchbeans.CouchClient(couch_base_uri)

s3_client_map = {}
s3_fs_map = {}

def get_s3_client(profile=None):
    profile = get_s3_profile(profile)
    if profile["local_id"] not in s3_client_map:
        s3_client_map[profile["local_id"]] = boto3.client("s3",
            endpoint_url=profile["endpoint"],
            aws_access_key_id=profile["access_key"],
            aws_secret_access_key=profile["secret_key"],
            region_name=profile["region"],
            aws_session_token=None,
            config=boto3.session.Config(signature_version='s3v4'),
            verify=False
        )
    return s3_client_map[profile["local_id"]]

def get_s3_fs(profile=None):
    profile = get_s3_profile(profile)
    if profile["local_id"] not in s3_fs_map:
        uri_split = profile["endpoint"].split("://")
        s3_fs_map[profile["local_id"]] = pyarrow.fs.S3FileSystem(
                endpoint_override=uri_split[1],
                scheme=uri_split[0],
                access_key=profile["access_key"],
                secret_key=profile["secret_key"],
                region=profile["region"]
            )
    return s3_fs_map[profile["local_id"]]

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
        profile_copy = crab_config["s3_buckets"][profile]
        profile_copy["local_id"] = profile
        return profile_copy
    raise KeyError("Missing S3 profile: " + str(profile))

def get_s3_bucket_name(profile=None):
    return get_s3_profile(profile)["bucket"]

def get_s3_bucket_endpoint(profile=None):
    return get_s3_profile(profile)["endpoint"]

def get_s3_bucket_uri(profile=None):
    return get_s3_bucket_endpoint(profile) + "/" + get_s3_bucket_name(profile)

def get_s3_bucket_ext_endpoint(profile=None):
    s3_profile_def = get_s3_profile(profile)
    if "external_endpoint" in s3_profile_def:
        return s3_profile_def["external_endpoint"]
    else:
        return s3_profile_def["endpoint"]

def get_s3_bucket_ext_uri(profile=None):
    return get_s3_bucket_ext_endpoint(profile) + "/" + get_s3_bucket_name(profile)

def to_snake_case(str_in):
    str_out = re.sub("(?<!^)(?<![A-Z])(?=[A-Z]+)", "_", str_in).lower() # Prepend all strings of uppercase with an underscore
    str_out = re.sub("[^a-z0-9]", "_", str_out) # Replace all non-alphanumeric with underscore
    str_out = re.sub("_+", "_", str_out) # Clean up double underscores
    str_out = re.sub("(^_)|(_$)", "", str_out) # Clean up trailing or leading underscores
    return str_out
