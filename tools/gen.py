"""Génère les SVG animés du profil GitHub vavacry (thèmes clair et sombre).

Usage : python tools/gen.py <dossier_des_polices>
Polices : Archivo et JetBrains Mono (SIL OFL 1.1), sous-ensemble embarqué dans chaque SVG.
"""
import base64
import io
import sys
from pathlib import Path
from xml.sax.saxutils import escape

from fontTools import subset
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets"
FONT_DIR = Path(sys.argv[1])

FONTS = {
    "D": ("archivo-display.woff2", "800"),   # titres, condensé
    "T": ("archivo-text.woff2", "400 600"),  # texte courant
    "M": ("jetbrains-mono.woff2", "400 700"),  # labels, code
}
_tt = {k: TTFont(FONT_DIR / f) for k, (f, _) in FONTS.items()}
_cmap = {k: t.getBestCmap() for k, t in _tt.items()}

THEMES = {
    "dark": dict(
        bg="#0b0b0c", panel="#121214", panel2="#1b1b1f", line="#2a2a30", line2="#3d3d45",
        ink="#edece6", mute="#a3a2a9", dim="#85848c", blue="#3a3aff", bluet="#9090ff",
        onblue="#ffffff", ok="#4af626", grid="#2a2a30", shadow="#3a3aff",
    ),
    "light": dict(
        bg="#f4f3ee", panel="#ffffff", panel2="#ecebe4", line="#d6d5cc", line2="#bdbcb2",
        ink="#0b0b0c", mute="#55545b", dim="#77767d", blue="#3a3aff", bluet="#2b2bd9",
        onblue="#ffffff", ok="#1d9a07", grid="#dcdbd2", shadow="#0b0b0c",
    ),
}

EASE = "cubic-bezier(0.16, 1, 0.3, 1)"


def width(font, text, size, tracking=0.0):
    t = _tt[font]
    upm = t["head"].unitsPerEm
    hmtx = t["hmtx"]
    total = 0
    for ch in text:
        g = _cmap[font].get(ord(ch))
        if g is None:
            raise SystemExit(f"glyphe absent dans {font}: {ch!r} ({text!r})")
        total += hmtx[g][0]
    return total * size / upm + tracking * len(text)


class Svg:
    def __init__(self, w, h, theme, title):
        self.w, self.h, self.c = w, h, THEMES[theme]
        self.title = title
        self.used = {k: set() for k in FONTS}
        self.css = []
        self.defs = []
        self.body = []

    def text(self, font, s, x, y, size, fill, weight=None, tracking=0, cls="", anchor="start", extra=""):
        self.used[font].update(s)
        w = f' font-weight="{weight}"' if weight else ""
        ls = f' letter-spacing="{tracking}"' if tracking else ""
        c = f' class="{cls}"' if cls else ""
        a = f' text-anchor="{anchor}"' if anchor != "start" else ""
        return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{font}" font-size="{size}" fill="{fill}"'
                f'{w}{ls}{a}{c}{extra}>{escape(s)}</text>')

    def add(self, *parts):
        self.body.extend(parts)

    def render(self):
        faces = []
        for k, chars in self.used.items():
            if not chars:
                continue
            fname, weight = FONTS[k]
            opts = subset.Options()
            opts.flavor = "woff2"
            opts.layout_features = ["kern", "liga"]
            opts.name_IDs = ["*"]
            opts.notdef_outline = True
            font = TTFont(FONT_DIR / fname)
            sub = subset.Subsetter(opts)
            sub.populate(text="".join(sorted(chars)) + " ")
            sub.subset(font)
            buf = io.BytesIO()
            font.flavor = "woff2"
            font.save(buf)
            b64 = base64.b64encode(buf.getvalue()).decode()
            faces.append(f"@font-face{{font-family:{k};font-weight:{weight};"
                         f"src:url(data:font/woff2;base64,{b64}) format('woff2')}}")
        css = "\n".join(faces + self.css + [
            "@media (prefers-reduced-motion: reduce){*{animation:none!important}}",
        ])
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" '
                f'viewBox="0 0 {self.w} {self.h}" role="img" aria-label="{escape(self.title)}">'
                f"<title>{escape(self.title)}</title><style>{css}</style>"
                f"<defs>{''.join(self.defs)}</defs>{''.join(self.body)}</svg>")


