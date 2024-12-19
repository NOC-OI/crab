import uuid
import zipfile
import re
import json
import requests
import uuid
import tempfile
import os
import io
from PIL import Image
from flask import Blueprint, request, render_template, Response, make_response, send_file

from utils import get_session_info, get_app_frontend_globals, to_snake_case
from db import get_couch, get_bucket, get_bucket_uri, get_couch_base_uri, get_bucket_object

browse_pages = Blueprint("browse_pages", __name__)
browse_api = Blueprint("browse_api", __name__)

@browse_pages.route("/runs", methods=['GET'])
def run_browse_screen():
    return render_template("runs.html", global_vars=get_app_frontend_globals(), session_info=get_session_info())

@browse_pages.route("/projects", methods=['GET'])
def project_browse_screen():
    return render_template("projects.html", global_vars=get_app_frontend_globals(), session_info=get_session_info())


@browse_pages.route("/runs/<raw_uuid>", methods=['GET'])
def run_detail_screen(raw_uuid):
    try:
        uuid_obj = uuid.UUID(raw_uuid, version=4)
        run_data = get_couch()["crab_runs"][str(uuid_obj)]
        return render_template("run_info.html", global_vars=get_app_frontend_globals(), session_info=get_session_info(), run_data=run_data)
    except ValueError:
        return Response(json.dumps({
            "error": "badUUID",
            "msg": "Invalid UUID " + raw_uuid
            }), status=400, mimetype='application/json')

@browse_api.route("/api/v1/runs", methods=["POST", "GET"])
def api_v1_get_runs():
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
            "fields": ["creator", "ingest_timestamp", "_id", "samples.0", "identifier"],
            "sort": mango_sort,
            "skip": page * limit,
            "limit": limit
        }
    #        "sort": mango_sort

    #get_couch()["crab_runs"].find(mango)
    ret = requests.post(get_couch_base_uri() + "crab_runs/" + "_find", json=mango).json()
    #print(json.dumps(ret, indent=4))

    return Response(json.dumps(ret), status=200, mimetype='application/json')


@browse_api.route("/api/v1/projects", methods=["POST", "GET"])
def api_v1_get_projects():
    raw_selector = json.dumps({})
    mango_selector = json.loads(raw_selector)
    raw_sort = json.dumps([{
            "creation_timestamp": "desc"
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
            "fields": ["collaborators", "creation_timestamp", "_id", "identifier"],

            "skip": page * limit,
            "limit": limit
        }
    #            "sort": mango_sort,

    ret = requests.post(get_couch_base_uri() + "crab_projects/" + "_find", json=mango).json()
    print(ret)
    return Response(json.dumps(ret), status=200, mimetype='application/json')

#@browse_api.route("/api/v1/get_run/<raw_uuid>", methods=['GET'])
@browse_api.route("/api/v1/runs/<raw_uuid>", methods=['GET'])
def api_v1_get_run(raw_uuid):
    try:
        uuid_obj = uuid.UUID(raw_uuid, version=4)
        run_data = get_couch()["crab_runs"][str(uuid_obj)]
        return Response(json.dumps(run_data), status=200, mimetype='application/json')
    except ValueError:
        return Response(json.dumps({
            "error": "badUUID",
            "msg": "Invalid UUID " + raw_uuid
            }), status=400, mimetype='application/json')

#@browse_api.route("/api/v1/get_user/<raw_uuid>", methods=['GET'])
@browse_api.route("/api/v1/users/<raw_uuid>", methods=['GET'])
def api_v1_get_user(raw_uuid):
    try:
        uuid_obj = uuid.UUID(raw_uuid, version=4)
        user_data = get_couch()["crab_users"][str(uuid_obj)]
        return Response(json.dumps(user_data), status=200, mimetype='application/json')
    except ValueError:
        return Response(json.dumps({
            "error": "badUUID",
            "msg": "Invalid UUID " + raw_uuid
            }), status=400, mimetype='application/json')

#@browse_api.route("/api/v1/get_sample_metadata/<raw_uuid>", methods=['GET'])
@browse_api.route("/api/v1/samples/<raw_uuid>/metadata", methods=['GET'])
def api_v1_get_sample_metadata(raw_uuid):
    try:
        uuid_obj = uuid.UUID(raw_uuid, version=4)
        sample_metadata = get_couch()["crab_samples"][str(uuid_obj)]
        return Response(json.dumps(sample_metadata), status=200, mimetype='application/json')
    except ValueError:
        return Response(json.dumps({
            "error": "badUUID",
            "msg": "Invalid UUID " + raw_uuid
            }), status=400, mimetype='application/json')

#@browse_api.route("/api/v1/get_sample/<raw_uuid>", methods=['GET'])
@browse_api.route("/api/v1/samples/<raw_uuid>", methods=['GET'])
def api_v1_get_sample(raw_uuid):
    try:
        uuid_obj = uuid.UUID(raw_uuid, version=4)
        sample_metadata = get_couch()["crab_samples"][str(uuid_obj)]
        temp_file = get_bucket_object(path=sample_metadata["path"])
        #return send_file(fh, download_name=os.path.basename(sample_metadata["path"]))
        return Response(
            temp_file['Body'].read(),
            mimetype=sample_metadata["type"]["format"],
            headers={"Content-Disposition": "attachment;filename=" + os.path.basename(sample_metadata["path"])}
        )
    except ValueError:
        return Response(json.dumps({
            "error": "badUUID",
            "msg": "Invalid UUID " + raw_uuid
            }), status=400, mimetype='application/json')

#@browse_api.route("/api/v1/get_sample_thumbnail/<raw_uuid>", methods=['GET'])
@browse_api.route("/api/v1/samples/<raw_uuid>/thumbnail", methods=['GET'])
def api_v1_get_sample_thumbnail(raw_uuid):
    #try:
        uuid_obj = uuid.UUID(raw_uuid, version=4)
        sample_metadata = get_couch()["crab_samples"][str(uuid_obj)]
        in_temp_file = get_bucket_object(path=sample_metadata["path"])
        #return send_file(fh, download_name=os.path.basename(sample_metadata["path"]))
        out_temp_file = io.BytesIO()
        #print(in_temp_file['Body'].read())
        im = Image.open(io.BytesIO(in_temp_file['Body'].read())) # Open with PIL to convert to jpeg
        im.save(out_temp_file, "JPEG", quality=50) # Only intended for a thumbnail - we can skimp on quality
        out_bytearray = out_temp_file.getvalue()
        return Response(
            out_bytearray,
            mimetype="image/jpeg",
            headers={"Content-Disposition": "inline;filename=" + os.path.splitext(os.path.basename(sample_metadata["path"]))[0] + ".jpg"}
        )
        # switch to inline
    #except ValueError:
        #return Response(json.dumps({
            #"error": "badUUID",
            #"msg": "Invalid UUID " + raw_uuid
            #}), status=400, mimetype='application/json')
