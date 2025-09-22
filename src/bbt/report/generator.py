from jinja2 import Environment, FileSystemLoader, select_autoescape
from pathlib import Path
import datetime

TEMPLATE_DIR = Path(__file__).resolve().parents[2] / "templates"

env = Environment(
    loader=FileSystemLoader(str(TEMPLATE_DIR)),
    autoescape=select_autoescape(["html", "xml", "md"])
)
template = env.get_template("report_template.md.j2")

def render_report(scope: dict) -> str:
    ctx = {
        "generated_at": datetime.datetime.utcnow().isoformat() + "Z",
        "scope": scope
    }
    return template.render(**ctx)