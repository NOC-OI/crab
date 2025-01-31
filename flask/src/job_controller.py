from flask import Blueprint, request, render_template, Response, make_response, send_file, redirect
import uuid
import requests
import datetime
import json
from utils import get_session_info, get_app_frontend_globals, to_snake_case
from db import get_couch, get_bucket, get_bucket_uri, get_couch_base_uri, get_bucket_object
import markdown
from pygments.formatters import HtmlFormatter


job_pages = Blueprint("job_pages", __name__)
job_api = Blueprint("job_api", __name__)

@job_api.route("/api/v1/jobs/<raw_uuid>", methods=['GET'])
def api_v1_get_job(raw_uuid):
    try:
        uuid_obj = uuid.UUID(raw_uuid, version=4)
        job_data = get_couch()["crab_jobs"][str(uuid_obj)]
        return Response(json.dumps(job_data), status=200, mimetype='application/json')
    except ValueError:
        return Response(json.dumps({
            "error": "badUUID",
            "msg": "Invalid UUID " + raw_uuid
            }), status=400, mimetype='application/json')

@job_pages.route("/jobs/<raw_uuid>", methods=['GET'])
def get_job_status(raw_uuid):
    try:
        uuid_obj = uuid.UUID(raw_uuid, version=4)
        return render_template("job_view.html", global_vars=get_app_frontend_globals(), session_info=get_session_info(), job_id=str(uuid_obj))
    except ValueError:
        return Response(json.dumps({
            "error": "badUUID",
            "msg": "Invalid UUID " + raw_uuid
            }), status=400, mimetype='application/json')
