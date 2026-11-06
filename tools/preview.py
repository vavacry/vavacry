"""Aperçu local du README rendu par l'API Markdown de GitHub, en clair et en sombre."""
import json
import pathlib
import subprocess

root = pathlib.Path(__file__).resolve().parent.parent
out = root.parent / "preview"
out.mkdir(exist_ok=True)
md = (root / "README.md").read_text(encoding="utf-8")
html = subprocess.run(["gh", "api", "markdown", "--input", "-"],
                      input=json.dumps({"text": md, "mode": "markdown"}).encode(),
                      capture_output=True, check=True).stdout.decode("utf-8")
html = html.replace('srcset="assets/', 'srcset="../vavacry/assets/').replace('src="assets/', 'src="../vavacry/assets/')

for theme, bg, fg, bd, a in [("light", "#ffffff", "#1f2328", "#d1d9e0", "#0969da"),
                             ("dark", "#0d1117", "#f0f6fc", "#3d444d", "#4493f8")]:
    body = html
    if theme == "dark":
        body = body.replace("-light.svg", "-dark.svg")
    page = f"""<!doctype html><html><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>Aperçu {theme}</title><style>
body{{margin:0;background:{bg};color:{fg};font:16px/1.5 -apple-system,'Segoe UI',Helvetica,Arial,sans-serif}}
.box{{max-width:896px;margin:24px auto;border:1px solid {bd};border-radius:6px;padding:24px}}
.hd{{font-size:12px;font-family:monospace;margin-bottom:16px}} a{{color:{a};text-decoration:none}} img{{max-width:100%}} p{{margin:0 0 16px}}
@media (max-width:600px){{.box{{margin:8px;padding:16px}}}}
</style></head><body><div class=box><div class=hd>vavacry / README.md</div><article>{body}</article></div></body></html>"""
    (out / f"{theme}.html").write_text(page, encoding="utf-8")
print("ok")
