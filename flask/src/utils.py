import uuid
import re
from flask import request
from db import get_couch

global_vars = {
        "brand": "CRAB",
        "long_brand": "Centralised Repository for Annotations and BLOBs"
    }

def get_app_frontend_globals():
    return global_vars

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
        bearer_token_components = bearer_token.split(".")
        if len(bearer_token_components) > 1:
            raw_session_id = bearer_token_components[0]
            access_token = bearer_token_components[1]
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
            return session_info
    return None
