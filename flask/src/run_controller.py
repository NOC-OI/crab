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

run_pages = Blueprint("run_pages", __name__)
run_api = Blueprint("run_api", __name__)

def can_view(run_uuid):
    session_info = get_session_info()
    couch_client = get_couch_client()
    run_data = couch_client.get_document("crab_runs", run_uuid)
    if "public_visibility" in run_data:
        if run_data["public_visibility"] == True:
            return True
    if not session_info is None:
        if session_info["user_uuid"] == run_data["creator"]["uuid"]:
            return True
    #projects = []
    collection_match = couch_client.find_all("crab_collections", {"runs":{"$in": [run_uuid]}}, ["_id", "project"])
    #print(collection_match)
    for collection in collection_match:
        project_data = couch_client.get_document("crab_projects", collection["project"])
        #projects.append(proj)
        if not session_info is None:
            if session_info["user_uuid"] in project_data["collaborators"]:
                return True
        if project_data["public_visibility"]:
            return True
    return False

def can_edit(run_uuid):
    session_info = get_session_info()
    couch_client = get_couch_client()
    run_data = couch_client.get_document("crab_runs", run_uuid)
    if not session_info is None:
        if session_info["user_uuid"] == run_data["creator"]["uuid"]:
            return True
    return False

@run_pages.route("/runs", methods=['GET'])
def run_run_screen():
    return render_template("runs.html", global_vars=get_app_frontend_globals(), session_info=get_session_info())

@run_pages.route("/runs/<raw_uuid>", methods=['GET'])
def run_detail_screen(raw_uuid):
    try:
        uuid_obj = uuid.UUID(raw_uuid, version=4)


        if not can_view(str(uuid_obj)):
            return Response(json.dumps({
                "error": "readDenied",
                "msg": "User is not allowed to view this resource."
                }), status=401, mimetype='application/json')

        run_data = get_couch()["crab_runs"][str(uuid_obj)]
        run_data_raw = json.dumps(run_data["tags"], indent=2)
        run_data["observation_count"] = len(run_data["observations"])
        run_data["observations"] = run_data["observations"][:10]
        return render_template("run_info.html", global_vars=get_app_frontend_globals(), session_info=get_session_info(), run_data=run_data, run_data_raw=run_data_raw, can_edit=can_edit(str(uuid_obj)))
    except ValueError:
        return Response(json.dumps({
            "error": "badUUID",
            "msg": "Invalid UUID " + raw_uuid
            }), status=400, mimetype='application/json')

@run_pages.route("/runs/<raw_uuid>/delete", methods=['GET'])
def run_delete_page(raw_uuid):
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

        run_data = get_couch()["crab_runs"][str(uuid_obj)]
        jwt_token_content = {
                "iat": (datetime.utcnow() - datetime(1970, 1, 1)).total_seconds(),
                "sub": session_info["user_uuid"],
                "targ": str(uuid_obj),
                "prp": "csrf"
            }
        csrf_token = jwt.encode(jwt_token_content, get_csrf_secret_key(), algorithm="HS256")
        object_name = "run"
        action_uri = "/api/v1/runs/" + str(uuid_obj) + "/delete"
        return render_template("delete_confirm.html", global_vars=get_app_frontend_globals(), session_info=session_info, object_name=object_name, csrf_token=csrf_token, action_uri=action_uri, redirect_uri="/runs", hint="This will not delete run contents from snapshots. You must delete any snapshots that contain this data seperately. This will break projects that rely on this data. You cannot undo this action.")
    except ValueError:
        return Response(json.dumps({
            "error": "badUUID",
            "msg": "Invalid UUID " + raw_uuid
            }), status=400, mimetype='application/json')

