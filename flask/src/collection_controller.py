from flask import Blueprint, request, render_template, Response, make_response, send_file, redirect
import uuid
import requests
import datetime
from multiprocessing import Process
import io
import zipfile
import hashlib
import json
from utils import get_session_info, get_app_frontend_globals, to_snake_case
from db import get_couch, get_bucket, get_bucket_uri, get_couch_base_uri, get_bucket_object, get_s3_client, get_bucket_name, get_couch_client, advertise_job, get_s3_profiles, get_s3_profile

collection_pages = Blueprint("collection_pages", __name__)
collection_api = Blueprint("collection_api", __name__)

def can_view(collection_uuid):
    session_info = get_session_info()
    project_data = get_couch()["crab_projects"][get_couch()["crab_collections"][collection_uuid]["project"]]
    if not session_info is None:
        if session_info["user_uuid"] in project_data["collaborators"]:
            return True
    return project_data["public_visibility"]

def can_edit(collection_uuid):
    session_info = get_session_info()
    project_data = get_couch()["crab_projects"][get_couch()["crab_collections"][collection_uuid]["project"]]
    if not session_info is None:
        if session_info["user_uuid"] in project_data["collaborators"]:
            return True
    return False

@collection_pages.route("/collections/<raw_uuid>", methods=['GET'])
def collection_detail_screen(raw_uuid):
    session_info = get_session_info()
    try:
        uuid_obj = uuid.UUID(raw_uuid, version=4)

        if not can_view(str(uuid_obj)):
            return Response(json.dumps({
                "error": "readDenied",
                "msg": "User is not allowed to view this resource."
                }), status=401, mimetype='application/json')

        collection_data = get_couch()["crab_collections"][str(uuid_obj)]
        project_data = get_couch()["crab_projects"][get_couch()["crab_collections"][str(uuid_obj)]["project"]]
        is_collaborator = False
        if not session_info is None:
            if session_info["user_uuid"] in project_data["collaborators"]:
                is_collaborator = True
        return render_template("collection_info.html", global_vars=get_app_frontend_globals(), session_info=session_info, collection_data=collection_data, is_collaborator=is_collaborator)
    except ValueError:
        return Response(json.dumps({
            "error": "badUUID",
            "msg": "Invalid UUID " + raw_uuid
            }), status=400, mimetype='application/json')


@collection_pages.route("/collections/<raw_uuid>/new-snapshot", methods=['GET'])
def collection_new_snapshot(raw_uuid):
    try:
        uuid_obj = uuid.UUID(raw_uuid, version=4)

        if not can_edit(str(uuid_obj)):
            return Response(json.dumps({
                "error": "writeDenied",
                "msg": "User is not allowed to edit this resource."
                }), status=401, mimetype='application/json')
        s3_profiles = []
        for profile_id in get_s3_profiles():
            s3_profiles.append({
                    "id": profile_id,
                    "name": get_s3_profile(profile_id)["name"]
                })
        collection_data = get_couch()["crab_collections"][str(uuid_obj)]
        return render_template("collection_new_snapshot.html", global_vars=get_app_frontend_globals(), session_info=get_session_info(), collection_data=collection_data, s3_profiles=s3_profiles)
    except ValueError:
        return Response(json.dumps({
            "error": "badUUID",
            "msg": "Invalid UUID " + raw_uuid
            }), status=400, mimetype='application/json')

@collection_pages.route("/collections", methods=['GET'])
def collection_browse_screen():
    return render_template("collections.html", global_vars=get_app_frontend_globals(), session_info=get_session_info())

@collection_api.route("/api/v1/collections", methods=["POST", "GET"])
def api_v1_get_collections():
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

    ret = requests.post(get_couch_base_uri() + "crab_collections/" + "_find", json=mango).json()
    #print(ret)

    return Response(json.dumps(ret), status=200, mimetype='application/json')

@collection_api.route("/api/v1/collections/<raw_uuid>", methods=['GET'])
def api_v1_get_collection(raw_uuid):
    try:
        uuid_obj = uuid.UUID(raw_uuid, version=4)

        if not can_view(str(uuid_obj)):
            return Response(json.dumps({
                "error": "readDenied",
                "msg": "User is not allowed to view this resource."
                }), status=401, mimetype='application/json')

        collection_data = get_couch()["crab_collections"][str(uuid_obj)]
        return Response(json.dumps(collection_data), status=200, mimetype='application/json')
    except ValueError:
        return Response(json.dumps({
            "error": "badUUID",
            "msg": "Invalid UUID " + raw_uuid
            }), status=400, mimetype='application/json')