# ------------------------------------------------------------------ pictos (pas de glyphes)

def arrow(x, y, s, color, sw=2.4):
    """Flèche → dont la pointe est en (x+s, y)."""
    h = s * 0.38
    return (f'<path d="M{x:.1f} {y:.1f}H{x+s:.1f}M{x+s-h:.1f} {y-h:.1f}L{x+s:.1f} {y:.1f}L{x+s-h:.1f} {y+h:.1f}" '
            f'fill="none" stroke="{color}" stroke-width="{sw}" stroke-linecap="square"/>')


def check(x, y, s, color, sw=2.2):
    return (f'<path d="M{x:.1f} {y+s*0.55:.1f}L{x+s*0.38:.1f} {y+s*0.9:.1f}L{x+s:.1f} {y+s*0.1:.1f}" '
            f'fill="none" stroke="{color}" stroke-width="{sw}" stroke-linecap="square"/>')


def live_dot(x, y, c, delay=0):
    return (f'<circle cx="{x}" cy="{y}" r="9" fill="none" stroke="{c["ok"]}" stroke-width="1.5" class="ping" '
            f'style="animation-delay:{delay}s"/><circle cx="{x}" cy="{y}" r="4" fill="{c["ok"]}"/>')


PING_CSS = (".ping{transform-box:fill-box;transform-origin:center;animation:ping 2.2s ease-out infinite}"
            "@keyframes ping{0%{transform:scale(.4);opacity:.9}80%,100%{transform:scale(1.6);opacity:0}}")


def grid_pattern(svg, pid, step=24):
    c = svg.c
    svg.defs.append(
        f'<pattern id="{pid}" width="{step}" height="{step}" patternUnits="userSpaceOnUse">'
        f'<path d="M{step} 0V{step}H0" fill="none" stroke="{c["grid"]}" stroke-width="1"/></pattern>')


# ------------------------------------------------------------------ 1. hero

