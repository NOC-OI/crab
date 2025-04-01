from flask import Flask, render_template
from flasgger import Swagger
from werkzeug.middleware.proxy_fix import ProxyFix
import os

csrf_secret_key = os.environ.get("CRAB_CSRF_SECRET_KEY")


app = Flask(__name__)

crab_schemes = ["http"]
crab_external_host = os.environ.get("CRAB_EXTERNAL_HOST") + ":" + os.environ.get("CRAB_EXTERNAL_PORT")
if os.environ.get("CRAB_EXTERNAL_PORT") == "80":
    crab_external_host = os.environ.get("CRAB_EXTERNAL_HOST")
elif os.environ.get("CRAB_EXTERNAL_PORT") == "443":
    crab_external_host = os.environ.get("CRAB_EXTERNAL_HOST")
    crab_schemes = ["https"]

app.config["SWAGGER"] = {
    "title": "CRAB",
    "description": "API for ocean image data",
    "termsOfService": crab_schemes[0] + "://" + crab_external_host + "/tos",
    "host": crab_external_host,
    "schemes": crab_schemes,
    "version": "1.0.0",
    "uiversion": 3
}

swagger = Swagger(app)
app.wsgi_app = ProxyFix(app.wsgi_app)


from utils import get_session_info, get_app_frontend_globals
from user_management_controller import login_pages, account_pages, access_token_pages, session_api, users_api
from ingest_controller import ingest_pages
from run_controller import run_pages, run_api
from project_controller import project_pages, project_api
from layer_controller import layer_pages, layer_api
from job_controller import job_pages, job_api
from snapshot_controller import snapshot_pages, snapshot_api
from documentation_controller import documentation_pages
from annotation_set_controller import annotation_set_pages, annotation_set_api
from export_controller import export_pages, export_api
from workspace_controller import workspace_pages, workspace_api

app.register_blueprint(login_pages)
app.register_blueprint(account_pages)
app.register_blueprint(access_token_pages)
app.register_blueprint(users_api)
app.register_blueprint(session_api)
app.register_blueprint(ingest_pages)
app.register_blueprint(run_pages)
app.register_blueprint(run_api)
app.register_blueprint(project_pages)
app.register_blueprint(project_api)
app.register_blueprint(layer_pages)
app.register_blueprint(layer_api)
app.register_blueprint(job_pages)
app.register_blueprint(job_api)
app.register_blueprint(snapshot_pages)
app.register_blueprint(snapshot_api)
app.register_blueprint(annotation_set_pages)
app.register_blueprint(annotation_set_api)
app.register_blueprint(export_pages)
app.register_blueprint(export_api)
app.register_blueprint(documentation_pages)
app.register_blueprint(workspace_pages)
app.register_blueprint(workspace_api)

@app.errorhandler(404)
def not_found_error_handler(e):
    return render_template("404.html", global_vars=get_app_frontend_globals(), session_info=get_session_info())

@app.route("/")
def home_screen():
    return render_template("index.html", global_vars=get_app_frontend_globals(), session_info=get_session_info())

if __name__ == "__main__":
    app.run()
