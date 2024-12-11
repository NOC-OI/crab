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
    raw_session_id = request.cookies.get("sessionId")
    if raw_session_id is None:
        return None
    try:
        uuid_obj = uuid.UUID(raw_session_id, version=4)
        session_uuid = str(uuid_obj)
    except ValueError:
        return None
    session_info = get_couch()["crab_sessions"][session_uuid].copy()
    if session_info["status"] == "ACTIVE":
        if session_info["access_token"] == request.cookies.get("sessionKey"):
            session_info["session_uuid"] = session_uuid
            return session_info
    return None