def hero(theme):
    W, H = 900, 400
    s = Svg(W, H, theme, "vavacry : sites et outils web, de l'idée à la mise en ligne")
    c = s.c
    grid_pattern(s, "g")
    s.defs.append('<linearGradient id="fade" x1="0" y1="0" x2="0" y2="1">'
                  '<stop offset="0" stop-color="#fff" stop-opacity="1"/>'
                  '<stop offset=".85" stop-color="#fff" stop-opacity="0"/></linearGradient>'
                  f'<mask id="m"><rect width="{W}" height="{H}" fill="url(#fade)"/></mask>'
                  f'<linearGradient id="scan" x1="0" y1="0" x2="0" y2="1">'
                  f'<stop offset="0" stop-color="{c["blue"]}" stop-opacity="0"/>'
                  f'<stop offset="1" stop-color="{c["blue"]}" stop-opacity=".22"/></linearGradient>')
    s.css.append(PING_CSS)
    s.css.append(
        f".draw{{stroke-dasharray:1200;stroke-dashoffset:1200;animation:draw 1.6s {EASE} forwards}}"
        "@keyframes draw{to{stroke-dashoffset:0}}"
        f".rise{{transform:translateY(130px);animation:rise .9s {EASE} forwards}}"
        "@keyframes rise{to{transform:none}}"
        f".fade{{opacity:0;animation:fade .7s {EASE} forwards}}"
        "@keyframes fade{to{opacity:1}}"
        f".bar{{transform-box:fill-box;transform-origin:left;transform:scaleX(0);animation:bar 1s {EASE} 1.35s forwards}}"
        "@keyframes bar{to{transform:none}}"
        ".blink{animation:blink 1s steps(1) infinite}@keyframes blink{50%{opacity:0}}"
        ".scan{animation:scan 7s linear infinite}@keyframes scan{from{transform:translateY(-120px)}to{transform:translateY(400px)}}"
    )
    s.add(f'<rect width="{W}" height="{H}" fill="{c["bg"]}"/>',
          f'<rect width="{W}" height="{H}" fill="url(#g)" mask="url(#m)"/>',
          f'<rect class="scan" width="{W}" height="120" fill="url(#scan)"/>')
    # lignes de construction
    s.add(f'<g stroke="{c["line2"]}" stroke-width="1" fill="none">'
          f'<path class="draw" d="M40 236H{W-40}"/>'
          f'<path class="draw" style="animation-delay:.15s" d="M40 72V330"/>'
          f'<path class="draw" style="animation-delay:.3s" d="M{W-40} 40V360"/></g>')
    # label
    s.add(f'<g class="fade" style="animation-delay:.2s"><rect x="40" y="40" width="12" height="12" fill="{c["blue"]}"/>',
          s.text("M", "VAVACRY · SITES & OUTILS WEB", 62, 51, 13, c["bluet"], weight=600, tracking=2), "</g>")
    # mot géant, lettre par lettre
    word, size, x0, base = "VAVACRY", 132, 40, 222
    s.defs.append(f'<clipPath id="cw"><rect x="0" y="70" width="{W}" height="{base - 70 + 8}"/></clipPath>')
    letters, x = [], x0
    for i, ch in enumerate(word):
        letters.append(f'<g class="rise" style="animation-delay:{0.35 + i * 0.07:.2f}s">'
                       + s.text("D", ch, x, base, size, c["ink"]) + "</g>")
        x += width("D", ch, size)
    s.add(f'<g clip-path="url(#cw)">{"".join(letters)}</g>')
    s.add(f'<rect class="blink" x="{x + 10:.1f}" y="{base - 92}" width="22" height="92" fill="{c["blue"]}"/>')
    s.add(f'<rect class="bar" x="40" y="232" width="{x - 40:.1f}" height="8" fill="{c["blue"]}"/>')
    # sous-titre tapé
    sub = "Je conçois des sites et des outils web, et je les mets en ligne."
    sw = width("T", sub, 22)
    s.css.append(f".type{{animation:type 2.4s steps({len(sub)}) 1.6s both}}@keyframes type{{from{{width:0}}to{{width:{sw + 4:.0f}px}}}}")
    s.defs.append(f'<clipPath id="ct"><rect class="type" x="40" y="258" height="36" width="{sw + 4:.0f}"/></clipPath>')
    s.add(f'<g clip-path="url(#ct)">' + s.text("T", sub, 40, 284, 22, c["mute"], weight=400) + "</g>")
    # barre d'état
    st = [("2 PROJETS EN LIGNE", c["ink"]), ("NEXT.JS · TYPESCRIPT · TAILWIND CSS", c["mute"]), ("GITHUB PAGES", c["mute"])]
    g = [f'<g class="fade" style="animation-delay:3.4s">', live_dot(48, 341, c)]
    x = 66
    for i, (t, col) in enumerate(st):
        if i:
            g.append(f'<rect x="{x + 10:.1f}" y="335" width="1" height="12" fill="{c["line2"]}"/>')
            x += 22
        g.append(s.text("M", t, x, 346, 13, col, weight=500, tracking=1.5))
        x += width("M", t, 13, 1.5)
    g.append("</g>")
    s.add(*g)
    # terminal
    tx, ty, tw, th = 590, 64, 270, 150
    s.add(f'<g class="fade" style="animation-delay:.9s">'
          f'<rect x="{tx + 8}" y="{ty + 8}" width="{tw}" height="{th}" fill="{c["shadow"]}"/>'
          f'<rect x="{tx}" y="{ty}" width="{tw}" height="{th}" fill="{c["panel"]}" stroke="{c["line2"]}"/>'
          f'<rect x="{tx}" y="{ty}" width="{tw}" height="26" fill="{c["panel2"]}" stroke="{c["line2"]}"/>',
          s.text("M", "BUILD", tx + 12, ty + 17, 11, c["mute"], weight=600, tracking=2),
          ''.join(f'<rect x="{tx + tw - 18 - i * 12}" y="{ty + 10}" width="7" height="7" fill="{c["line2"]}"/>' for i in range(3)),
          "</g>")
    rows = [("$ npm run build", c["ink"], None), ("compilé", c["mute"], "ok"),
            ("$ git push", c["ink"], None), ("GitHub Actions", c["mute"], "arrow"), ("en ligne", c["ok"], "ok")]
    cyc = 9.0
    for i, (t, col, icon) in enumerate(rows):
        y = ty + 52 + i * 20
        start = 1.2 + i * 0.55
        on = start / cyc * 100
        s.css.append(f".r{i}{{opacity:0;animation:r{i} {cyc}s {start - 1.2 + 1.2:.2f}s infinite}}"
                     f"@keyframes r{i}{{0%{{opacity:0;transform:translateX(-6px)}}"
                     f"3%,{88 - on * 0.0:.0f}%{{opacity:1;transform:none}}94%,100%{{opacity:0}}}}")
        ic = ""
        tx2 = tx + 14
        if icon == "ok":
            ic = check(tx + 16, y - 10, 10, c["ok"])
            tx2 = tx + 34
        elif icon == "arrow":
            ic = arrow(tx + 15, y - 4, 11, c["bluet"], 2)
            tx2 = tx + 34
        s.add(f'<g class="r{i}">{ic}' + s.text("M", t, tx2, y, 13, col, weight=500) + "</g>")
    s.add(f'<rect class="blink" x="{tx + 14}" y="{ty + 52 + 5 * 20 - 11}" width="8" height="13" fill="{c["bluet"]}"/>')
    s.add(f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" fill="none" stroke="{c["line"]}"/>')
    return s


# ------------------------------------------------------------------ 2. carte 12testeurs

def card_12(theme):
    W, H = 900, 400
    s = Svg(W, H, theme, "12testeurs : Google exige 12 testeurs, on t'en fournit 14. 39 € par app.")
    c = s.c
    grid_pattern(s, "g2", 20)
    s.css.append(PING_CSS)
    s.css.append(
        f".sh{{transform:translate(-10px,-10px);animation:sh .8s {EASE} .2s forwards}}@keyframes sh{{to{{transform:none}}}}"
        f".fade{{opacity:0;animation:fade .7s {EASE} forwards}}@keyframes fade{{to{{opacity:1}}}}"
        f".up{{opacity:0;transform:translateY(14px);animation:up .8s {EASE} forwards}}@keyframes up{{to{{opacity:1;transform:none}}}}"
        f".sweep{{transform-box:fill-box;transform-origin:left;transform:scaleX(0);animation:bar .7s {EASE} 1.1s forwards}}"
        "@keyframes bar{to{transform:none}}"
    )
    cw, ch = W - 12, H - 12
    s.add(f'<rect class="sh" x="10" y="10" width="{cw}" height="{ch}" fill="{c["shadow"]}"/>',
          f'<rect x=".5" y=".5" width="{cw}" height="{ch}" fill="{c["panel"]}" stroke="{c["line2"]}"/>')
    # en-tête
    s.add(f'<g class="fade" style="animation-delay:.3s"><rect x="36" y="34" width="12" height="12" fill="{c["blue"]}"/>',
          s.text("M", "PROJET 01 · 12TESTEURS", 58, 45, 13, c["bluet"], weight=600, tracking=2),
          live_dot(W - 136, 40, c), s.text("M", "EN LIGNE", W - 120, 45, 13, c["ok"], weight=600, tracking=2), "</g>")
    s.add(f'<rect x="36" y="64" width="{cw - 72}" height="1" fill="{c["line"]}"/>')
    # titre
    lines = ["GOOGLE EXIGE", "12 TESTEURS.", "ON T’EN FOURNIT"]
    for i, t in enumerate(lines):
        s.add(f'<g class="up" style="animation-delay:{0.45 + i * 0.1:.2f}s">' + s.text("D", t, 36, 122 + i * 46, 50, c["ink"]) + "</g>")
    lw = width("D", "ON T’EN FOURNIT ", 50)
    nw = width("D", "14.", 50)
    s.add(f'<rect class="sweep" x="{36 + lw - 4:.1f}" y="{122 + 2 * 46 - 40}" width="{nw + 10:.1f}" height="46" fill="{c["blue"]}"/>',
          f'<g class="up" style="animation-delay:.75s">' + s.text("D", "14.", 36 + lw + 1, 122 + 2 * 46, 50, c["onblue"]) + "</g>")
    # texte
    body = [("14 testeurs réels sur de vrais téléphones Android,", c["mute"], 400),
            ("pendant les 14 jours exigés par Google.", c["mute"], 400),
            ("39 € par app. Accès production refusé ? Remboursé.", c["ink"], 600)]
    for i, (t, col, wgt) in enumerate(body):
        s.add(f'<g class="fade" style="animation-delay:{1.2 + i * 0.12:.2f}s">' + s.text("T", t, 36, 266 + i * 26, 17, col, weight=wgt) + "</g>")
    s.add(f'<g class="fade" style="animation-delay:1.7s">'
          + s.text("M", "NEXT.JS 16 · TYPESCRIPT · TAILWIND CSS 4", 36, 358, 12, c["dim"], weight=500, tracking=1.5) + "</g>")
    # fenêtre commande
    wx, wy, ww, wh = 540, 92, 318, 274
    s.add(f'<g class="fade" style="animation-delay:.6s">'
          f'<rect x="{wx}" y="{wy}" width="{ww}" height="{wh}" fill="url(#g2)" stroke="{c["line2"]}"/>'
          f'<rect x="{wx}" y="{wy}" width="{ww}" height="28" fill="{c["panel2"]}" stroke="{c["line2"]}"/>',
          s.text("M", "TA COMMANDE", wx + 14, wy + 19, 11, c["mute"], weight=600, tracking=2),
          ''.join(f'<rect x="{wx + ww - 70 + i * 4}" y="{wy + 10}" width="1.5" height="9" fill="{c["line2"]}" transform="rotate(20 {wx + ww - 70 + i * 4} {wy + 14})"/>' for i in range(12)),
          "</g>")
    # 14 téléphones
    cyc = 10.0
    s.css.append(
        f".ph{{animation:ph {cyc}s infinite}}@keyframes ph{{0%{{fill:transparent}}3%,82%{{fill:{c['blue']}}}90%,100%{{fill:transparent}}}}"
        f".px{{animation:px {cyc}s infinite}}@keyframes px{{0%{{fill:transparent}}3%,82%{{fill:{c['ok']}}}90%,100%{{fill:transparent}}}}"
    )
    pw, phh, gap = 30, 46, 11
    gx = wx + (ww - (7 * pw + 6 * gap)) / 2
    for i in range(14):
        r, col = divmod(i, 7)
        x = gx + col * (pw + gap)
        y = wy + 48 + r * (phh + 14)
        cls = "px" if i >= 12 else "ph"
        stroke = c["ok"] if i >= 12 else c["bluet"]
        s.add(f'<rect class="{cls}" style="animation-delay:{0.9 + i * 0.16:.2f}s" x="{x:.1f}" y="{y}" width="{pw}" height="{phh}" '
              f'rx="5" fill="transparent" stroke="{stroke}" stroke-width="1.6"/>',
              f'<rect x="{x + pw / 2 - 4:.1f}" y="{y + phh - 7}" width="8" height="2" fill="{stroke}" opacity=".7"/>')
    # compteurs 12 / +2 / = 14
    cy = wy + 196
    s.add(f'<g class="fade" style="animation-delay:1.2s">' + s.text("D", "12", wx + 18, cy, 44, c["ink"])
          + s.text("M", "EXIGÉS", wx + 18 + width("D", "12", 44) + 8, cy - 6, 11, c["mute"], weight=600, tracking=1.5) + "</g>")
    x2 = wx + 124
    s.add(f'<g class="fade" style="animation-delay:3.1s">' + s.text("D", "+2", x2, cy, 44, c["ok"])
          + s.text("M", "MARGE", x2 + width("D", "+2", 44) + 8, cy - 6, 11, c["mute"], weight=600, tracking=1.5) + "</g>")
    s.add(f'<g class="fade" style="animation-delay:3.4s">' + s.text("D", "= 14", wx + ww - 18, cy, 44, c["bluet"], anchor="end") + "</g>")
    # barre 14 jours
    by = wy + 222
    s.css.append(f".days{{transform-box:fill-box;transform-origin:left;animation:days {cyc}s linear infinite}}"
                 "@keyframes days{0%,10%{transform:scaleX(0)}80%,88%{transform:scaleX(1)}96%,100%{transform:scaleX(0)}}")
    bx, bw = wx + 18, ww - 36
    s.add(f'<rect x="{bx}" y="{by}" width="{bw}" height="10" fill="none" stroke="{c["line2"]}"/>',
          f'<rect class="days" x="{bx + 2}" y="{by + 2}" width="{bw - 4}" height="6" fill="{c["blue"]}"/>',
          ''.join(f'<rect x="{bx + bw * d / 14:.1f}" y="{by}" width="1" height="10" fill="{c["panel"]}"/>' for d in range(1, 14)),
          s.text("M", "J1", bx, by + 30, 11, c["mute"], weight=600, tracking=1),
          s.text("M", "14 JOURS DE TEST", bx + bw / 2, by + 30, 11, c["ink"], weight=700, tracking=1, anchor="middle"),
          s.text("M", "J14", bx + bw, by + 30, 11, c["mute"], weight=600, tracking=1, anchor="end"))
    return s


# ------------------------------------------------------------------ 3. carte Perso

def card_perso(theme):
    W, H = 900, 390
    s = Svg(W, H, theme, "Perso : un outil personnel pour gérer mes chaînes YouTube via l'API YouTube")
    c = s.c
    s.css.append(PING_CSS)
    s.css.append(
        f".sh{{transform:translate(-10px,-10px);animation:sh .8s {EASE} .2s forwards}}@keyframes sh{{to{{transform:none}}}}"
        f".fade{{opacity:0;animation:fade .7s {EASE} forwards}}@keyframes fade{{to{{opacity:1}}}}"
        f".up{{opacity:0;transform:translateY(14px);animation:up .8s {EASE} forwards}}@keyframes up{{to{{opacity:1;transform:none}}}}"
    )
    cw, ch = W - 12, H - 12
    s.add(f'<rect class="sh" x="10" y="10" width="{cw}" height="{ch}" fill="{c["line2"] if theme == "dark" else c["shadow"]}"/>',
          f'<rect x=".5" y=".5" width="{cw}" height="{ch}" fill="{c["panel"]}" stroke="{c["line2"]}"/>')
    s.add(f'<g class="fade" style="animation-delay:.3s"><rect x="36" y="34" width="12" height="12" fill="{c["blue"]}"/>',
          s.text("M", "PROJET 02 · PERSO", 58, 45, 13, c["bluet"], weight=600, tracking=2),
          live_dot(W - 136, 40, c, .6), s.text("M", "EN LIGNE", W - 120, 45, 13, c["ok"], weight=600, tracking=2), "</g>")
    s.add(f'<rect x="36" y="64" width="{cw - 72}" height="1" fill="{c["line"]}"/>')
    for i, t in enumerate(["MES CHAÎNES YOUTUBE,", "PILOTÉES D’UN SEUL OUTIL."]):
        s.add(f'<g class="up" style="animation-delay:{0.45 + i * 0.1:.2f}s">' + s.text("D", t, 36, 118 + i * 44, 46, c["ink"]) + "</g>")
    s.add(f'<g class="fade" style="animation-delay:.9s">'
          + s.text("T", "Un outil personnel, branché sur l’API YouTube : envoi, statistiques, commentaires.", 36, 202, 17, c["mute"], weight=400) + "</g>")
    # trois modules
    cyc = 6.0
    tiles = ["ENVOI DES VIDÉOS", "STATISTIQUES", "COMMENTAIRES"]
    tw, th, ty = 264, 118, 228
    for i, label in enumerate(tiles):
        x = 36 + i * (tw + 14)
        d = 1.0 + i * 0.15
        g = [f'<g class="up" style="animation-delay:{d:.2f}s">',
             f'<rect x="{x}" y="{ty}" width="{tw}" height="{th}" fill="{c["panel2"]}" stroke="{c["line2"]}"/>',
             s.text("M", f"0{i + 1}", x + 14, ty + 24, 11, c["bluet"], weight=700, tracking=1.5),
             s.text("M", label, x + 40, ty + 24, 11, c["mute"], weight=600, tracking=1.5)]
        if i == 0:  # envoi : flèche qui monte + barre de progression
            s.css.append(f".upl{{transform-box:fill-box;transform-origin:left;animation:upl {cyc}s {EASE} infinite}}"
                         "@keyframes upl{0%{transform:scaleX(0)}55%,80%{transform:scaleX(1)}90%,100%{transform:scaleX(0)}}"
                         f".lift{{animation:lift {cyc / 3}s ease-in-out infinite}}@keyframes lift{{0%,100%{{transform:translateY(4px)}}50%{{transform:translateY(-4px)}}}}")
            ax = x + 30
            g.append(f'<g class="lift"><path d="M{ax} {ty + 82}V{ty + 46}M{ax - 10} {ty + 56}L{ax} {ty + 46}L{ax + 10} {ty + 56}" '
                     f'fill="none" stroke="{c["blue"]}" stroke-width="3" stroke-linecap="square"/></g>')
            g.append(f'<rect x="{ax - 14}" y="{ty + 90}" width="28" height="3" fill="{c["line2"]}"/>')
            g.append(f'<rect x="{x + 66}" y="{ty + 62}" width="{tw - 90}" height="10" fill="none" stroke="{c["line2"]}"/>'
                     f'<rect class="upl" x="{x + 68}" y="{ty + 64}" width="{tw - 94}" height="6" fill="{c["blue"]}"/>')
        elif i == 1:  # stats : barres qui poussent (illustration, sans chiffres)
            hs = [0.35, 0.55, 0.45, 0.75, 0.6, 0.9, 0.7]
            bw = 22
            for j, hh in enumerate(hs):
                bh = 62 * hh
                bx = x + 22 + j * (bw + 9)
                s.css.append(f".b{j}{{transform-box:fill-box;transform-origin:bottom;animation:grow {cyc}s {EASE} {j * 0.12:.2f}s infinite}}")
                g.append(f'<rect class="b{j}" x="{bx}" y="{ty + 102 - bh:.1f}" width="{bw}" height="{bh:.1f}" '
                         f'fill="{c["blue"] if j == 5 else c["line2"]}"/>')
            s.css.append("@keyframes grow{0%{transform:scaleY(.08)}30%,80%{transform:scaleY(1)}95%,100%{transform:scaleY(.08)}}")
            g.append(f'<rect x="{x + 16}" y="{ty + 102}" width="{tw - 32}" height="1" fill="{c["line2"]}"/>')
        else:  # commentaires : bulles qui apparaissent
            for j in range(3):
                by = ty + 40 + j * 24
                ww = [150, 110, 170][j]
                bx = x + 16 + (40 if j == 1 else 0)
                fill = c["blue"] if j == 1 else c["panel"]
                s.css.append(f".c{j}{{opacity:0;animation:pop {cyc}s {EASE} {j * 0.5:.1f}s infinite}}")
                g.append(f'<g class="c{j}"><rect x="{bx}" y="{by}" width="{ww}" height="18" fill="{fill}" stroke="{c["line2"]}"/>'
                         f'<rect x="{bx + 8}" y="{by + 7}" width="{ww * 0.6:.0f}" height="4" fill="{c["onblue"] if j == 1 else c["line2"]}"/></g>')
            s.css.append("@keyframes pop{0%{opacity:0;transform:translateY(6px)}8%,80%{opacity:1;transform:none}92%,100%{opacity:0}}")
        g.append("</g>")
        s.add(*g)
    return s


# ------------------------------------------------------------------ 4. stack défilante

STACK = ["NEXT.JS 16", "REACT 19", "TYPESCRIPT", "TAILWIND CSS 4", "HTML / CSS",
         "GITHUB PAGES", "GITHUB ACTIONS", "API YOUTUBE", "OAUTH"]


def stack(theme):
    W, H = 900, 92
    s = Svg(W, H, theme, "Outils : " + ", ".join(STACK))
    c = s.c
    s.defs.append('<linearGradient id="ef" x1="0" x2="1">'
                  '<stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".08" stop-color="#fff"/>'
                  '<stop offset=".92" stop-color="#fff"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>'
                  f'<mask id="em"><rect width="{W}" height="{H}" fill="url(#ef)"/></mask>')
    chips, x = [], 0
    for i, t in enumerate(STACK):
        tw = width("M", t, 14, 1.5)
        w = tw + 44
        accent = i % 3 == 0
        chips.append(f'<rect x="{x}" y="22" width="{w:.1f}" height="44" fill="{c["panel"]}" stroke="{c["line2"]}"/>'
                     f'<rect x="{x + 14}" y="40" width="8" height="8" fill="{c["blue"] if accent else c["line2"]}"/>'
                     + s.text("M", t, x + 30, 49.5, 14, c["ink"], weight=600, tracking=1.5))
        x += w + 12
    total = x
    s.css.append(f".mq{{animation:mq 26s linear infinite}}@keyframes mq{{to{{transform:translateX(-{total:.1f}px)}}}}")
    row = "".join(chips)
    s.add(f'<g mask="url(#em)"><g class="mq">{row}<g transform="translate({total:.1f} 0)">{row}</g>'
          f'<g transform="translate({2 * total:.1f} 0)">{row}</g></g></g>')
    return s


# ------------------------------------------------------------------ 5. bouton

def cta(theme):
    W, H = 900, 150
    s = Svg(W, H, theme, "Lancer mon test sur 12testeurs, 39 €")
    c = s.c
    label = "LANCER MON TEST · 39 €"
    size = 28
    lw = width("D", label, size, 0.5)
    bw, bh = lw + 120, 70
    bx, by = (W - bw) / 2, 52
    s.defs.append('<linearGradient id="shine" x1="0" x2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/>'
                  '<stop offset=".5" stop-color="#fff" stop-opacity=".35"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>'
                  f'<clipPath id="bc"><rect x="{bx}" y="{by}" width="{bw}" height="{bh}"/></clipPath>')
    s.css.append(
        f".shine{{animation:shine 3.2s {EASE} infinite}}@keyframes shine{{0%{{transform:translateX(-160px)}}45%,100%{{transform:translateX({bw + 160:.0f}px)}}}}"
        ".nudge{animation:nudge 1.6s ease-in-out infinite}@keyframes nudge{0%,100%{transform:none}50%{transform:translateX(6px)}}"
        f".press{{animation:press 3.2s {EASE} infinite}}@keyframes press{{0%,70%,100%{{transform:none}}78%{{transform:translate(5px,5px)}}86%{{transform:none}}}}"
    )
    s.add(s.text("M", "BESOIN DE 12 TESTEURS POUR GOOGLE PLAY ?", W / 2, 30, 13, c["mute"], weight=600, tracking=2, anchor="middle"))
    s.add(f'<rect x="{bx + 8}" y="{by + 8}" width="{bw}" height="{bh}" fill="{c["shadow"] if theme == "light" else c["ink"]}"/>',
          f'<g class="press"><rect x="{bx}" y="{by}" width="{bw}" height="{bh}" fill="{c["blue"]}"/>',
          f'<g clip-path="url(#bc)"><rect class="shine" x="{bx - 120}" y="{by}" width="120" height="{bh}" fill="url(#shine)"/></g>',
          s.text("D", label, bx + 36, by + 46, size, c["onblue"], tracking=0.5),
          f'<g class="nudge">{arrow(bx + 36 + lw + 18, by + bh / 2, 26, c["onblue"], 3.5)}</g></g>')
    return s


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name, fn in [("hero", hero), ("12testeurs", card_12), ("perso", card_perso), ("stack", stack), ("cta", cta)]:
        for theme in THEMES:
            svg = fn(theme).render()
            p = OUT / f"{name}-{theme}.svg"
            p.write_text(svg, encoding="utf-8")
            print(f"{p.name}: {len(svg) / 1024:.1f} Ko")


if __name__ == "__main__":
    main()
