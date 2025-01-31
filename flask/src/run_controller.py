import uuid
import zipfile
import re
import json
import requests
import uuid
import urllib
import tempfile
import os
import io
from PIL import Image
from flask import Blueprint, request, render_template, Response, make_response, send_file

from utils import get_session_info, get_app_frontend_globals, to_snake_case
from db import get_couch, get_bucket, get_bucket_uri, get_couch_base_uri, get_bucket_object

run_pages = Blueprint("run_pages", __name__)
run_api = Blueprint("run_api", __name__)

@run_pages.route("/runs", methods=['GET'])
def run_run_screen():
    return render_template("runs.html", global_vars=get_app_frontend_globals(), session_info=get_session_info())

@run_pages.route("/runs/<raw_uuid>", methods=['GET'])
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

@run_api.route("/api/v1/runs", methods=["POST", "GET"])
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

#@run_api.route("/api/v1/get_run/<raw_uuid>", methods=['GET'])
@run_api.route("/api/v1/runs/<raw_uuid>", methods=['GET'])
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

@run_api.route("/api/v1/runs/<raw_uuid>/as_zip", methods=['GET'])
def api_v1_run_download(raw_uuid):
    try:
        uuid_obj = uuid.UUID(raw_uuid, version=4)
        run_data = get_couch()["crab_runs"][str(uuid_obj)]
        filename = str(uuid_obj)
        if "identifier" in run_data:
            filename = urllib.parse.quote_plus(run_data["identifier"])
        zip_fp = io.BytesIO()
        zip_fo = zipfile.ZipFile(zip_fp, "w", compression=zipfile.ZIP_DEFLATED)
        zip_fo.writestr("run_metadata.json", json.dumps(run_data, indent=4))
        zip_fo.mkdir("samples")
        for sample in run_data["samples"]:
            sample_metadata = get_couch()["crab_samples"][str(uuid.UUID(sample, version=4))] # This parsing is to throw an error on malformed input - it should not be removed!
            zip_fo.writestr("samples/" + sample + ".json", json.dumps(sample_metadata, indent=4))

            sample_bucket_obj = get_bucket_object(path=sample_metadata["path"])
            sample_temp_file = io.BytesIO(sample_bucket_obj['Body'].read())
            zip_fo.writestr("samples/" + sample + ".tiff", sample_temp_file.getvalue())

        zip_fo.close()
        out_bytearray = zip_fp.getvalue()
        return Response(
            out_bytearray,
            mimetype="application/zip",
            headers={"Content-Disposition": "attachment;filename=" + filename + ".zip"}
            )
    except ValueError:
        return Response(json.dumps({
            "error": "badUUID",
            "msg": "Invalid UUID " + raw_uuid
            }), status=400, mimetype='application/json')

#@run_api.route("/api/v1/get_user/<raw_uuid>", methods=['GET'])
@run_api.route("/api/v1/users/<raw_uuid>", methods=['GET'])
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

#@run_api.route("/api/v1/get_sample_metadata/<raw_uuid>", methods=['GET'])
@run_api.route("/api/v1/samples/<raw_uuid>/metadata", methods=['GET'])
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

#@run_api.route("/api/v1/get_sample/<raw_uuid>", methods=['GET'])
@run_api.route("/api/v1/samples/<raw_uuid>", methods=['GET'])
@run_api.route("/api/v1/samples/<raw_uuid>.tiff", methods=['GET'])
@run_api.route("/api/v1/samples/<raw_uuid>.tif", methods=['GET'])
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

@run_api.route("/api/v1/samples/<raw_uuid>.jpeg", methods=['GET'])
@run_api.route("/api/v1/samples/<raw_uuid>.jpg", methods=['GET'])
def api_v1_get_sample_jpeg(raw_uuid):
    #try:
        uuid_obj = uuid.UUID(raw_uuid, version=4)
        sample_metadata = get_couch()["crab_samples"][str(uuid_obj)]
        in_temp_file = get_bucket_object(path=sample_metadata["path"])
        #return send_file(fh, download_name=os.path.basename(sample_metadata["path"]))
        out_temp_file = io.BytesIO()
        #print(in_temp_file['Body'].read())
        im = Image.open(io.BytesIO(in_temp_file['Body'].read())) # Open with PIL to convert to jpeg
        im.save(out_temp_file, "JPEG", quality=90)
        out_bytearray = out_temp_file.getvalue()
        return Response(
            out_bytearray,
            mimetype="image/jpeg",
            headers={"Content-Disposition": "inline;filename=" + os.path.splitext(os.path.basename(sample_metadata["path"]))[0] + ".jpg"}
        )

@run_api.route("/api/v1/samples/<raw_uuid>.png", methods=['GET'])
def api_v1_get_sample_png(raw_uuid):
    #try:
        uuid_obj = uuid.UUID(raw_uuid, version=4)
        sample_metadata = get_couch()["crab_samples"][str(uuid_obj)]
        in_temp_file = get_bucket_object(path=sample_metadata["path"])
        #return send_file(fh, download_name=os.path.basename(sample_metadata["path"]))
        out_temp_file = io.BytesIO()
        #print(in_temp_file['Body'].read())
        im = Image.open(io.BytesIO(in_temp_file['Body'].read())) # Open with PIL to convert to jpeg
        im.save(out_temp_file, "PNG")
        out_bytearray = out_temp_file.getvalue()
        return Response(
            out_bytearray,
            mimetype="image/png",
            headers={"Content-Disposition": "inline;filename=" + os.path.splitext(os.path.basename(sample_metadata["path"]))[0] + ".png"}
        )

#@run_api.route("/api/v1/get_sample_thumbnail/<raw_uuid>", methods=['GET'])
@run_api.route("/api/v1/samples/<raw_uuid>/thumbnail", methods=['GET'])
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
