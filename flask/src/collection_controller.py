from flask import Blueprint, request, render_template, Response, make_response, send_file, redirect
import uuid
import requests
import datetime
from multiprocessing import Process
import io
import json
from utils import get_session_info, get_app_frontend_globals, to_snake_case
from db import get_couch, get_bucket, get_bucket_uri, get_couch_base_uri, get_bucket_object, get_s3_client, get_bucket_name

collection_pages = Blueprint("collection_pages", __name__)
collection_api = Blueprint("collection_api", __name__)

@collection_pages.route("/collections/<raw_uuid>", methods=['GET'])
def collection_detail_screen(raw_uuid):
    try:
        uuid_obj = uuid.UUID(raw_uuid, version=4)
        collection_data = get_couch()["crab_collections"][str(uuid_obj)]
        return render_template("collection_info.html", global_vars=get_app_frontend_globals(), session_info=get_session_info(), collection_data=collection_data)
    except ValueError:
        return Response(json.dumps({
            "error": "badUUID",
            "msg": "Invalid UUID " + raw_uuid
            }), status=400, mimetype='application/json')


@collection_pages.route("/collections/<raw_uuid>/new-snapshot", methods=['GET'])
def collection_new_snapshot(raw_uuid):
    try:
        uuid_obj = uuid.UUID(raw_uuid, version=4)
        collection_data = get_couch()["crab_collections"][str(uuid_obj)]
        return render_template("collection_new_snapshot.html", global_vars=get_app_frontend_globals(), session_info=get_session_info(), collection_data=collection_data)
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
        collection_data = get_couch()["crab_collections"][str(uuid_obj)]
        return Response(json.dumps(collection_data), status=200, mimetype='application/json')
    except ValueError:
        return Response(json.dumps({
            "error": "badUUID",
            "msg": "Invalid UUID " + raw_uuid
            }), status=400, mimetype='application/json')

@collection_api.route("/api/v1/collections/<raw_uuid>/connect", methods=["GET"])
def api_v1_add_collection_connection(raw_uuid):
    try:
        uuid_obj = uuid.UUID(raw_uuid, version=4)
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


