from flask import Blueprint, request, render_template, Response, make_response, send_file, redirect
import uuid
import requests
import datetime
import json
from utils import get_session_info, get_app_frontend_globals, to_snake_case
from db import get_couch, get_bucket, get_bucket_uri, get_couch_base_uri, get_bucket_object
import markdown
from pygments.formatters import HtmlFormatter


project_pages = Blueprint("project_pages", __name__)
project_api = Blueprint("project_api", __name__)

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

@project_pages.route("/projects/<raw_uuid>", methods=['GET'])
def project_detail_screen(raw_uuid):
    try:
        uuid_obj = uuid.UUID(raw_uuid, version=4)
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
            for run_id in collection["runs"]:
                runs.append(get_couch()["crab_runs"][str(run_id)])
            collections.append({
                    "_id": collection["_id"],
                    "identifier": collection["identifier"],
                    "runs": runs
                })

        return render_template("project_info.html", global_vars=get_app_frontend_globals(), session_info=get_session_info(), project_data=project_data, project_readme=md_template, collections=collections)
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
            "limit": limit
        }
    #            "sort": mango_sort,

    ret = requests.post(get_couch_base_uri() + "crab_projects/" + "_find", json=mango).json()
    print(ret)
    return Response(json.dumps(ret), status=200, mimetype='application/json')

@project_api.route("/api/v1/projects/<raw_uuid>", methods=['GET'])
def api_v1_get_project(raw_uuid):
    try:
        uuid_obj = uuid.UUID(raw_uuid, version=4)
        project_data = get_couch()["crab_projects"][str(uuid_obj)]
        return Response(json.dumps(project_data), status=200, mimetype='application/json')
    except ValueError:
        return Response(json.dumps({
            "error": "badUUID",
            "msg": "Invalid UUID " + raw_uuid
            }), status=400, mimetype='application/json')
