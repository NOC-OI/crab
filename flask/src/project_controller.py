from flask import Blueprint, request, render_template, Response, make_response, send_file, redirect
import uuid
import requests
import datetime
import json
from utils import get_session_info, get_app_frontend_globals, to_snake_case
from db import get_couch, get_bucket, get_bucket_uri, get_couch_base_uri, get_bucket_object
import markdown
from pygments.formatters import HtmlFormatter
from base64 import urlsafe_b64encode


project_pages = Blueprint("project_pages", __name__)
project_api = Blueprint("project_api", __name__)

def can_view(project_uuid):
    session_info = get_session_info()
    project_data = get_couch()["crab_projects"][project_uuid]
    if not session_info is None:
        if session_info["user_uuid"] in project_data["collaborators"]:
            return True
    return project_data["public_visibility"]

def can_edit(project_uuid):
    session_info = get_session_info()
    project_data = get_couch()["crab_projects"][project_uuid]
    if not session_info is None:
        if session_info["user_uuid"] in project_data["collaborators"]:
            return True
    return False

@project_pages.route("/projects/new", methods=['GET'])
def project_new_screen():
    session_info = get_session_info()
    if session_info is None:
        return redirect("/login", code=302)
    return render_template("project_new.html", global_vars=get_app_frontend_globals(), session_info=get_session_info())



@project_pages.route("/projects/new", methods=['POST'])
def unpack_upload():
    session_info = get_session_info()
    if session_info is None:
        return Response(json.dumps({
            "error": "notLoggedIn",
            "msg": "User is not logged in, or session has expired."
            }), status=403, mimetype='application/json')

    project_uuid = str(uuid.uuid4())
    identifier = request.form.get("identifier", project_uuid)
    public_visibility = request.form.get("public_visibility", False)
    description = request.form.get("description", "")
    readme = request.form.get("readme", "")
    dt = datetime.datetime.now()
    timestamp = "{:04d}-{:02d}-{:02d}T{:02d}:{:02d}:{:02d}Z".format(dt.year,dt.month,dt.day,dt.hour,dt.minute,dt.second)

    initial_collection_uuid = str(uuid.uuid4())

    document_template = {
            "identifier": identifier,
            "public_visibility": public_visibility,
            "collaborators": [session_info["user_uuid"]],
            "description": description,
            "readme": readme,
            "creation_timestamp": timestamp,
            "collections": [initial_collection_uuid]
        }

    collection_template = {
            "runs": [],
            "identifier": "main",
            "project": project_uuid
        }

    project_dblist = get_couch()["crab_projects"]
    project_dblist[project_uuid] = document_template
    collections_dblist = get_couch()["crab_collections"]
    collections_dblist[initial_collection_uuid] = collection_template

    #    return Response(json.dumps({
    #        "error": "badProfile",
    #        "msg": "Invalid Profile " + profile
    #        }), status=400, mimetype='application/json')

    response = make_response(redirect("/projects/" + project_uuid, code=302))
    return response

@project_pages.route("/projects/<raw_uuid>/edit", methods=['GET'])
def project_edit_screen(raw_uuid):
    try:
        uuid_obj = uuid.UUID(raw_uuid, version=4)

        if not can_edit(str(uuid_obj)):
            return Response(json.dumps({
                "error": "writeDenied",
                "msg": "User is not allowed to edit this resource."
                }), status=401, mimetype='application/json')

        project_data = get_couch()["crab_projects"][str(uuid_obj)]
        return render_template("project_edit.html", global_vars=get_app_frontend_globals(), session_info=get_session_info(), project_data=project_data)
    except ValueError:
        return Response(json.dumps({
            "error": "badUUID",
            "msg": "Invalid UUID " + raw_uuid
            }), status=400, mimetype='application/json')

@project_pages.route("/projects/<raw_uuid>/edit", methods=['POST'])
def project_edit_function(raw_uuid):
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

        project_data = get_couch()["crab_projects"][str(uuid_obj)]

        project_data["identifier"] = request.form.get("identifier", str(uuid_obj))
        project_data["public_visibility"] = request.form.get("public_visibility", False)
        project_data["description"] = request.form.get("description", "")
        colabs_raw = request.form.get("collaborators", "").splitlines()
        collaborators = []
        if len(colabs_raw) == 0:
            collaborators.append(session_info["user_uuid"])
        for collaborator in colabs_raw:
            try:
                uuid_colab = uuid.UUID(collaborator, version=4)
                collaborators.append(str(uuid_colab))
            except ValueError:
                pass
        project_data["collaborators"] = collaborators
        project_data["readme"] = request.form.get("readme", "")

        get_couch()["crab_projects"][str(uuid_obj)] = project_data

        response = make_response(redirect("/projects/" + str(uuid_obj), code=302))
        return response
    except ValueError:
        return Response(json.dumps({
            "error": "badUUID",
            "msg": "Invalid UUID " + raw_uuid
            }), status=400, mimetype='application/json')

