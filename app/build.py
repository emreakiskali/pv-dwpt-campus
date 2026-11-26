"""Assemble the single-file interactive app (docs/index.html) from app/.

Usage (from the repository root):  python app/export_data.py && python app/build.py
docs/ can be served with GitHub Pages (Settings > Pages > Deploy from branch: main, folder /docs).
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A = lambda n: open(os.path.join(ROOT, "app", n), encoding="utf-8").read()
model = A("model.js").replace("if (typeof module !== 'undefined') module.exports = { buildCalendar, vehicles, simulate };", "")
page = A("template.html").replace("__DATA__", A("data.json")).replace("__CAMPUS__", A("campus.json")).replace("__MODEL__", model)
html = ("<!doctype html>\n<html lang=\"tr\">\n<head>\n<meta charset=\"utf-8\">\n"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1, viewport-fit=cover\">\n"
        "</head>\n<body>\n" + page + "\n</body>\n</html>\n")
os.makedirs(os.path.join(ROOT, "docs"), exist_ok=True)
with open(os.path.join(ROOT, "docs", "index.html"), "w", encoding="utf-8") as f:
    f.write(html)
print("wrote docs/index.html", len(html) // 1024, "KB")
