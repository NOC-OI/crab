from flask import Flask, render_template
from werkzeug.middleware.proxy_fix import ProxyFix
import os

csrf_secret_key = os.environ.get("CRAB_CSRF_SECRET_KEY")

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app)

from utils import get_session_info, get_app_frontend_globals
from user_management_controller import login_pages, account_pages, access_token_pages, session_api
from ingest_controller import ingest_pages
from run_controller import run_pages, run_api
from project_controller import project_pages, project_api
from collection_controller import collection_pages, collection_api
from job_controller import job_pages, job_api
from snapshot_controller import snapshot_pages, snapshot_api

app.register_blueprint(login_pages)
app.register_blueprint(account_pages)
app.register_blueprint(access_token_pages)
app.register_blueprint(session_api)
app.register_blueprint(ingest_pages)
app.register_blueprint(run_pages)
app.register_blueprint(run_api)
app.register_blueprint(project_pages)
app.register_blueprint(project_api)
app.register_blueprint(collection_pages)
app.register_blueprint(collection_api)
app.register_blueprint(job_pages)
app.register_blueprint(job_api)
app.register_blueprint(snapshot_pages)
app.register_blueprint(snapshot_api)

@app.errorhandler(404)
def not_found_error_handler(e):
    return render_template("404.html", global_vars=get_app_frontend_globals(), session_info=get_session_info())

@app.route("/")
def home_screen():
    return render_template("index.html", global_vars=get_app_frontend_globals(), session_info=get_session_info())

if __name__ == "__main__":
    app.run()
