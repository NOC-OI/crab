from flask import Blueprint, request, render_template, Response, make_response, send_file, redirect
import uuid
import requests
import datetime
import json
from utils import get_session_info, get_app_frontend_globals, to_snake_case
from db import get_couch, get_bucket, get_bucket_uri, get_couch_base_uri, get_bucket_object

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
    print(ret)
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
                "msg": "Done",
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