@collection_api.route("/api/v1/collections/<raw_uuid>/via_annotation_project", methods=['GET'])
def api_v1_get_collection_via_proj(raw_uuid):
    try:
        uuid_obj = uuid.UUID(raw_uuid, version=4)

        if not can_view(str(uuid_obj)):
            return Response(json.dumps({
                "error": "readDenied",
                "msg": "User is not allowed to view this resource."
                }), status=401, mimetype='application/json')

        couch_client = get_couch_client()

        collection_info = couch_client.get_document("crab_collections", str(uuid_obj))

        via_config = {
                "file": {
                "loc_prefix": {"1": "","2": "","3": "","4": ""}},
                "ui": {
                    "file_content_align": "center",
                    "file_metadata_editor_visible": True,
                    "spatial_metadata_editor_visible": True,
                    "temporal_segment_metadata_editor_visible": False,
                    "spatial_region_label_attribute_id": "",
                    "gtimeline_visible_row_count": "4"
                }
            }

        #via_attributes = {
        #        "1": {
        #        "aname": "beans",
        #        "anchor_id": "FILE1_Z0_XY1",
        #        "type": 2,
        #        "desc": "",
        #        "options": {
        #            "0": "is_beans"
        #        },
        #        "default_option_id": ""
        #        }
        #    }

        via_attributes = {}
        via_views = {}
        via_files = {}

        sample_ids = []
        for run_id in collection_info["runs"]:
            run_info = couch_client.get_document("crab_runs", run_id)
            for sample_id in run_info["samples"]:
                sample_ids.append(sample_id)

        sample_ids.sort() # Used to make sure order is easy to parse for end users!

        idx = 1
        for sample_id in sample_ids:
            via_files[str(idx)] = {
                    "fid": str(idx),
                    "fname": sample_id,
                    "type": 2,
                    "loc": 2,
                    "src": "/api/v1/samples/" + sample_id + ".jpeg"
                }
            via_views[str(idx)] = {
                    "fid_list": [
                        str(idx)
                    ]
                }
            idx += 1

        vid_list = []
        for key in via_views:
            vid_list.append(key)

        via_project = {
            "pid": str(uuid_obj),
            "rev": "1",
            "rev_timestamp": "1738233380656",
            "pname": "beans",
            "creator": "CRAB (https://github.com/NOC-OI/crab)",
            "created": 1738233184858,
            "vid_list": vid_list
        }

        via_metadata = {}

        via_data = {
                "project": via_project,
                "config": via_config,
                "attribute": via_attributes,
                "file": via_files,
                "metadata": {},
                "view": via_views
            }

        return Response(json.dumps(via_data), status=200, mimetype='application/json')
    except ValueError:
        return Response(json.dumps({
            "error": "badUUID",
            "msg": "Invalid UUID " + raw_uuid
            }), status=400, mimetype='application/json')

@collection_api.route("/api/v1/collections/<raw_uuid>/connect", methods=["GET"])
def api_v1_add_collection_connection(raw_uuid):
    try:
        uuid_obj = uuid.UUID(raw_uuid, version=4)

        if not can_edit(str(uuid_obj)):
            return Response(json.dumps({
                "error": "writeDenied",
                "msg": "User is not allowed to edit this resource."
                }), status=401, mimetype='application/json')

        collection_data = get_couch()["crab_collections"][str(uuid_obj)]
        to_raw_uuid = request.args.get("to", None)
        to_uuid_obj = uuid.UUID(to_raw_uuid, version=4)
        to_type = request.args.get("type", None)
        if to_type == "run":
            #run_data = get_couch()["crab_runs"][str(to_uuid_obj)]
            if not "runs" in collection_data:
                collection_data["runs"] = []
            collection_data["runs"].append(str(to_uuid_obj))
            get_couch()["crab_collections"][str(uuid_obj)] = collection_data

            redirect_uri = request.args.get("redirect", "")
            if len(redirect_uri) > 0:
                return redirect(redirect_uri, code=302)
            else:
                return Response(json.dumps({
                    "msg": "done",
                    "collection": collection_data
                    }), status=200, mimetype='application/json')
        else:
            return Response(json.dumps({
                "error": "badType",
                "msg": "Invalid target type \"" + to_type + "\""
                }), status=400, mimetype='application/json')
    except ValueError:
        return Response(json.dumps({
            "error": "badUUID",
            "msg": "Invalid UUID " + raw_uuid
            }), status=400, mimetype='application/json')





@collection_api.route("/api/v1/collections/<raw_uuid>/snapshot", methods=["POST"])
def api_v1_create_snapshot(raw_uuid):
    try:
        uuid_obj = uuid.UUID(raw_uuid, version=4)

        if not can_edit(str(uuid_obj)):
            return Response(json.dumps({
                "error": "writeDenied",
                "msg": "User is not allowed to edit this resource."
                }), status=401, mimetype='application/json')

        collection_data = get_couch()["crab_collections"][str(uuid_obj)]
        name = request.form.get("snapshot_name", "")
        if len(name) == 0:
            name = datetime.datetime.now().strftime("%Y-%m-%d")
        public_avail = request.form.get("public_visibility_switch", "false")
        public_avail = public_avail == "true"
        snapshot_uuid = uuid.uuid4()
        snapshot_md = {
                "identifier": name,
                "public_visibility": public_avail,
                "collection": str(uuid_obj),
                "s3_profile": request.form.get("s3_profile", None)
            }
        job_uuid = uuid.uuid4()
        if collection_data is None:
            return Response(json.dumps({
                "error": "collectionNotFound",
                "msg": "Could not find collection with id {" + str(uuid_obj) + "}"
                }), status=404, mimetype='application/json')
        else:
            #proc = Process(target=build_collection_snapshot, args=(str(job_uuid), str(snapshot_uuid), collection_data, snapshot_md))
            #proc.start()

            job_md = {
                "type": "TAKE_SNAPSHOT",
                "target_id": str(snapshot_uuid),
                "status": "PENDING",
                "progress": 0.0,
                "job_args": snapshot_md
            }
            get_couch()["crab_jobs"][str(job_uuid)] = job_md
            #


            advertise_job(str(job_uuid))

            #get_couch()["crab_collections"][str(uuid_obj)] = collection_data
            return Response(json.dumps({
                "name": name,
                "snapshot_id": str(snapshot_uuid),
                "make_public": public_avail,
                "job_id": str(job_uuid),
                "collection": collection_data
                }), status=200, mimetype='application/json')
            #args": request.form.to_dict(),
    except ValueError as e:
        print(e)

        return Response(json.dumps({
            "error": "badUUID",
            "msg": "Invalid UUID " + raw_uuid
            }), status=400, mimetype='application/json')
