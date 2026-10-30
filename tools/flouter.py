#!/usr/bin/env python3
"""Floute les visages d'une vidéo avant publication.

Usage :
  python3 tools/flouter.py ENTREE.mp4 SORTIE.mp4 [--modele yunet.onnx] [--garder garder.json] [--controle dossier/]

- Détecte les visages image par image (modèle YuNet d'OpenCV) et les floute fortement.
- Un visage reste flouté quelques images après sa dernière détection, pour couvrir les ratés.
- --garder : zones à NE PAS flouter (agents des forces de l'ordre), au format
    [{"de": 3.0, "a": 7.5, "zone": [x, y, l, h]}]   (secondes ; zone en fraction de l'image, 0 à 1)
  Un visage dont le centre tombe dans une zone pendant l'intervalle n'est pas flouté.
- --controle : écrit une planche d'images floutées pour vérifier à l'œil qu'aucun visage n'a été manqué.

La détection automatique manque des visages (profil, flou de bougé, très petits, partiellement
cachés) : chaque vidéo doit être revue avant publication.
"""
import argparse, json, os, subprocess, sys
import cv2
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("entree"); ap.add_argument("sortie")
ap.add_argument("--modele", default=os.path.join(os.path.dirname(__file__), "yunet.onnx"))
ap.add_argument("--garder", default=None)
ap.add_argument("--controle", default=None)
ap.add_argument("--seuil", type=float, default=0.45)
ap.add_argument("--crf", type=int, default=26)
args = ap.parse_args()

cap = cv2.VideoCapture(args.entree)
if not cap.isOpened(): sys.exit("Vidéo illisible : " + args.entree)
W, H = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
fps = cap.get(cv2.CAP_PROP_FPS) or 25
n_total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0

# Les petites vidéos sont agrandies pour la détection : les visages lointains y sont minuscules
echelle = max(1.0, min(3.0, 960 / max(W, H)))
DW, DH = int(W * echelle), int(H * echelle)
det = cv2.FaceDetectorYN.create(args.modele, "", (DW, DH), args.seuil, 0.3, 5000)

garder = json.load(open(args.garder)) if args.garder else []
def a_garder(t, cx, cy):
    for g in garder:
        x, y, l, h = g["zone"]
        if g["de"] <= t <= g["a"] and x * W <= cx <= (x + l) * W and y * H <= cy <= (y + h) * H:
            return True
    return False

PERSIST = max(4, int(fps * 0.4))   # images pendant lesquelles un visage disparu reste flouté
pistes = []                        # [x, y, w, h, age]

def floute(img, x, y, w, h):
    m = 0.45                       # marge autour du visage (cheveux, oreilles, menton)
    x0, y0 = int(max(0, x - w * m)), int(max(0, y - h * m * 1.1))
    x1, y1 = int(min(W, x + w * (1 + m))), int(min(H, y + h * (1 + m)))
    if x1 - x0 < 2 or y1 - y0 < 2: return
    roi = img[y0:y1, x0:x1]
    k = max(4, (x1 - x0) // 7)
    pix = cv2.resize(cv2.resize(roi, (max(1, (x1 - x0) // k), max(1, (y1 - y0) // k)), interpolation=cv2.INTER_LINEAR),
                     (x1 - x0, y1 - y0), interpolation=cv2.INTER_NEAREST)
    pix = cv2.GaussianBlur(pix, (0, 0), sigmaX=max(2, (x1 - x0) / 10))
    masque = np.zeros(roi.shape[:2], np.uint8)
    cv2.ellipse(masque, ((x1 - x0) // 2, (y1 - y0) // 2), ((x1 - x0) // 2, (y1 - y0) // 2), 0, 0, 360, 255, -1)
    roi[masque > 0] = pix[masque > 0]

tmp = args.sortie + ".video.mp4"
enc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}",
                        "-r", f"{fps}", "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", str(args.crf),
                        "-pix_fmt", "yuv420p", tmp], stdin=subprocess.PIPE)
controle = []
i = nb_floutes = 0
while True:
    ok, img = cap.read()
    if not ok: break
    t = i / fps
    small = cv2.resize(img, (DW, DH)) if echelle != 1 else img
    _, faces = det.detect(small)
    trouves = []
    if faces is not None:
        for f in faces:
            x, y, w, h = (f[:4] / echelle).tolist()
            trouves.append([x, y, w, h, 0])
    # rattacher aux pistes existantes, garder les pistes récentes non retrouvées
    nouvelles = trouves[:]
    for p in pistes:
        pcx, pcy = p[0] + p[2] / 2, p[1] + p[3] / 2
        if not any(abs((q[0] + q[2] / 2) - pcx) < max(p[2], q[2]) and abs((q[1] + q[3] / 2) - pcy) < max(p[3], q[3]) for q in trouves):
            if p[4] + 1 <= PERSIST: nouvelles.append([p[0], p[1], p[2], p[3], p[4] + 1])
    pistes = nouvelles
    for x, y, w, h, _ in pistes:
        if a_garder(t, x + w / 2, y + h / 2): continue
        floute(img, x, y, w, h); nb_floutes += 1
    if args.controle and i % max(1, int(fps)) == 0:
        controle.append((t, img.copy()))
    enc.stdin.write(img.tobytes())
    i += 1
enc.stdin.close(); enc.wait()

# remettre le son d'origine, rendre la vidéo lisible en streaming
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", tmp, "-i", args.entree, "-map", "0:v:0", "-map", "1:a:0?",
                "-c:v", "copy", "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", "-shortest", args.sortie], check=True)
os.remove(tmp)

if args.controle and controle:
    os.makedirs(args.controle, exist_ok=True)
    base = os.path.splitext(os.path.basename(args.sortie))[0]
    vign = []
    for t, im in controle:
        im = cv2.resize(im, (320, int(320 * H / W)))
        cv2.putText(im, f"{t:5.1f}s", (6, 20), cv2.FONT_HERSHEY_SIMPLEX, .6, (0, 0, 0), 3)
        cv2.putText(im, f"{t:5.1f}s", (6, 20), cv2.FONT_HERSHEY_SIMPLEX, .6, (255, 255, 255), 1)
        vign.append(im)
    cols = 6
    while len(vign) % cols: vign.append(np.zeros_like(vign[0]))
    planche = np.vstack([np.hstack(vign[r:r + cols]) for r in range(0, len(vign), cols)])
    cv2.imwrite(os.path.join(args.controle, base + ".jpg"), planche, [cv2.IMWRITE_JPEG_QUALITY, 80])

print(f"{os.path.basename(args.entree)} : {i} images, {nb_floutes} visages floutés, {os.path.getsize(args.sortie)/1e6:.1f} Mo")
