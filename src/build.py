#!/usr/bin/env python3
"""Génère public/index.html (src/entries.json + src/template.html)
et public/carte/index.html (src/carte.json + src/carte_template.html).
Usage : python3 src/build.py JJ/MM/AAAA   (date de mise à jour affichée)
Une vidéo est intégrée si public/v/<id>.mp4 existe (vignette : public/p/<id>.jpg)."""
import json, os, sys, subprocess
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC, PUB = os.path.join(ROOT, 'src'), os.path.join(ROOT, 'public')
E = json.load(open(os.path.join(SRC, 'entries.json')))
changed = False
out = []
for e in E:
    o = {k: v for k, v in e.items() if k != 'fn'}
    vid = os.path.join(PUB, 'v', e['id'] + '.mp4')
    if e['k'] == 'Vidéo' and os.path.exists(vid):
        if not e.get('w'):
            wh = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
                                 'stream=width,height', '-of', 'csv=p=0', vid], capture_output=True, text=True).stdout.strip()
            e['w'], e['h'] = map(int, wh.split(',')[:2]); o['w'], o['h'] = e['w'], e['h']; changed = True
        o['v'] = f"v/{e['id']}.mp4"; o['p'] = f"p/{e['id']}.jpg"
    else:
        o.pop('w', None); o.pop('h', None)
    if e['k'] != 'Vidéo':
        for x in ('pdf', 'png', 'jpg'):
            if os.path.exists(os.path.join(PUB, 'd', f"{e['id']}.{x}")):
                o['doc'] = f"d/{e['id']}.{x}"; break
    out.append(o)
if changed:
    json.dump(E, open(os.path.join(SRC, 'entries.json'), 'w'), ensure_ascii=False, indent=0)
days = [e['d'] for e in E if e['d']]
t = open(os.path.join(SRC, 'template.html')).read()
t = (t.replace('/*DATA*/[]', json.dumps(out, ensure_ascii=False))
      .replace('/*RANGE*/', f"Du 17 au {max(days)} octobre 2026")
      .replace('/*UPDATED*/', sys.argv[1] if len(sys.argv) > 1 else ''))
t = t.replace('<meta name="claude:viewport-fit-sides" content="cover">\n', '')
head = ('<!doctype html>\n<html lang="fr">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        '<meta name="description" content="Violences policières, mesures antidémocratiques et déclarations haineuses depuis le 17 octobre 2026 : tous les éléments répertoriés et sourcés.">\n')
open(os.path.join(PUB, 'index.html'), 'w').write(head + t + '\n</html>\n')
print(len(out), 'éléments,', sum('v' in o for o in out), 'vidéos intégrées')

# ---------- Carte des violences policières (public/carte/) ----------
# Données : src/carte.json. Vidéo floutée attendue dans public/carte/v/<id>.mp4 (voir tools/flouter.py).
C = json.load(open(os.path.join(SRC, 'carte.json')))
cout = []
for c in C:
    o = {k: v for k, v in c.items() if k != 'fn'}
    vid = os.path.join(PUB, 'carte', 'v', c['id'] + '.mp4')
    if c.get('id') and os.path.exists(vid):
        wh = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height',
                             '-of', 'csv=p=0', vid], capture_output=True, text=True).stdout.strip()
        o['vw'], o['vh'] = map(int, wh.split(',')[:2])
        poster = os.path.join(PUB, 'carte', 'p', c['id'] + '.jpg')
        if not os.path.exists(poster):   # vignette tirée de la vidéo DÉJÀ floutée
            subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-ss', '1', '-i', vid, '-frames:v', '1', '-q:v', '5', poster])
        o['v'] = f"/carte/v/{c['id']}.mp4"; o['p'] = f"/carte/p/{c['id']}.jpg"
    elif c.get('id') and os.path.exists(os.path.join(PUB, 'carte', 'i', c['id'] + '.jpg')):
        o['img'] = f"/carte/i/{c['id']}.jpg"
    cout.append(o)
ct = open(os.path.join(SRC, 'carte_template.html')).read()
ct = ct.replace('/*DATA*/[]', json.dumps(cout, ensure_ascii=False)).replace('/*UPDATED*/', sys.argv[1] if len(sys.argv) > 1 else '')
chead = ('<!doctype html>\n<html lang="fr">\n<head>\n<meta charset="utf-8">\n'
         '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
         '<meta name="description" content="Carte des violences policières filmées en France depuis le 17 octobre 2026 : lieu, type de violence, forces de l\'ordre et infractions présumées.">\n')
open(os.path.join(PUB, 'carte', 'index.html'), 'w').write(chead + ct + '\n</html>\n')
print(len(cout), 'faits sur la carte,', sum('v' in o for o in cout), 'vidéos floutées intégrées')
