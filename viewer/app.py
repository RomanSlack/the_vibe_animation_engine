#!/usr/bin/env python3
"""
Minimal Flask viewer for animation_gif_engine projects.

Browse every project's rendered GIFs (and montage) in one page so you can eyeball
iterations without opening files by hand. Read-only — it never builds or edits.

Run:
    python3 viewer/app.py            # http://localhost:8015
    PORT=8020 python3 viewer/app.py  # custom port

It auto-discovers projects/<name>/out/*.gif, so just re-run a build and refresh.
"""
import os, json, glob, time
from flask import Flask, send_file, abort, render_template_string

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECTS = os.path.join(ROOT, "projects")
PORT = int(os.environ.get("PORT", 8015))

app = Flask(__name__)


def list_projects():
    out = []
    for cfg_path in sorted(glob.glob(os.path.join(PROJECTS, "*", "project.json"))):
        pdir = os.path.dirname(cfg_path)
        name = os.path.basename(pdir)
        try:
            cfg = json.load(open(cfg_path))
        except Exception:
            cfg = {}
        gifs = sorted(glob.glob(os.path.join(pdir, "out", "*.gif")))
        montage = os.path.join(pdir, "out", "_montage.png")
        manifest = os.path.join(pdir, "manifest.json")
        built = None
        if os.path.exists(manifest):
            try:
                built = json.load(open(manifest)).get("builtAt")
            except Exception:
                pass
        out.append({
            "name": name,
            "desc": cfg.get("description", ""),
            "word": cfg.get("source", {}).get("word", ""),
            "built": built,
            "gifs": [{"name": os.path.basename(g),
                      "kb": round(os.path.getsize(g) / 1024),
                      "mtime": os.path.getmtime(g)} for g in gifs],
            "has_montage": os.path.exists(montage),
        })
    return out


@app.route("/")
def index():
    return render_template_string(PAGE, projects=list_projects())


@app.route("/asset/<project>/<path:fname>")
def asset(project, fname):
    # only serve files from a project's out/ dir
    p = os.path.normpath(os.path.join(PROJECTS, project, "out", fname))
    if not p.startswith(os.path.join(PROJECTS, project, "out")) or not os.path.exists(p):
        abort(404)
    return send_file(p)


PAGE = """<!doctype html><html><head><meta charset=utf-8>
<title>gif engine · viewer</title>
<meta name=viewport content="width=device-width,initial-scale=1">
<style>
 :root{--bg:#0d0d12;--card:#16161d;--mut:#7a7a88;--fg:#e8e8ef;--accent:#6ea8ff}
 *{box-sizing:border-box} body{margin:0;background:var(--bg);color:var(--fg);
   font:14px/1.5 system-ui,sans-serif} header{padding:18px 22px;border-bottom:1px solid #23232d}
 h1{font-size:15px;margin:0;letter-spacing:.04em} .sub{color:var(--mut);font-size:12px;margin-top:3px}
 main{padding:18px 22px;max-width:1100px;margin:0 auto}
 .proj{margin:0 0 30px} .ptitle{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap}
 .ptitle b{font-size:15px} .ptitle .desc{color:var(--mut);font-size:12px}
 .meta{color:var(--mut);font-size:11px;margin:2px 0 12px}
 .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:14px}
 .card{background:var(--card);border:1px solid #23232d;border-radius:10px;overflow:hidden}
 .card .imgwrap{background:
     conic-gradient(#23232d 25%,#1a1a22 0 50%,#23232d 0 75%,#1a1a22 0) 0 0/22px 22px;
   display:flex;align-items:center;justify-content:center;min-height:150px;padding:8px}
 .card img{max-width:100%;height:auto;display:block}
 .card .cap{padding:8px 10px;font-size:12px;display:flex;justify-content:space-between;gap:8px}
 .card .cap a{color:var(--accent);text-decoration:none} .card .cap .kb{color:var(--mut)}
 .montage img{max-width:100%;border:1px solid #23232d;border-radius:10px;margin-top:6px}
 details{margin-top:8px} summary{cursor:pointer;color:var(--mut);font-size:12px}
 .empty{color:var(--mut);font-size:12px;padding:8px 0}
 code{background:#23232d;padding:1px 5px;border-radius:4px}
</style></head><body>
<header><h1>animation_gif_engine · viewer</h1>
 <div class=sub>read-only. build with <code>node engine/engine.js build projects/&lt;name&gt;</code>, then refresh.</div>
</header><main>
{% for p in projects %}
 <section class=proj>
  <div class=ptitle><b>{{p.name}}</b>{% if p.desc %}<span class=desc>{{p.desc}}</span>{% endif %}</div>
  <div class=meta>word “{{p.word}}” · {{p.gifs|length}} gif(s){% if p.built %} · built {{p.built}}{% endif %}</div>
  {% if p.gifs %}
   <div class=grid>
   {% for g in p.gifs %}
    <div class=card>
     <div class=imgwrap><img src="/asset/{{p.name}}/{{g.name}}" loading=lazy></div>
     <div class=cap><a href="/asset/{{p.name}}/{{g.name}}" target=_blank>{{g.name}}</a><span class=kb>{{g.kb}} KB</span></div>
    </div>
   {% endfor %}
   </div>
  {% else %}<div class=empty>no gifs yet — run a build.</div>{% endif %}
  {% if p.has_montage %}
   <details class=montage><summary>montage (frame grid)</summary>
    <img src="/asset/{{p.name}}/_montage.png" loading=lazy></details>
  {% endif %}
 </section>
{% else %}
 <p class=empty>No projects found under <code>projects/</code>.</p>
{% endfor %}
</main></body></html>"""


if __name__ == "__main__":
    print(f"  gif engine viewer → http://localhost:{PORT}  (Ctrl-C to stop)")
    app.run(host="0.0.0.0", port=PORT, debug=False)
