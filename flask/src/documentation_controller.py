
from flask import Blueprint, request, render_template, Response, make_response, send_file
import markdown
import os
from pygments.formatters import HtmlFormatter
from utils import get_session_info, get_app_frontend_globals, to_snake_case

documentation_pages = Blueprint("documentation_pages", __name__)

def markdown_page(path):
    split_path = path.split("/")
    sanit_path = ""
    for ele in split_path:
        sanit_path = sanit_path + "/" + to_snake_case(ele)

    raw_markdown = None

    doc_path = "docs" + sanit_path
    doc_path = doc_path.replace("_", "-")

    print(doc_path)

    if os.path.isfile(doc_path + ".md"):
        with open(doc_path + ".md") as f:
            raw_markdown = f.read()
    elif os.path.isfile(doc_path + "/index.md"):
        with open(doc_path + "/index.md") as f:
            raw_markdown = f.read()

    if raw_markdown is None:
        return render_template("404.html", global_vars=get_app_frontend_globals(), session_info=get_session_info())

    md_template_string = markdown.markdown(
        raw_markdown, extensions=[
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

    return render_template("doc_page.html", global_vars=get_app_frontend_globals(), session_info=get_session_info(), markdown=md_template)

@documentation_pages.route("/docs", defaults={'path': 'index'}, methods=['GET'])
@documentation_pages.route("/docs/", defaults={'path': 'index'}, methods=['GET'])
@documentation_pages.route("/docs/<path:path>", methods=['GET'])
def docs_index(path):
    return markdown_page(path)
