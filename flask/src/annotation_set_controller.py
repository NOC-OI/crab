from flask import Blueprint, request, render_template, Response, make_response, send_file, redirect
import uuid
import requests
from datetime import datetime
from multiprocessing import Process
import io
import os
import jwt
import zipfile
import json
from utils import get_session_info, get_app_frontend_globals, to_snake_case, get_crab_external_endpoint, get_csrf_secret_key
from db import get_couch, get_couch_base_uri, get_bucket_object, get_s3_client, get_bucket_name, get_couch_client, advertise_job, get_s3_bucket_name, get_s3_client, get_s3_profile, get_s3_bucket_ext_uri

annotation_set_pages = Blueprint("annotation_set_pages", __name__)
annotation_set_api = Blueprint("annotation_set_api", __name__)

csrf_secret_key = get_csrf_secret_key()


def can_view(annotation_set_uuid):
    #couch_client = get_couch_client()
    #session_info = get_session_info()
    #annotation_set_data = couch_client.get_document("crab_annotation_sets", annotation_set_uuid)
    #if not session_info is None:
    #    if session_info["user_uuid"] in project_data["collaborators"]:
    #        return True
    #override = False
    #if "public_visibility" in snapshot_data:
    #    override = snapshot_data["public_visibility"]
    #return project_data["public_visibility"] or override
    return True

def can_edit(annotation_set_uuid):
    return True


@annotation_set_api.route("/api/v1/annotations/<annotation_set_uuid>", methods=['GET'])
def api_v1_get_annotation_set(annotation_set_uuid):
    try:
        uuid_obj = uuid.UUID(annotation_set_uuid, version=4)

        if not can_view(str(uuid_obj)):
            return Response(json.dumps({
                "error": "readDenied",
                "msg": "User is not allowed to view this resource."
                }), status=401, mimetype='application/json')

        annotation_data = get_couch()["crab_annotation_sets"][str(uuid_obj)]
        return Response(json.dumps(annotation_data), status=200, mimetype='application/json')
    except ValueError:
        return Response(json.dumps({
            "error": "badUUID",
            "msg": "Invalid UUID " + annotation_set_uuid
            }), status=400, mimetype='application/json')
