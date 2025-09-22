from pathlib import Path
from typing import List, Optional
import json

from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader, select_autoescape
from markdown import markdown

from bbt.recon.crtsh import fetch_crtsh_subdomains
from bbt.recon.http_checker import check_hosts
from bbt.report.generator import render_report
from bbt.config import DEFAULT_OUTPUT_DIR

# --- Paths ---
ROOT = Path(__file__).resolve().parents[3]  # repo root
TEMPLATES_DIR = ROOT / "templates_web"
OUTPUT_DIR = ROOT / "output"
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)

# --- Template environment ---
env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html", "xml"])
)

# --- FastAPI app ---
app = FastAPI(title="Bug Bounty Toolkit")

# static (for CSS/images if we add later)
STATIC_DIR = ROOT / "static"
STATIC_DIR.mkdir(exist_ok=True, parents=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# expose output files for download
app.mount("/artifacts", StaticFiles(directory=str(OUTPUT_DIR)), name="artifacts")


def render(name: str, **ctx) -> HTMLResponse:
    tmpl = env.get_template(name)
    return HTMLResponse(tmpl.render(**ctx))


def generate_report_files(scope: dict, outdir: Path) -> Path:
    """
    Create Markdown and HTML reports. Markdown uses report_template.md.j2;
    HTML is a simple conversion of the generated Markdown.
    """
    md_text = render_report(scope, outdir)
    md_path = outdir / f"{scope['main_domain']}_recon_report.md"
    md_path.write_text(md_text, encoding="utf-8")

    html_text = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Recon Report — {scope['main_domain']}</title>
<style>body{{font-family:system-ui,Segoe UI,Roboto,Arial,sans-serif;max-width:900px;margin:40px auto;line-height:1.5}}
code,pre{{background:#f6f6f6;padding:2px 5px;border-radius:4px}}</style></head>
<body>{markdown(md_text)}</body></html>"""
    html_path = outdir / f"{scope['main_domain']}_recon_report.html"
    html_path.write_text(html_text, encoding="utf-8")

    return md_path


@app.get("/", response_class=HTMLResponse)
def home():
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

    # also refresh the report (may not have live-check data yet; that's ok)
    generate_report_files(scope, outdir)

    message = f"Scope saved to {scope_file.name} — {len(subs)} subdomains found. Report generated."
    scopes = sorted(outdir.glob("*_scope.json"))
    return render("home.html", scopes=[p.name for p in scopes], message=message, results=None)


@app.post("/check-live", response_class=HTMLResponse)
def check_live(scope_file: str = Form(...), output_dir: Optional[str] = Form("output"), workers: int = Form(4)):
    outdir = ROOT / output_dir
    sfile = outdir / scope_file
    if not sfile.exists():
        return render("home.html", scopes=[p.name for p in outdir.glob("*_scope.json")], message="Scope file not found.", results=None)

    scope = json.loads(sfile.read_text(encoding="utf-8"))
    subs: List[str] = scope.get("passive", {}).get("crtsh_subdomains", [])
    if not subs:
        return render("home.html", scopes=[p.name for p in outdir.glob("*_scope.json")], message="No subdomains in scope file.", results=None)

    results = check_hosts(subs, max_workers=int(workers))
    results_file = outdir / f"{scope['main_domain']}_livecheck.json"
    results_file.write_text(json.dumps(results, indent=2))

    # re-generate report so Live Hosts Summary appears
    generate_report_files(scope, outdir)

    view = results[:50]
    message = (
        f"Live-check done — saved to {results_file.name} "
        f"(showing {len(view)}/{len(results)} rows). Report updated."
    )
    scopes = sorted(outdir.glob("*_scope.json"))
    return render("home.html", scopes=[p.name for p in scopes], message=message, results=view)


@app.post("/generate-report", response_class=HTMLResponse)
def generate_report_route(scope_file: str = Form(...), output_dir: str = Form("output")):
    outdir = ROOT / output_dir
    sfile = outdir / scope_file
    if not sfile.exists():
        scopes = sorted(outdir.glob("*_scope.json"))
        return render("home.html", scopes=[p.name for p in scopes],
                      message="Scope file not found.", results=None)

    scope = json.loads(sfile.read_text(encoding="utf-8"))
    md_path = generate_report_files(scope, outdir)
    main = scope.get("main_domain", "report")
    msg = (
        f"Report generated: "
        f"<a href='/artifacts/{main}_recon_report.md' target='_blank'>{main}_recon_report.md</a> "
        f"and <a href='/artifacts/{main}_recon_report.html' target='_blank'>{main}_recon_report.html</a>"
    )
    scopes = sorted(outdir.glob("*_scope.json"))
    return render("home.html", scopes=[p.name for p in scopes], message=msg, results=None)
