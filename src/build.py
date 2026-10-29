#!/usr/bin/env python3
"""Génère public/index.html à partir de src/entries.json et src/template.html.
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
