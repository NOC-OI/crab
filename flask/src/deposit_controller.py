import uuid
import zipfile
import re
import json
import requests
import uuid
import urllib
import tempfile
import os
from datetime import datetime
import jwt
import io
from PIL import Image
from flask import Blueprint, request, render_template, Response, make_response, send_file, redirect

from utils import get_session_info, get_app_frontend_globals, to_snake_case, get_csrf_secret_key
from db import get_couch, get_s3_client, get_s3_bucket_uri, get_s3_bucket_name, get_couch_base_uri, get_couch_client

deposit_pages = Blueprint("deposit_pages", __name__)
deposit_api = Blueprint("deposit_api", __name__)

def can_view(deposit_uuid):
    session_info = get_session_info()
    couch_client = get_couch_client()
    deposit_data = couch_client.get_document("crab_deposits", deposit_uuid)
    if "public_visibility" in deposit_data:
        if deposit_data["public_visibility"] == True:
            return True
    if not session_info is None:
        if session_info["user_uuid"] in deposit_data["owners"]:
            return True
    #projects = []
    layer_match = couch_client.find_all("crab_layers", {"deposits":{"$in": [deposit_uuid]}}, ["_id", "project"])
    #print(layer_match)
    for layer in layer_match:
        project_data = couch_client.get_document("crab_projects", layer["project"])
        #projects.append(proj)
        if not session_info is None:
            if session_info["user_uuid"] in project_data["collaborators"]:
                return True
        if project_data["public_visibility"]:
            return True
    return False

def can_edit(deposit_uuid):
    session_info = get_session_info()
    couch_client = get_couch_client()
    deposit_data = couch_client.get_document("crab_deposits", deposit_uuid)
    if not session_info is None:
        if session_info["user_uuid"] in deposit_data["owners"]:
            return True
    return False

@deposit_pages.route("/deposits", methods=['GET'])
def deposit_deposit_screen():
    return render_template("deposits.html", global_vars=get_app_frontend_globals(), session_info=get_session_info())

@deposit_pages.route("/deposits/<raw_uuid>", methods=['GET'])
def deposit_detail_screen(raw_uuid):
    try:
        uuid_obj = uuid.UUID(raw_uuid, version=4)


        if not can_view(str(uuid_obj)):
            return Response(json.dumps({
                "error": "readDenied",
                "msg": "User is not allowed to view this resource."
                }), status=401, mimetype='application/json')

        deposit_data = get_couch()["crab_deposits"][str(uuid_obj)]
        #deposit_data_raw = json.dumps(deposit_data["tags"], indent=2)
        return render_template("deposit_info.html", global_vars=get_app_frontend_globals(), session_info=get_session_info(), deposit_data=deposit_data, can_edit=can_edit(str(uuid_obj)))
    except ValueError:
        return Response(json.dumps({
            "error": "badUUID",
            "msg": "Invalid UUID " + raw_uuid
            }), status=400, mimetype='application/json')

@deposit_pages.route("/deposits/<raw_uuid>/delete", methods=['GET'])
def deposit_delete_page(raw_uuid):
    session_info = get_session_info()
    if session_info is None:
        return Response(json.dumps({
            "error": "notLoggedIn",
            "msg": "User is not logged in, or session has expired."
            }), status=403, mimetype='application/json')
    try:
        uuid_obj = uuid.UUID(raw_uuid, version=4)

        if not can_edit(str(uuid_obj)):
            return Response(json.dumps({
                "error": "writeDenied",
                "msg": "User is not allowed to edit this resource."
                }), status=401, mimetype='application/json')

        deposit_data = get_couch()["crab_deposits"][str(uuid_obj)]
        jwt_token_content = {
                "iat": (datetime.utcnow() - datetime(1970, 1, 1)).total_seconds(),
                "sub": session_info["user_uuid"],
                "targ": str(uuid_obj),
                "prp": "csrf"
            }
        csrf_token = jwt.encode(jwt_token_content, get_csrf_secret_key(), algorithm="HS256")
        object_name = "deposit"
        action_uri = "/api/v1/deposits/" + str(uuid_obj) + "/delete"
        return render_template("delete_confirm.html", global_vars=get_app_frontend_globals(), session_info=session_info, object_name=object_name, csrf_token=csrf_token, action_uri=action_uri, redirect_uri="/deposits", hint="This will not delete deposit contents from snapshots. You must delete any snapshots that contain this data seperately. This will break projects that rely on this data. You cannot undo this action.")
    except ValueError:
        return Response(json.dumps({
            "error": "badUUID",
            "msg": "Invalid UUID " + raw_uuid
            }), status=400, mimetype='application/json')

