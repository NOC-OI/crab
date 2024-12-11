from flask import Flask, render_template
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app)

from utils import get_session_info, get_app_frontend_globals
from user_management_controller import login_pages, account_pages
from ingest_controller import ingest_pages
from browse_controller import browse_pages, browse_api

app.register_blueprint(login_pages)
app.register_blueprint(account_pages)
app.register_blueprint(ingest_pages)
app.register_blueprint(browse_pages)
app.register_blueprint(browse_api)

@app.errorhandler(404)
def not_found_error_handler(e):
    return render_template("404.html", global_vars=get_app_frontend_globals(), session_info=get_session_info())

@app.route("/")
def home_screen():
    return render_template("index.html", global_vars=get_app_frontend_globals(), session_info=get_session_info())

if __name__ == "__main__":
    app.run()
