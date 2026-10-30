#!/usr/bin/env python3
"""Floute en série les vidéos téléchargées depuis Drive et les range dans public/carte/v/<id>.mp4.
Usage : python3 tools/traiter_videos.py DOSSIER_TELECHARGEMENTS DOSSIER_CONTROLE [--travailleurs 2]
Les fichiers téléchargés sont reconnus par leur taille (identique à celle indiquée par Drive).
Les originaux téléchargés ne sont jamais modifiés ; seules les copies floutées vont dans public/."""
import argparse, glob, json, os, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ap = argparse.ArgumentParser(); ap.add_argument("dl"); ap.add_argument("controle"); ap.add_argument("--travailleurs", type=int, default=2)
a = ap.parse_args()
inv = {x['taille']: x for x in json.load(open(os.path.join(ROOT, 'src', 'carte_drive.json')))}
garder = json.load(open(os.path.join(ROOT, 'src', 'carte_garder.json'))) if os.path.exists(os.path.join(ROOT, 'src', 'carte_garder.json')) else {}
os.makedirs(os.path.join(ROOT, 'public', 'carte', 'v'), exist_ok=True)
def un(f):
    x = inv.get(os.path.getsize(f))
    if not x or not x['mime'].startswith('video/'): return None
    out = os.path.join(ROOT, 'public', 'carte', 'v', x['id'] + '.mp4')
    if os.path.exists(out): return None
    verrou = out + '.verrou'
    try: fd = os.open(verrou, os.O_CREAT | os.O_EXCL)   # une seule tâche par vidéo, même si deux traitements tournent
    except FileExistsError: return None
    os.close(fd)
    try: return traiter(f, x, out)
    finally: os.remove(verrou)
def traiter(f, x, out):
    cmd = [sys.executable, os.path.join(ROOT, 'tools', 'flouter.py'), f, out + '.tmp.mp4', '--controle', a.controle]
    if x['fn'] in garder:
        gp = os.path.join(a.controle, x['id'] + '.garder.json'); json.dump(garder[x['fn']], open(gp, 'w')); cmd += ['--garder', gp]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode == 0:
        os.replace(out + '.tmp.mp4', out)
        base = os.path.join(a.controle, os.path.basename(out) + '.tmp.jpg')
        if os.path.exists(base): os.replace(base, os.path.join(a.controle, x['fn'] + '__' + x['id'] + '.jpg'))
        print('OK', x['fn'], flush=True)
    else:
        print('ÉCHEC', x['fn'], r.stderr[-300:].replace('\n', ' '), flush=True)
fichiers = sorted(glob.glob(os.path.join(a.dl, '*')), key=os.path.getsize)
with ThreadPoolExecutor(a.travailleurs) as ex: list(ex.map(un, fichiers))
print('FINI', flush=True)
