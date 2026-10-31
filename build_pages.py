#!/usr/bin/env python3
"""Build the two positioning pages from template + data.

  artifact/<cat>.html  page body for publishing as a Claude artifact (the
                       Artifact tool adds the document skeleton itself)
  site/<cat>.html      the same page as a complete HTML document (GitHub Pages
                       or local viewing)

Usage: python build_pages.py
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent

CONFIGS = {
    "noncomm": {
        "title": "COT Non-commercial Positioning",
        "category": "noncomm",
        "category_label": "Non-commercial (Legacy report)",
        "category_note": ("Non-commercial = all reportable traders not classified as commercial hedgers. "
                          "For financial contracts this includes asset managers as well as leveraged funds."),
    },
    "spec": {
        "title": "COT Speculator Positioning",
        "category": "spec",
        "category_label": "Leveraged funds (TFF) / Managed money (Disaggregated)",
        "category_note": ("Leveraged funds from the Traders in Financial Futures report for financial contracts "
                          "and managed money from the Disaggregated report for gold, copper and WTI: the "
                          "narrowest speculator definitions the CFTC publishes."),
    },
}

SKELETON_HEAD = ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
                 '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
                 '<style>:root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}'
                 'body{margin:0;font:14px system-ui,sans-serif}img{max-width:100%}[hidden]{display:none!important}</style>'
                 '</head><body>')
SKELETON_TAIL = '</body></html>'


def embed_json(obj):
    # Keep JSON safe inside a <script> block.
    return json.dumps(obj, separators=(",", ":")).replace("</", "<\\/")


def main():
    template = (HERE / "cot_live.html").read_text(encoding="utf-8")
    universe = json.loads((HERE / "universe.json").read_text(encoding="utf-8"))
    (HERE / "artifact").mkdir(exist_ok=True)
    (HERE / "site").mkdir(exist_ok=True)
    for cat, cfg in CONFIGS.items():
        data_path = HERE / "data" / f"{cat}.json"
        if not data_path.exists():
            print(f"no data for {cat} ({data_path}); skipped")
            continue
        data = json.loads(data_path.read_text(encoding="utf-8"))
        config = dict(cfg, universe=universe, report=data["report"])
        page = (template
                .replace("<title>COT Positioning</title>", f"<title>{cfg['title']}</title>")
                .replace("/*__CONFIG__*/{}", embed_json(config))
                .replace("/*__DATA__*/{}", embed_json(data)))
        (HERE / "artifact" / f"{cat}.html").write_text(page, encoding="utf-8")
        (HERE / "site" / f"{cat}.html").write_text(SKELETON_HEAD + page + SKELETON_TAIL, encoding="utf-8")
        print(f"built {cat}: {len(page) // 1024} KB, as of {data['as_of']}")


if __name__ == "__main__":
    main()