@deposit_api.route("/api/v1/deposits/<raw_uuid>/delete", methods=["POST", "DELETE"])
def api_v1_deposit_delete(raw_uuid):
    session_info = get_session_info()
    if session_info is None:
        return Response(json.dumps({
            "error": "notLoggedIn",
            "msg": "User is not logged in, or session has expired."
            }), status=403, mimetype='application/json')
    try:
        uuid_obj = uuid.UUID(raw_uuid, version=4)
        redirect_uri = request.form.get("redirect", "")



        if not can_edit(str(uuid_obj)):
            return Response(json.dumps({
                "error": "writeDenied",
                "msg": "User is not allowed to edit this resource."
                }), status=401, mimetype='application/json')


        if session_info["auth_type"] == "OPENID":
            # Only do CSRF checking on users authenticated via a browser
            try:
                csrf_token = jwt.decode(request.form.get("csrf_token", ""), get_csrf_secret_key(), algorithms=["HS256"])
                if not (csrf_token["prp"] == "csrf" and csrf_token["targ"] == str(uuid_obj) and csrf_token["sub"] == session_info["user_uuid"]):
                    return Response(json.dumps({
                        "error": "invalidCSRFToken",
                        "msg": "CSRF token invalid for this use"
                        }), status=401, mimetype='application/json')
            except jwt.exceptions.InvalidSignatureError:
                return Response(json.dumps({
                    "error": "badCSRFToken",
                    "msg": "CSRF token tampering detected"
                    }), status=401, mimetype='application/json')

        couch_client = get_couch_client()
        couch_client.delete_document("crab_deposits", str(uuid_obj))

        if len(redirect_uri) > 0:
            return redirect(redirect_uri, code=302)
        else:
            return Response(json.dumps({
                "msg": "objectDeleted"
                }), status=200, mimetype='application/json')

    except ValueError:
        return Response(json.dumps({
            "error": "badUUID",
            "msg": "Invalid UUID " + raw_uuid
            }), status=400, mimetype='application/json')


@deposit_api.route("/api/v1/deposits", methods=["POST", "GET"])
def api_v1_get_deposits():
    raw_selector = json.dumps({})
    mango_selector = json.loads(raw_selector)
    raw_sort = json.dumps([{
            "ingest_timestamp": "desc"
        }])
    mango_sort = json.loads(raw_sort)
    for sortby in mango_sort:
        for key in sortby:
            if not key in mango_selector:
                mango_selector[key] = {"$exists": True}
    page = int(request.form.get("page",request.args.get("page", 0)))
    limit = 12
    mango = {
            "selector": mango_selector,
            "fields": ["public_visibility", "s3_profile", "identifier", "ingest_timestamp", "_id", "owners"],
            "sort": mango_sort,
            "skip": page * limit,
            "limit": limit
        }
    #        "sort": mango_sort
    #get_couch()["crab_deposits"].find(mango)
    ret = requests.post(get_couch_base_uri() + "crab_deposits/" + "_find", json=mango).json()
    return Response(json.dumps(ret), status=200, mimetype='application/json')

@deposit_api.route("/api/v1/deposits/<raw_uuid>", methods=['GET'])
def api_v1_get_deposit(raw_uuid):
    try:
        uuid_obj = uuid.UUID(raw_uuid, version=4)
        if can_view(str(uuid_obj)):
            deposit_data = get_couch()["crab_deposits"][str(uuid_obj)]
            return Response(json.dumps(deposit_data), status=200, mimetype='application/json')
    except ValueError:
        return Response(json.dumps({
            "error": "badUUID",
            "msg": "Invalid UUID " + raw_uuid
            }), status=400, mimetype='application/json')

