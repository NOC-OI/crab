import uuid
import re
import os
from datetime import datetime
from flask import request
from db import get_couch
import random
import string
import secrets
import json

config_file_loc = os.environ.get("CRAB_CONFIG_FILE", "config.json")
crab_config = {}
with open(config_file_loc, "r") as f:
    crab_config = json.load(f)

def try_get_config_prop(property_name, alternate=None):
    if property_name in crab_config:
        return crab_config[property_name]
    return alternate

csrf_secret_key = os.environ.get("CRAB_CSRF_SECRET_KEY", try_get_config_prop("csrf_secret_key"))
if csrf_secret_key == None:
    if not os.path.isfile(".crab_temp_csrf_secretkey"):
        with open(".crab_temp_csrf_secretkey", "w") as f:
            f.write(secrets.token_urlsafe(24))
    with open(".crab_temp_csrf_secretkey", "r") as f:
        csrf_secret_key = f.read()

def get_csrf_secret_key():
    print(csrf_secret_key)
    return csrf_secret_key

def get_crab_external_endpoint():
    crab_external_endpoint = "http://" + os.environ.get("CRAB_EXTERNAL_HOST") + ":" + os.environ.get("CRAB_EXTERNAL_PORT") + "/"
    if os.environ.get("CRAB_EXTERNAL_PORT") == "80":
        crab_external_endpoint = "http://" + os.environ.get("CRAB_EXTERNAL_HOST") + "/"
    elif os.environ.get("CRAB_EXTERNAL_PORT") == "443":
        crab_external_endpoint = "https://" + os.environ.get("CRAB_EXTERNAL_HOST") + "/"
    return crab_external_endpoint

def get_app_frontend_globals():
    return {
        "brand": crab_config["brand"],
        "long_brand": crab_config["long_brand"]
    }

def to_snake_case(str_in):
    str_out = re.sub("(?<!^)(?<![A-Z])(?=[A-Z]+)", "_", str_in).lower() # Prepend all strings of uppercase with an underscore
    str_out = re.sub("[^a-z0-9]", "_", str_out) # Replace all non-alphanumeric with underscore
    str_out = re.sub("_+", "_", str_out) # Clean up double underscores
    str_out = re.sub("(^_)|(_$)", "", str_out) # Clean up trailing or leading underscores
    return str_out

def get_session_info():
    session_uuid = None
    raw_session_id = None
    access_token = None
    bearer_token = request.headers.get("authorization")
    if not bearer_token is None:
        #print(bearer_token)
        bearer_token_components = bearer_token.split(" ")
        if len(bearer_token_components) > 1:
            if bearer_token_components[0].lower() == "bearer":
                bearer_token_components = bearer_token_components[1].split(".")
                if len(bearer_token_components) > 1:
                    raw_session_id = bearer_token_components[0]
                    access_token = bearer_token_components[1]
                #print(raw_session_id)
                #print(access_token)
    if raw_session_id is None:
        raw_session_id = request.cookies.get("sessionId")
        access_token = request.cookies.get("sessionKey")
    if raw_session_id is None:
        return None
    try:
        uuid_obj = uuid.UUID(raw_session_id, version=4)
        session_uuid = str(uuid_obj)
    except ValueError:
        return None
    session_info = get_couch()["crab_sessions"][session_uuid].copy()
    if session_info["status"] == "ACTIVE":
        if session_info["access_token"] == access_token:
            session_info["session_uuid"] = session_uuid
            session_info["ip_addr"] = request.remote_addr
            session_info["last_active"] = (datetime.utcnow() - datetime(1970, 1, 1)).total_seconds()
            get_couch()["crab_sessions"][session_uuid] = session_info
            return session_info
    return None