@project_pages.route("/projects/<raw_uuid>", methods=['GET'])
def project_detail_screen(raw_uuid):
    try:
        uuid_obj = uuid.UUID(raw_uuid, version=4)

        if not can_view(str(uuid_obj)):
            return Response(json.dumps({
                "error": "readDenied",
                "msg": "User is not allowed to view this resource."
                }), status=401, mimetype='application/json')

        project_data = get_couch()["crab_projects"][str(uuid_obj)]
        md_template_string = markdown.markdown(
            project_data["readme"], extensions=[
                "markdown.extensions.extra",
                "markdown.extensions.codehilite",
                "markdown.extensions.sane_lists"
            ]
        )
        md_template_string = md_template_string.replace("<table>", "<table class=\"table table-hover\">")
        formatter = HtmlFormatter(style="emacs",full=True,cssclass="codehilite")
        css_string = formatter.get_style_defs()
        md_css_string = "<style>" + css_string + "</style>"
        md_template_string = md_template_string.replace("<div class=\"codehilite\">", "<div class=\"codehilite container p-2 my-3 border rounded\">")
        md_template_string = md_template_string.replace("<pre>", "<pre style=\"margin:0;\">")
        md_template = md_css_string + md_template_string

        collections = []

        for collection_id in project_data["collections"]:
            collection = get_couch()["crab_collections"][str(collection_id)]
            runs = []
            if "runs" in collection:
                for run_id in collection["runs"]:
                    if run_id in get_couch()["crab_runs"]:
                        runs.append(get_couch()["crab_runs"][run_id])
            snapshots = []
            if "snapshots" in collection:
                for snapshot_id in collection["snapshots"]:
                    if snapshot_id in get_couch()["crab_snapshots"]:
                        snapshots.append(get_couch()["crab_snapshots"][snapshot_id])
                        #print(json.dumps(get_couch()["crab_snapshots"][snapshot_id], indent=2))

            via_project_string = urlsafe_b64encode(json.dumps({
                    "remote_project": "/api/v1/collections/" + collection["_id"] + "/via_annotation_project"
                }).encode("utf-8")).decode("utf-8")

            collections.append({
                    "_id": collection["_id"],
                    "identifier": collection["identifier"],
                    "via_project_string": via_project_string,
                    "snapshots": snapshots,
                    "runs": runs
                })

        return render_template("project_info.html", global_vars=get_app_frontend_globals(), session_info=get_session_info(), project_data=project_data, project_readme=md_template, collections=collections, can_edit=can_edit(str(uuid_obj)))
    except ValueError:
        return Response(json.dumps({
            "error": "badUUID",
            "msg": "Invalid UUID " + raw_uuid
            }), status=400, mimetype='application/json')

@project_pages.route("/projects", methods=['GET'])
def project_browse_screen():
    return render_template("projects.html", global_vars=get_app_frontend_globals(), session_info=get_session_info())

@project_api.route("/api/v1/projects", methods=["POST", "GET"])
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
            "fields": ["collaborators", "creation_timestamp", "_id", "identifier", "description", "collections"],
            "skip": page * limit,
            "sort": mango_sort,
            "limit": limit
        }
    #            "sort": mango_sort,

    ret = requests.post(get_couch_base_uri() + "crab_projects/" + "_find", json=mango).json()
    #print(ret)
    return Response(json.dumps(ret), status=200, mimetype='application/json')

@project_api.route("/api/v1/projects/<raw_uuid>/new_collection", methods=["POST"])
def api_v1_new_collection(raw_uuid):
    try:
        uuid_obj = uuid.UUID(raw_uuid, version=4)

        if not can_view(str(uuid_obj)):
            return Response(json.dumps({
                "error": "readDenied",
                "msg": "User is not allowed to view this resource."
                }), status=401, mimetype='application/json')

        project_data = get_couch()["crab_projects"][str(uuid_obj)]
        new_collection_id = str(uuid.uuid4())

        collection_template = {
            "runs": [],
            "identifier": request.form.get("name","untitled"),
            "project": str(uuid_obj)
        }

        project_data["collections"].append(new_collection_id)

        get_couch()["crab_collections"][new_collection_id] = collection_template
        get_couch()["crab_projects"][str(uuid_obj)] = project_data

        redirect_uri = request.args.get("redirect", "")
        if len(redirect_uri) > 0:
            return redirect(redirect_uri, code=302)
        else:
            return Response(json.dumps({
                "msg": "done",
                "collection": collection_data
                }), status=200, mimetype='application/json')
    except ValueError:
        return Response(json.dumps({
            "error": "badUUID",
            "msg": "Invalid UUID " + raw_uuid
            }), status=400, mimetype='application/json')

@project_api.route("/api/v1/projects/<raw_uuid>", methods=['GET'])
def api_v1_get_project(raw_uuid):
    try:
        uuid_obj = uuid.UUID(raw_uuid, version=4)

        if not can_edit(str(uuid_obj)):
            return Response(json.dumps({
                "error": "writeDenied",
                "msg": "User is not allowed to edit this resource."
                }), status=401, mimetype='application/json')

        project_data = get_couch()["crab_projects"][str(uuid_obj)]
        return Response(json.dumps(project_data), status=200, mimetype='application/json')
    except ValueError:
        return Response(json.dumps({
            "error": "badUUID",
            "msg": "Invalid UUID " + raw_uuid
            }), status=400, mimetype='application/json')
