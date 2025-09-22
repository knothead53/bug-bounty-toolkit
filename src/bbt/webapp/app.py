from pathlib import Path
from typing import List, Optional
import json
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader, select_autoescape

from bbt.recon.crtsh import fetch_crtsh_subdomains
from bbt.recon.http_checker import check_hosts
from bbt.config import DEFAULT_OUTPUT_DIR

ROOT = Path(__file__).resolve().parents[3]  # repo root
TEMPLATES_DIR = ROOT / "templates_web"
OUTPUT_DIR = ROOT / "output"
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)

env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html", "xml"])
)

app = FastAPI(title="Bug Bounty Toolkit")

# static files (css if we add any later)
STATIC_DIR = ROOT / "static"
STATIC_DIR.mkdir(exist_ok=True, parents=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

def render(name: str, **ctx) -> HTMLResponse:
    tmpl = env.get_template(name)
    return HTMLResponse(tmpl.render(**ctx))

@app.get("/", response_class=HTMLResponse)
def home():
    # list existing scope files to pick from
    scopes = sorted(OUTPUT_DIR.glob("*_scope.json"))
    return render("home.html", scopes=[p.name for p in scopes], message=None, results=None)

@app.post("/init-scope", response_class=HTMLResponse)
def init_scope(main_domain: str = Form(...), in_scope: Optional[str] = Form(""), output_dir: Optional[str] = Form("output")):
    outdir = ROOT / output_dir
    outdir.mkdir(exist_ok=True, parents=True)

    scope = {
        "main_domain": main_domain.strip(),
        "in_scope": [d.strip() for d in in_scope.splitlines() if d.strip()],
        "passive": {}
    }

    subs = fetch_crtsh_subdomains(scope["main_domain"])
    scope["passive"]["crtsh_subdomains"] = sorted(subs)

    scope_file = outdir / f"{scope['main_domain']}_scope.json"
    scope_file.write_text(json.dumps(scope, indent=2))

    message = f"Scope saved to {scope_file.name} — {len(subs)} subdomains found."
    scopes = sorted(outdir.glob("*_scope.json"))
    return render("home.html", scopes=[p.name for p in scopes], message=message, results=None)

@app.post("/check-live", response_class=HTMLResponse)
def check_live(scope_file: str = Form(...), output_dir: Optional[str] = Form("output"), workers: int = Form(4)):
    outdir = ROOT / output_dir
    sfile = outdir / scope_file
    if not sfile.exists():
        return render("home.html", scopes=[p.name for p in outdir.glob("*_scope.json")], message="Scope file not found.", results=None)

    scope = json.loads(sfile.read_text())
    subs: List[str] = scope.get("passive", {}).get("crtsh_subdomains", [])
    if not subs:
        return render("home.html", scopes=[p.name for p in outdir.glob("*_scope.json")], message="No subdomains in scope file.", results=None)

    results = check_hosts(subs, max_workers=int(workers))
    results_file = outdir / f"{scope['main_domain']}_livecheck.json"
    results_file.write_text(json.dumps(results, indent=2))

    # show a small subset in the UI (first 50 rows) to keep it snappy
    view = results[:50]
    message = f"Live-check done — saved to {results_file.name} (showing {len(view)}/{len(results)} rows)"
    scopes = sorted(outdir.glob("*_scope.json"))
    return render("home.html", scopes=[p.name for p in scopes], message=message, results=view)