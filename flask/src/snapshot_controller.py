from flask import Blueprint, request, render_template, Response, make_response, send_file, redirect
import uuid
import requests
import datetime
from multiprocessing import Process
import io
import os
import zipfile
import json
from utils import get_session_info, get_app_frontend_globals, to_snake_case
from db import get_couch, get_bucket, get_bucket_uri, get_couch_base_uri, get_bucket_object, get_s3_client, get_bucket_name

snapshot_pages = Blueprint("snapshot_pages", __name__)
snapshot_api = Blueprint("snapshot_api", __name__)

@snapshot_pages.route("/snapshots/<raw_uuid>", methods=['GET'])
def snapshot_info_page(raw_uuid):
    try:
        uuid_obj = uuid.UUID(raw_uuid, version=4)
        snapshot_data = get_couch()["crab_snapshots"][str(uuid_obj)]
        return render_template("snapshot_info.html", global_vars=get_app_frontend_globals(), session_info=get_session_info(), snapshot_data=snapshot_data)
    except ValueError:
        return Response(json.dumps({
            "error": "badUUID",
            "msg": "Invalid UUID " + raw_uuid
            }), status=400, mimetype='application/json')

@snapshot_api.route("/api/v1/snapshots/<raw_uuid>/packages/<ptype>", methods=['GET'])
def api_v1_snapshot_download_package(raw_uuid, ptype):
    try:
        uuid_obj = uuid.UUID(raw_uuid, version=4)
        snapshot_data = get_couch()["crab_snapshots"][str(uuid_obj)]
        s3path = snapshot_data["packages"][ptype]["path"]
        temp_file = get_bucket_object(path=s3path)
        return Response(
            temp_file['Body'].read(),
            mimetype="application/zip",
            headers={"Content-Disposition": "attachment;filename=" + os.path.basename(s3path)}
            )
    except ValueError:
        return Response(json.dumps({
            "error": "badUUID",
            "msg": "Invalid UUID " + raw_uuid
            }), status=400, mimetype='application/json')

@snapshot_api.route("/api/v1/snapshots/<raw_uuid>", methods=['GET'])
def api_v1_get_snapshot(raw_uuid):
    try:
        uuid_obj = uuid.UUID(raw_uuid, version=4)
        snapshot_data = get_couch()["crab_snapshots"][str(uuid_obj)]
        return Response(json.dumps(snapshot_data), status=200, mimetype='application/json')
    except ValueError:
        return Response(json.dumps({
            "error": "badUUID",
            "msg": "Invalid UUID " + raw_uuid
            }), status=400, mimetype='application/json')



def build_ifdo_package(job_uuid, snapshot_uuid, snapshot_info):
    print(f"Starting package build thread {job_uuid}.")

    #print(json.dumps(get_couch()["crab_jobs"][job_uuid]))

    current_job_md = get_couch()["crab_jobs"][job_uuid]
    current_job_md["status"] = "ACTIVE"
    current_job_md["progress"] = 0.1
    get_couch()["crab_jobs"][job_uuid] = current_job_md

    # minimal ifdo interpretation
    ifdo_metadata = {
            "image-set-header": {
                    "image-set-ifdo-version": "v2.1.0",
                    "image-set-uuid": snapshot_info["_id"],
                    "image-set-name": snapshot_info["identifier"],
                    "image-set-handle": "https://example.com"
                },
            "image-set-items": {}
        }

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zipper:
        for sample_id in snapshot_info["samples"]:
            raw_format = snapshot_info["samples"][sample_id]["type"]["format"].split("/", 1)
            f_ext = "bin"
            m_type = None
            if raw_format[0] == "image":
                if raw_format[1] == "tiff":
                    f_ext = "tiff"
                    m_type = "TIFF"
            file_name = sample_id + "." + f_ext
            ifdo_metadata["image-set-items"][file_name] = {
                    "image-uuid": sample_id,
                    "image-media-type": m_type
                }
            image_path = "snapshots/" + snapshot_info["_id"] + "/raw_img/" + sample_id + "." + f_ext
            infile_object = get_bucket_object(path=image_path)
            infile_content = infile_object['Body'].read()
            zipper.writestr(file_name, infile_content)


        zipper.writestr("ifdo.json", json.dumps(ifdo_metadata, indent=4))

    get_s3_client().put_object(Bucket=get_bucket_name(), Key="snapshots/" + snapshot_uuid + "/ifdo_package.zip", Body=zip_buffer.getvalue())

    current_job_md = get_couch()["crab_jobs"][job_uuid]
    current_job_md["status"] = "COMPLETE"
    current_job_md["progress"] = 1
    get_couch()["crab_jobs"][job_uuid] = current_job_md

    current_snapshot_md = get_couch()["crab_snapshots"][snapshot_uuid]
    if not "packages" in current_snapshot_md:
        current_snapshot_md["packages"] = {}
    current_snapshot_md["packages"]["ifdo"] = {
            "path": "snapshots/" + snapshot_uuid + "/ifdo_package.zip",
            "host": get_bucket_uri()
        }
    get_couch()["crab_snapshots"][snapshot_uuid] = current_snapshot_md

    print(f"Job thread {job_uuid} complete.")


@snapshot_api.route("/api/v1/snapshots/<raw_uuid>/makepkg/<p_type>", methods=["GET"])
def api_v1_create_snapshot(raw_uuid, p_type):
    p_type = p_type.lower()
    try:
        uuid_obj = uuid.UUID(raw_uuid, version=4)
        snapshot_data = get_couch()["crab_snapshots"][str(uuid_obj)]
        job_uuid = uuid.uuid4()
        job_md = {
                "type": "SNAPSHOT_MAKE_PACKAGE",
                "target_id": str(uuid_obj),
                "status": "PENDING",
                "progress": 0.0
            }
        get_couch()["crab_jobs"][str(job_uuid)] = job_md
        if snapshot_data is None:
            return Response(json.dumps({
                "error": "snapshotNotFound",
                "msg": "Could not find snapshot with id {" + str(uuid_obj) + "}"
                }), status=404, mimetype='application/json')
        else:
            if p_type == "ifdo":
                proc = Process(target=build_ifdo_package, args=(str(job_uuid), str(uuid_obj), snapshot_data))
                proc.start()
            else:
                return Response(json.dumps({
                    "error": "badExportType",
                    "msg": "Could not make package with type \"" + p_type + "\""
                    }), status=400, mimetype='application/json')
            #get_couch()["crab_snapshots"][str(uuid_obj)] = snapshot_data
            return Response(json.dumps({
                "job_id": str(job_uuid),
                "snapshot": str(uuid_obj)
                }), status=200, mimetype='application/json')
            #args": request.form.to_dict(),
    except ValueError as e:
        print(e)

        return Response(json.dumps({
            "error": "badUUID",
            "msg": "Invalid UUID " + raw_uuid
            }), status=400, mimetype='application/json')