def build_collection_snapshot(job_uuid, snapshot_uuid, collection_info, snapshot_md):
    print(f"Starting snapshot thread {job_uuid}.")

    #print(json.dumps(get_couch()["crab_jobs"][job_uuid]))

    current_job_md = get_couch()["crab_jobs"][job_uuid]
    current_job_md["status"] = "ACTIVE"
    current_job_md["progress"] = 0
    get_couch()["crab_jobs"][job_uuid] = current_job_md

    creators = []
    creator_map = {}
    samples = []
    metadata_map = {}

    raw_metadata_run_heap = {}
    raw_metadata_sample_heap = {}
    raw_origin_metadata_run_heap = {}
    raw_origin_metadata_sample_heap = {}

    collection_global_metadata = {}
    residual_global_metadata = {}
    residual_run_metadata = {}
    residual_sample_metadata = {}
    collection_global_origin_metadata = {}
    residual_global_origin_metadata = {}
    residual_run_origin_metadata = {}
    residual_sample_origin_metadata = {}

    #run_info = []
    for run_id in collection_info["runs"]:
        run_info = get_couch()["crab_runs"][run_id]
        for sample_id in run_info["samples"]:
            samples.append(sample_id)
            creators.append(run_info["creator"]["uuid"])
            metadata_map[sample_id] = {
                    "creator": run_info["creator"],
                    "sensor": run_info["sensor"],
                    "from_run": run_id,
                    "ingest_timestamp": run_info["ingest_timestamp"]
                }
            sample_info = get_couch()["crab_samples"][sample_id]
            #print(json.dumps(sample_info, indent=4))
            if not "tags" in sample_info:
                sample_info["tags"] = {}

            raw_origin_metadata_sample_heap[sample_id] = sample_info["origin_tags"]
            raw_metadata_sample_heap[sample_id] = sample_info["tags"]
            residual_sample_origin_metadata[sample_id] = {}
            residual_sample_metadata[sample_id] = {}
        raw_origin_metadata_run_heap[run_id] = run_info["origin_tags"]
        raw_metadata_run_heap[run_id] = run_info["tags"]
        residual_run_origin_metadata[run_id] = {}
        residual_run_metadata[run_id] = {}
        #print(json.dumps(run_info, indent=4))

    for run_id in raw_metadata_run_heap:
        for key in raw_metadata_run_heap[run_id]:
            value = raw_metadata_run_heap[run_id][key]
            #if not type(value) is list:
            if key in collection_global_metadata:
                if not value in collection_global_metadata[key]:
                    collection_global_metadata[key].append(value)
            else:
                collection_global_metadata[key] = [value]

    for run_id in raw_origin_metadata_run_heap:
        for key in raw_origin_metadata_run_heap[run_id]:
            value = raw_origin_metadata_run_heap[run_id][key]
            #if not type(value) is list:
            if key in collection_global_origin_metadata:
                if not value in collection_global_origin_metadata[key]:
                    collection_global_origin_metadata[key].append(value)
            else:
                collection_global_origin_metadata[key] = [value]


    for sample_id in raw_metadata_sample_heap:
        for key in raw_metadata_sample_heap[sample_id]:
            value = raw_metadata_sample_heap[sample_id][key]
            if not type(value) is list:
                if key in collection_global_metadata:
                    if not value in collection_global_metadata[key]:
                        collection_global_metadata[key].append(value)
                else:
                    collection_global_metadata[key] = [value]

    for sample_id in raw_origin_metadata_sample_heap:
        for key in raw_origin_metadata_sample_heap[sample_id]:
            value = raw_origin_metadata_sample_heap[sample_id][key]
            if not type(value) is list:
                if key in collection_global_origin_metadata:
                    if not value in collection_global_origin_metadata[key]:
                        collection_global_origin_metadata[key].append(value)
                else:
                    collection_global_origin_metadata[key] = [value]


    for key in collection_global_metadata:
        if len(collection_global_metadata[key]) > 1:
            for run_id in collection_info["runs"]:
                if not type(raw_metadata_run_heap[run_id][key]) is list:
                    residual_run_metadata[run_id][key] = raw_metadata_run_heap[run_id][key]
        else:
            if not type(collection_global_metadata[key][0]) is list:
                residual_global_metadata[key] = collection_global_metadata[key][0]

    for key in collection_global_origin_metadata:
        if len(collection_global_origin_metadata[key]) > 1:
            for run_id in collection_info["runs"]:
                if not type(raw_origin_metadata_run_heap[run_id][key]) is list:
                    residual_run_origin_metadata[run_id][key] = raw_origin_metadata_run_heap[run_id][key]
        else:
            if not type(collection_global_origin_metadata[key][0]) is list:
                residual_global_origin_metadata[key] = collection_global_origin_metadata[key][0]

    #print(json.dumps(residual_run_origin_metadata, indent=4))

    for run_id in residual_run_origin_metadata:
        run_samples = get_couch()["crab_runs"][run_id]["samples"]
        for sample_id in run_samples:
            residual_sample_metadata[sample_id] = residual_run_metadata[run_id]
            residual_sample_origin_metadata[sample_id] = residual_run_origin_metadata[run_id]

    for sample_id in samples:
        for key in raw_metadata_sample_heap[sample_id]:
            residual_sample_metadata[sample_id][key] = raw_metadata_sample_heap[sample_id][key]
        for key in raw_origin_metadata_sample_heap[sample_id]:
            residual_sample_origin_metadata[sample_id][key] = raw_origin_metadata_sample_heap[sample_id][key]

    #print(json.dumps(residual_sample_origin_metadata, indent=4))
    #print(json.dumps(residual_global_origin_metadata, indent=4))

    snapshot_md["runs"] = {}

    for sample_id in samples:
        snapshot_md["runs"][sample_id] = residual_sample_metadata[sample_id]
        snapshot_md["runs"][sample_id]["origin_tags"] = residual_sample_origin_metadata[sample_id]

    for key in residual_global_metadata:
        snapshot_md[key] = residual_global_metadata[key]
    snapshot_md["origin_tags"] = residual_global_origin_metadata

    #print(json.dumps(snapshot_md, indent=4))

    current_job_md = get_couch()["crab_jobs"][job_uuid]
    current_job_md["progress"] = 0.3
    get_couch()["crab_jobs"][job_uuid] = current_job_md

    get_couch()["crab_snapshots"][snapshot_uuid] = snapshot_md

    with io.BytesIO(json.dumps(snapshot_md, indent=4).encode()) as f:
        get_s3_client().upload_fileobj(f, get_bucket_name(), "snapshots/" + snapshot_uuid + ".json")

    current_job_md = get_couch()["crab_jobs"][job_uuid]
    current_job_md["progress"] = 0.6
    get_couch()["crab_jobs"][job_uuid] = current_job_md



    current_job_md = get_couch()["crab_jobs"][job_uuid]
    current_job_md["status"] = "COMPLETE"
    current_job_md["progress"] = 1
    get_couch()["crab_jobs"][job_uuid] = current_job_md

    print(f"Job thread {job_uuid} complete.")


@collection_api.route("/api/v1/collections/<raw_uuid>/snapshot", methods=["POST"])
def api_v1_create_snapshot(raw_uuid):
    try:
        uuid_obj = uuid.UUID(raw_uuid, version=4)
        collection_data = get_couch()["crab_collections"][str(uuid_obj)]
        name = request.form.get("snapshot_name", "")
        if len(name) == 0:
            name = datetime.datetime.now().strftime("%Y-%m-%d")
        public_avail = request.form.get("public_visibility_switch", "false")
        public_avail = public_avail == "true"
        snapshot_uuid = uuid.uuid4()
        snapshot_md = {
                "identifier": name,
                "collection": str(uuid_obj)
            }
        job_uuid = uuid.uuid4()
        job_md = {
                "type": "NEW_SNAPSHOT",
                "target_id": str(snapshot_uuid),
                "status": "PENDING",
                "progress": 0.0
            }
        get_couch()["crab_jobs"][str(job_uuid)] = job_md
        if collection_data is None:
            return Response(json.dumps({
                "error": "collectionNotFound",
                "msg": "Could not find collection with id {" + str(uuid_obj) + "}"
                }), status=404, mimetype='application/json')
        else:
            proc = Process(target=build_collection_snapshot, args=(str(job_uuid), str(snapshot_uuid), collection_data, snapshot_md))
            proc.start()
            if not "snapshots" in collection_data:
                collection_data["snapshots"] = []
            collection_data["snapshots"].append(str(snapshot_uuid))
            #get_couch()["crab_collections"][str(uuid_obj)] = collection_data
            return Response(json.dumps({
                "name": name,
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
