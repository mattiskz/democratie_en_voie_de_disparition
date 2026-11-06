# Régénère les images de partage (public/og/*.png). Lancer : python3 -m http.server 8765 -d public &  puis  python3 tools/images_partage.py
from playwright.sync_api import sync_playwright
import pathlib
PUB=pathlib.Path(__file__).resolve().parent.parent/'public'  # servir public/ sur le port 8765 avant de lancer
base='''<!doctype html><html><head><meta charset="utf-8"><link rel="stylesheet" href="/f/fonts.css"><style>
:root{--bg:#eef0f3;--ink:#111827;--red:#c8102e;--muted:#5b6474;--display:"Archivo",sans-serif;--mono:"IBM Plex Mono",monospace}
html,body{margin:0;width:1200px;height:630px;background:var(--bg);overflow:hidden}
.c{box-sizing:border-box;width:1200px;height:630px;padding:56px 72px 48px;display:flex;flex-direction:column;justify-content:space-between;border-top:14px solid var(--red)}
.k{font-family:var(--mono);font-size:24px;letter-spacing:.08em;text-transform:uppercase;color:var(--red)}
h1{font-family:var(--display);font-stretch:68%;font-weight:900;text-transform:uppercase;line-height:1.02;margin:0;color:var(--ink);font-size:%SIZE%px}
h1 span{color:var(--red)}
.p{font-family:"Source Serif 4",Georgia,serif;font-size:30px;line-height:1.3;color:var(--ink);max-width:960px;margin:0}
.u{font-family:var(--mono);font-size:22px;color:var(--muted);display:flex;justify-content:space-between}
</style></head><body><div class="c"><div class="k">%KICK%</div><h1>%TITLE%</h1><p class="p">%TXT%</p><div class="u"><span>democratie-en-voie-de-disparition.fr</span><span>%PATH%</span></div></div></body></html>'''
pages={
 'dossier':dict(SIZE=124,KICK='Depuis le 17 octobre 2026',TITLE='Démocratie en voie <span>de disparition</span>',TXT='Violences policières, mesures antidémocratiques et déclarations haineuses, répertoriées et sourcées.',PATH='Le dossier'),
 'carte':dict(SIZE=110,KICK='Démocratie en voie de disparition',TITLE='Carte des violences <span>policières</span>',TXT='Chaque fait filmé depuis le 17 octobre, placé à la rue où il s’est produit. Unités en cause, infractions présumées.',PATH='/carte'),
}
for name,v in pages.items():
    h=base
    for k,val in v.items(): h=h.replace('%'+k+'%',str(val))
    (PUB/f'og_{name}.html').write_text(h)
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(viewport={'width':1200,'height':630})
    for name in pages:
        pg.goto(f'http://localhost:8765/og_{name}.html'); pg.wait_for_timeout(800)
        pg.screenshot(path=str(PUB/'og'/f'{name}.png'))
        (PUB/f'og_{name}.html').unlink()
    b.close()
