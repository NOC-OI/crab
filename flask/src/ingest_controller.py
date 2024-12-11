import uuid
import zipfile
import re
import json
import os
import microtiff.ifcb
from flask import Blueprint, request, render_template, Response, make_response

from utils import get_session_info, get_app_frontend_globals, to_snake_case
from db import get_couch, get_bucket, get_bucket_uri

temp_loc = "temp"

ingest_pages = Blueprint("ingest_pages", __name__)

@ingest_pages.route('/applyMapping', methods=['POST'])
def unpack_upload():
    archive = None
    run_uuid = None
    try:
        uuid_obj = uuid.UUID(request.form["run_uuid"], version=4)
        archive = temp_loc + "/" + str(uuid_obj) + ".zip"
        run_uuid = str(uuid_obj)
    except ValueError:
        return Response(json.dumps({
            "error": "badUUID",
            "msg": "Invalid UUID " + request.form["run_uuid"]
            }), status=400, mimetype='application/json')
    get_bucket().upload_file(archive, "raw_uploads/" + run_uuid + ".zip")
    profile = request.form["sensor"]
    ret = {"uuid": run_uuid, "profile": profile}
    workdir = temp_loc + "/" + run_uuid + "-unpacked"
    with zipfile.ZipFile(archive) as zipf:
        zipf.extractall(workdir)
    if profile == "ifcb":
        print("IFCB profile!")
        #microtiff.
        targets = []
        for in_file in os.listdir(workdir):
            in_file_s = os.path.splitext(in_file)
            if in_file_s[1] == ".adc" or in_file_s[1] == ".hdr" or in_file_s[1] == ".roi":
                targets.append(in_file_s[0])
        targets = list(set(targets))
        #print(targets)
        run_metadata = None
        group_metadata = {}
        for target in targets:
            with open(workdir + "/" + target + ".hdr") as f:
                header_lines = f.readlines()
                extracted_metadata = microtiff.ifcb.header_file_to_dict(header_lines)
                filtered_metadata = {}
                for key in extracted_metadata:
                    filtered_metadata[to_snake_case(key)] = extracted_metadata[key]
                group_metadata[target] = filtered_metadata
                if run_metadata is None:
                    run_metadata = group_metadata[target].copy()
                for gmk in group_metadata[target]:
                    if not run_metadata[gmk] == group_metadata[target][gmk]:
                        run_metadata[gmk] = []
            microtiff.ifcb.extract_ifcb_images(workdir + "/" + target)

        for group in group_metadata:
            for gmk in group_metadata[group]:
                #print(gmk)
                if type(run_metadata[gmk]) is list:
                    #print(group_metadata[group][gmk])
                    run_metadata[gmk].append(group_metadata[group][gmk])
                else:
                    group_metadata[group][gmk] = None
            group_metadata[group] = {k: v for k, v in group_metadata[group].items() if v is not None}
        run_metadata = {k: v for k, v in run_metadata.items() if v is not None}

        ret["run_metadata"] = run_metadata

        run_dblist = get_couch()["crab_runs"]
        sample_dblist = get_couch()["crab_samples"]
        samples = []

        for in_file in os.listdir(workdir):
            in_file_s = os.path.splitext(in_file)
            if in_file_s[1] == ".tiff":
                base_group = in_file_s[0].split("_TN")[0]
                ofn = "runs/" + run_uuid + "/" + in_file_s[0] + ".tiff"
                get_bucket().upload_file(workdir + "/" + in_file, ofn)
                sample_uuid = str(uuid.uuid4())
                sample_metadata = {
                    "path": ofn,
                    "host": get_bucket_uri(),
                    "type": {
                            "dimensions": 2,
                            "format": "TIFF",
                            "channels": [
                                    {
                                        "type": "L",
                                        "bit_depth": 8
                                    }
                                ]
                        },
                    "origin_tags": group_metadata[base_group].copy()
                }
                sample_dblist[sample_uuid] = sample_metadata
                samples.append(sample_uuid)


        run_dblist[run_uuid] = {
            "origin_tags": run_metadata,
            "samples": samples
        }

    else:
        return Response(json.dumps({
            "error": "badProfile",
            "msg": "Invalid Profile " + profile
            }), status=400, mimetype='application/json')

    return Response(json.dumps(ret), status=200, mimetype='application/json')


@ingest_pages.route("/upload", methods=['GET'])
def upload_screen():
    session_info = get_session_info()
    if session_info is None:
        return redirect("/login", code=302)
    return render_template("upload.html", global_vars=get_app_frontend_globals(), session_info=session_info)

@ingest_pages.route('/upload', methods=['POST'])
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