@run_api.route("/api/v1/runs/<raw_uuid>/delete", methods=["POST", "DELETE"])
def api_v1_run_delete(raw_uuid):
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
            "fields": ["creator", "ingest_timestamp", "_id", "observations.0", "identifier"],
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
        if can_view(str(uuid_obj)):
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
        if can_view(str(uuid_obj)):
            run_data = get_couch()["crab_runs"][str(uuid_obj)]
            filename = str(uuid_obj)
            if "identifier" in run_data:
                filename = urllib.parse.quote_plus(run_data["identifier"])
            zip_fp = io.BytesIO()
            zip_fo = zipfile.ZipFile(zip_fp, "w", compression=zipfile.ZIP_DEFLATED)
            zip_fo.writestr("run_metadata.json", json.dumps(run_data, indent=4))
            zip_fo.mkdir("observations")
            for observation in run_data["observations"]:
                observation_metadata = get_couch()["crab_observations"][str(uuid.UUID(observation, version=4))] # This parsing is to throw an error on malformed input - it should not be removed!
                zip_fo.writestr("observations/" + observation + ".json", json.dumps(observation_metadata, indent=4))

                #observation_bucket_obj = get_bucket_object(path=observation_metadata["path"])
                #observation_temp_file = io.BytesIO(observation_bucket_obj['Body'].read())



                with io.BytesIO() as img_fp:
                    get_s3_client(observation_metadata["s3_profile"]).download_fileobj(get_s3_bucket_name(observation_metadata["s3_profile"]), observation_metadata["path"], img_fp)
                    img_fp.seek(0)
                    zip_fo.writestr("observations/" + observation + ".tiff", img_fp.read())

                #zip_fo.writestr("observations/" + observation + ".tiff", observation_temp_file.getvalue())

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

#@run_api.route("/api/v1/get_observation_metadata/<raw_uuid>", methods=['GET'])
@run_api.route("/api/v1/observations/<raw_uuid>/metadata", methods=['GET'])
def api_v1_get_observation_metadata(raw_uuid):
    try:
        uuid_obj = uuid.UUID(raw_uuid, version=4)
        observation_metadata = get_couch()["crab_observations"][str(uuid_obj)]
        return Response(json.dumps(observation_metadata), status=200, mimetype='application/json')
    except ValueError:
        return Response(json.dumps({
            "error": "badUUID",
            "msg": "Invalid UUID " + raw_uuid
            }), status=400, mimetype='application/json')

#@run_api.route("/api/v1/get_observation/<raw_uuid>", methods=['GET'])
@run_api.route("/api/v1/observations/<raw_uuid>", methods=['GET'])
@run_api.route("/api/v1/observations/<raw_uuid>.tiff", methods=['GET'])
@run_api.route("/api/v1/observations/<raw_uuid>.tif", methods=['GET'])
def api_v1_get_observation(raw_uuid):
    try:
        uuid_obj = uuid.UUID(raw_uuid, version=4)
        observation_metadata = get_couch()["crab_observations"][str(uuid_obj)]

        #temp_file = get_bucket_object(path=observation_metadata["path"])
        #return send_file(fh, download_name=os.path.basename(observation_metadata["path"]))
                    #temp_file['Body'].read(),
        with io.BytesIO() as img_fp:
            get_s3_client(observation_metadata["s3_profile"]).download_fileobj(get_s3_bucket_name(observation_metadata["s3_profile"]), observation_metadata["path"], img_fp)
            img_fp.seek(0)
            return Response(
                img_fp.read(),
                mimetype=observation_metadata["type"]["format"],
                headers={"Content-Disposition": "attachment;filename=" + os.path.basename(observation_metadata["path"])}
            )
    except ValueError:
        return Response(json.dumps({
            "error": "badUUID",
            "msg": "Invalid UUID " + raw_uuid
            }), status=400, mimetype='application/json')

