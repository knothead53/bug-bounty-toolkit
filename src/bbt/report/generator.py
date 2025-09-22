from pathlib import Path
import datetime
import json
from typing import Dict, List, Optional, Tuple

from jinja2 import Environment, FileSystemLoader, select_autoescape

# Template directory lives at: <repo_root>/templates
TEMPLATE_DIR = Path(__file__).resolve().parents[3] / "templates"

env = Environment(
    loader=FileSystemLoader(str(TEMPLATE_DIR)),
    autoescape=select_autoescape(["html", "xml", "md"]),
    trim_blocks=True,
    lstrip_blocks=True,
)

template = env.get_template("report_template.md.j2")


def _load_livecheck(outdir: Optional[Path], main_domain: str) -> Tuple[Optional[List[Dict]], Dict]:
    """
    Load <main>_livecheck.json from outdir (if present) and compute a summary.
    Returns (raw_results_or_none, summary_dict).
    """
    if not outdir:
        return None, {}

    live_path = outdir / f"{main_domain}_livecheck.json"
    if not live_path.exists():
        return None, {}

    try:
        results = json.loads(live_path.read_text(encoding="utf-8"))
    except Exception:
        return None, {}

    # Alive == has an HTTP status_code (any integer)
    alive = [r for r in results if r.get("status_code") is not None]
    dead = [r for r in results if r.get("status_code") is None]

    # Normalize minimal fields for the template
    normalized_alive = []
    for r in alive:
        normalized_alive.append(
            {
                "host": r.get("host"),
                "status_code": r.get("status_code"),
                "server": r.get("server"),
                "final_url": r.get("final_url"),
            }
        )

    summary = {
        "total_checked": len(results),
        "alive_count": len(alive),
        "dead_count": len(dead),
        "file": live_path.name,
    }
    return normalized_alive, summary


def render_report(scope: dict, outdir: Optional[Path] = None) -> str:
    """
    Render the Markdown report.
    - scope: dict saved by the tool (contains main_domain, in_scope, passive data)
    - outdir: output directory where <main>_livecheck.json may exist (optional)
    """
    main = scope.get("main_domain", "")
    live_hosts, live_summary = _load_livecheck(outdir, main)

    ctx = {
        "generated_at": datetime.datetime.utcnow().isoformat() + "Z",
        "scope": scope,
        "live_hosts": live_hosts,        # list[dict] or None
        "live_summary": live_summary,    # dict or {}
    }
    return template.render(**ctx)