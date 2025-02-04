import uuid
import zipfile
import re
import json
from datetime import datetime
import os
from PIL import Image
from flask import Blueprint, request, render_template, Response, make_response, redirect

from utils import get_session_info, get_app_frontend_globals, to_snake_case
from db import get_couch, get_bucket, get_bucket_uri, get_couch_client, advertise_job

temp_loc = "temp"

ingest_pages = Blueprint("ingest_pages", __name__)

#@ingest_pages.route('/applyMapping', methods=['POST']) # Legacy legacy endpoint
#@ingest_pages.route('/api/v1/apply_mapping', methods=['POST']) # Legacy endpoint
@ingest_pages.route('/api/v1/runs/<raw_uuid>/apply_upload_profile', methods=['POST'])
def unpack_upload(raw_uuid):
    session_info = get_session_info()
    if session_info is None:
        return Response(json.dumps({
            "error": "notLoggedIn",
            "msg": "User is not logged in, or session has expired."
            }), status=403, mimetype='application/json')
    archive = None
    run_uuid = None
    try:
        uuid_obj = uuid.UUID(raw_uuid, version=4)
        archive = temp_loc + "/" + str(uuid_obj) + ".zip"
        run_uuid = str(uuid_obj)
    except ValueError:
        return Response(json.dumps({
            "error": "badUUID",
            "msg": "Invalid UUID " + raw_uuid
            }), status=400, mimetype='application/json')
    get_bucket().upload_file(archive, "raw_uploads/" + run_uuid + ".zip")
    profile = request.form["sensor"]
    ret = {"uuid": run_uuid, "profile": profile}
    #workdir = temp_loc + "/" + run_uuid + "-unpacked"

    metadata_template = {
        "creator": {
            "uuid": session_info["user_uuid"],
            "email": session_info["email"]
        }
    }
    #print(request.form)
    if "identifier" in request.form:
        metadata_template["identifier"] = request.form["identifier"]


    job_uuid = uuid.uuid4()
    job_args = {
            "input_md": metadata_template
        }

    if profile == "ifcb":
        #print("IFCB profile!")
        job_args["profile"] = "IFCB"
        #ret["unpacker_output"] = ifcb_unpack(run_uuid, workdir, namelist, metadata_template)
    elif profile == "lisst-holo":
        #print("LISST-Holo profile!")
        job_args["profile"] = "LISST_HOLO"
        #ret["unpacker_output"] = lisst_holo_unpack(run_uuid, workdir, namelist, metadata_template)
    elif profile == "raw-image":
        #print("Raw-Image profile!")
        job_args["profile"] = "RAW_IMAGE"
        #ret["unpacker_output"] = raw_image_unpack(run_uuid, workdir, namelist, metadata_template)
    else:
        return Response(json.dumps({
            "error": "badProfile",
            "msg": "Invalid Profile " + profile
            }), status=400, mimetype='application/json')

    job_md = {
            "type": "RUN_APPLY_UPLOAD_PROFILE",
            "target_id": run_uuid,
            "status": "PENDING",
            "progress": 0.0,
            "job_args": job_args
        }
    get_couch_client().put_document("crab_jobs", str(job_uuid), job_md)
    ret["job_id"] = str(job_uuid)
    advertise_job(str(job_uuid))

    return Response(json.dumps(ret), status=200, mimetype='application/json')


# @ingest_pages.route("/upload", methods=['GET'])
@ingest_pages.route("/runs/upload", methods=['GET'])
def upload_screen():
    session_info = get_session_info()
    if session_info is None:
        return redirect("/login", code=302)
    return render_template("run_upload.html", global_vars=get_app_frontend_globals(), session_info=session_info)

# @ingest_pages.route('/upload', methods=['POST'])
@ingest_pages.route('/runs/upload', methods=['POST'])
def upload_file():
    uploaded_file = request.files['file']
    run_uuid = str(uuid.uuid4())
    if uploaded_file.filename != '':
        uploaded_file.save(temp_loc + "/" + run_uuid + ".zip")
    zipf = zipfile.ZipFile(temp_loc + "/" + run_uuid + ".zip")
    timestamp = None
    namelist = zipf.namelist()
    if len(namelist) > 0:
        dt = zipf.getinfo(namelist[0]).date_time
        timestamp = "{:04d}-{:02d}-{:02d}T{:02d}:{:02d}:{:02d}Z".format(dt[0],dt[1],dt[2],dt[3],dt[4],dt[5])
    folder_structure = {}
    for nlpath in namelist:
        cd = folder_structure
        pels = re.split("/|\\\\", nlpath)
        for pel in pels[:-1]:
            try:
                cd[pel]
            except KeyError:
                cd[pel] = {}
            cd = cd[pel]
        if len(pels[-1]) > 0:
            cd[pels[-1]] = "file"

    ret = {
        "run_uuid": run_uuid,
        "directory_structure": folder_structure,
        "file_list": namelist,
        "timestamp": timestamp
    }
    return ret