@run_api.route("/api/v1/observations/<raw_uuid>.jpeg", methods=['GET'])
@run_api.route("/api/v1/observations/<raw_uuid>.jpg", methods=['GET'])
def api_v1_get_observation_jpeg(raw_uuid):
    #try:
        uuid_obj = uuid.UUID(raw_uuid, version=4)
        observation_metadata = get_couch()["crab_observations"][str(uuid_obj)]

        #in_temp_file = get_bucket_object(path=observation_metadata["path"])
        with io.BytesIO() as in_temp_file:
            get_s3_client(observation_metadata["s3_profile"]).download_fileobj(get_s3_bucket_name(observation_metadata["s3_profile"]), observation_metadata["path"], in_temp_file)
            in_temp_file.seek(0)

            #return send_file(fh, download_name=os.path.basename(observation_metadata["path"]))
            out_temp_file = io.BytesIO()
            #print(in_temp_file['Body'].read())
            im = Image.open(in_temp_file) # Open with PIL to convert to jpeg
            im.save(out_temp_file, "JPEG", quality=90)
            out_bytearray = out_temp_file.getvalue()
            return Response(
                out_bytearray,
                mimetype="image/jpeg",
                headers={"Content-Disposition": "inline;filename=" + os.path.splitext(os.path.basename(observation_metadata["path"]))[0] + ".jpg"}
            )

@run_api.route("/api/v1/observations/<raw_uuid>.png", methods=['GET'])
def api_v1_get_observation_png(raw_uuid):
    #try:
        uuid_obj = uuid.UUID(raw_uuid, version=4)
        observation_metadata = get_couch()["crab_observations"][str(uuid_obj)]
        #in_temp_file = get_bucket_object(path=observation_metadata["path"])
        #return send_file(fh, download_name=os.path.basename(observation_metadata["path"]))

        with io.BytesIO() as in_temp_file:
            get_s3_client(observation_metadata["s3_profile"]).download_fileobj(get_s3_bucket_name(observation_metadata["s3_profile"]), observation_metadata["path"], in_temp_file)
            in_temp_file.seek(0)

            out_temp_file = io.BytesIO()
            #print(in_temp_file['Body'].read())
            im = Image.open(in_temp_file) # Open with PIL to convert to jpeg
            im.save(out_temp_file, "PNG")
            out_bytearray = out_temp_file.getvalue()
            return Response(
                out_bytearray,
                mimetype="image/png",
                headers={"Content-Disposition": "inline;filename=" + os.path.splitext(os.path.basename(observation_metadata["path"]))[0] + ".png"}
            )

#@run_api.route("/api/v1/get_observation_thumbnail/<raw_uuid>", methods=['GET'])
@run_api.route("/api/v1/observations/<raw_uuid>/thumbnail", methods=['GET'])
def api_v1_get_observation_thumbnail(raw_uuid):
    #try:
        uuid_obj = uuid.UUID(raw_uuid, version=4)
        observation_metadata = get_couch()["crab_observations"][str(uuid_obj)]
        #in_temp_file = get_bucket_object(path=observation_metadata["path"])
        #return send_file(fh, download_name=os.path.basename(observation_metadata["path"]))

        with io.BytesIO() as in_temp_file:
            get_s3_client(observation_metadata["s3_profile"]).download_fileobj(get_s3_bucket_name(observation_metadata["s3_profile"]), observation_metadata["path"], in_temp_file)
            in_temp_file.seek(0)

            out_temp_file = io.BytesIO()
            #print(in_temp_file['Body'].read())
            im = Image.open(in_temp_file) # Open with PIL to convert to jpeg
            im.save(out_temp_file, "JPEG", quality=50) # Only intended for a thumbnail - we can skimp on quality
            out_bytearray = out_temp_file.getvalue()
            return Response(
                out_bytearray,
                mimetype="image/jpeg",
                headers={"Content-Disposition": "inline;filename=" + os.path.splitext(os.path.basename(observation_metadata["path"]))[0] + ".jpg"}
            )
            # switch to inline
        #except ValueError:
            #return Response(json.dumps({
                #"error": "badUUID",
                #"msg": "Invalid UUID " + raw_uuid
                #}), status=400, mimetype='application/json')
