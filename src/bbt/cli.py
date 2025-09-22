#!/usr/bin/env python3
import json
import logging
from pathlib import Path
import click

from bbt.recon.crtsh import fetch_crtsh_subdomains
from bbt.report.generator import render_report
from bbt.config import DEFAULT_OUTPUT_DIR

logger = logging.getLogger(__name__)

@click.group()
def cli():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

@cli.command("init-scope")
@click.argument("main_domain")
@click.option("--in-scope", "-s", multiple=True, help="Additional in-scope domains (repeatable).")
@click.option("--out", "-o", default=DEFAULT_OUTPUT_DIR, help="Output directory.")
def init_scope(main_domain, in_scope, out):
    """
    Initialize scope and run passive collection (crt.sh).
    Example:
      bbt init-scope example.com -s sub.example.com -s other.com
    """
    outdir = Path(out)
    outdir.mkdir(parents=True, exist_ok=True)

    scope = {
        "main_domain": main_domain,
        "in_scope": list(in_scope) if in_scope else [],
        "passive": {}
    }

    click.echo(f"Starting passive recon for {main_domain} (this may take a few seconds)...")
    subdomains = fetch_crtsh_subdomains(main_domain)
    scope["passive"]["crtsh_subdomains"] = sorted(subdomains)
    out_file = outdir / f"{main_domain}_scope.json"
    out_file.write_text(json.dumps(scope, indent=2))
    click.echo(f"Scope saved to: {out_file}")

    # Generate report
    report_md = render_report(scope)
    report_file = outdir / f"{main_domain}_recon_report.md"
    report_file.write_text(report_md)
    click.echo(f"Report generated: {report_file}")

@cli.command("check-live")
@click.argument("scope_json", type=click.Path(exists=True))
@click.option("--out", "-o", default=DEFAULT_OUTPUT_DIR, help="Output directory")
@click.option("--workers", "-w", default=6, help="Max concurrent probes (keep low)")
def check_live(scope_json, out, workers):
    """
    Check which subdomains in a saved scope JSON are alive (polite HTTP probes).

    Example:
      python -m bbt.cli check-live output/example.com_scope.json -o output -w 4
    """
    from bbt.recon.http_checker import check_hosts
    outdir = Path(out)
    outdir.mkdir(parents=True, exist_ok=True)

    scope = json.loads(Path(scope_json).read_text())
    subs = scope.get("passive", {}).get("crtsh_subdomains", [])
    if not subs:
        click.echo("No subdomains found in scope file.")
        return

    click.echo(f"Probing {len(subs)} hosts with {workers} workers (polite)...")
    results = check_hosts(subs, max_workers=workers)
    results_file = outdir / f"{scope['main_domain']}_livecheck.json"
    results_file.write_text(json.dumps(results, indent=2))
    click.echo(f"Live-check results saved to {results_file}")

if __name__ == "__main__":
    cli()