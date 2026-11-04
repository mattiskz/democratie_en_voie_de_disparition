#!/usr/bin/env python3
"""Exporte le fichier Excel de vérification de la carte (une ligne par fait).
Usage : python3 tools/exporter_verification.py SORTIE.xlsx
Les libellés des infractions et des règles sont lus dans src/carte_template.html."""
import json, os, re, sys
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.worksheet.datavalidation import DataValidation

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
C = json.load(open(os.path.join(ROOT, 'src', 'carte.json')))
D = {x['id']: x for x in json.load(open(os.path.join(ROOT, 'src', 'carte_drive.json')))}
T = open(os.path.join(ROOT, 'src', 'carte_template.html')).read()

def dico(debut, fin):
    a, b = T.index(debut), T.index(fin)
    return {k: (l, r) for k, l, r in re.findall(r'^\s*"([^"]+)":\s*\["([^"]+)",\s*"([^"]+)"', T[a:b], re.M)}
INF = dico('const INFRACTIONS', '/* Règles d')
REG = dico('const REGLES', 'const SEMAINES')
SEM = {int(k): v for k, v in re.findall(r'(\d):"(Semaine[^"]+)"', T)}

vids = {f[:-4] for f in os.listdir(os.path.join(ROOT, 'public', 'carte', 'v')) if f.endswith('.mp4')}
def statut(c):
    if c['k'] == "Article (PDF)": return "Article PDF (pas de floutage)"
    if c['k'] == "Image": return "En ligne (aucun visage)"
    return "Floutée, en ligne" if c['id'] in vids else "À m'envoyer (trop lourde pour le connecteur)"

F = lambda **k: Font(name="Arial", **k)
J = PatternFill("solid", fgColor="FFF2B3"); H = PatternFill("solid", fgColor="1F2937")
thin = Side(style="thin", color="D5DAE2"); B = Border(left=thin, right=thin, top=thin, bottom=thin)
wb = Workbook()

m = wb.active; m.title = "Mode d'emploi"
lignes = [("Vérification de la carte des violences policières", True), ("", False),
 ("Chaque ligne de l'onglet « Faits » correspond à un fichier du dossier Drive « VIOLENCES POLICIÈRES ».", False),
 ("Les colonnes grises ont été déduites du nom du fichier : vérifie-les.", False),
 ("Les colonnes JAUNES sont à remplir ou à corriger. Laisse une case vide si tu n'as pas l'information.", False), ("", False),
 ("Colonnes à remplir", True),
 ("Adresse précise : numéro et rue, ou carrefour (ex. « 12 rue Bergère » ou « angle rue Bergère / rue du Faubourg-Montmartre »).", False),
 ("Jour : le jour du fait (ex. 17/10).  Heure : facultative (ex. 15h40).", False),
 ("Titre corrigé : seulement si le titre déduit ne convient pas.", False),
 ("Forces de l'ordre : choisis dans la liste ; s'il y en a plusieurs, écris-les séparées par une virgule (ex. CRS, BRAV-M).", False),
 ("Infractions OK ? : Oui si les infractions présumées te conviennent, sinon « À modifier » et précise dans Commentaire.", False),
 ("Publier ? : Non pour retirer un fait de la carte.", False),
 ("Commentaire : tout ce qui doit changer (description, source, visage resté visible dans la vidéo floutée, etc.).", False), ("", False),
 ("Exemple de ligne remplie", True)]
for i, (t, b) in enumerate(lignes, 1):
    m.cell(i, 1, t).font = F(bold=b, size=14 if i == 1 else 11)
ex = [("Cote", "VP-023"), ("Fichier Drive", "RUE_BERGERE_MATRAQUE"), ("Adresse précise", "12 rue Bergère"), ("Jour", "17/10"),
      ("Heure", "15h40"), ("Forces de l'ordre", "CRS"), ("Infractions OK ?", "Oui"), ("Publier ?", "Oui"),
      ("Commentaire", "Manifestant au sol frappé à plusieurs reprises ; visage d'un passant encore visible à 0:12.")]
r = len(lignes) + 1
for k, v in ex:
    m.cell(r, 1, k).font = F(bold=True); c = m.cell(r, 2, v); c.font = F(); c.fill = J; r += 1
m.cell(r + 1, 1, "Les onglets « Infractions » et « Règles » détaillent les références utilisées.").font = F(italic=True, color="5B6474")
m.column_dimensions['A'].width = 24; m.column_dimensions['B'].width = 95

s = wb.create_sheet("Faits")
cols = [("Cote", 9, 0), ("Fichier Drive (titre de la vidéo)", 42, 0), ("Semaine", 16, 0), ("Ville", 15, 0), ("Lieu déduit", 30, 0),
        ("Adresse précise", 30, 1), ("Jour", 8, 1), ("Heure", 8, 1), ("Titre affiché (déduit)", 40, 0), ("Titre corrigé", 30, 1),
        ("Types de violence (déduits)", 26, 0), ("Forces de l'ordre", 20, 1), ("Infractions présumées (déduites)", 55, 0),
        ("Infractions OK ?", 13, 1), ("Règles en cause (déduites)", 45, 0), ("Source", 24, 0), ("Images choquantes", 11, 0),
        ("Vidéo sur le site", 24, 0), ("Publier ?", 10, 1), ("Commentaire", 45, 1)]
for j, (h, w, e) in enumerate(cols, 1):
    c = s.cell(1, j, h); c.font = F(bold=True, color="FFFFFF"); c.fill = H; c.border = B
    c.alignment = Alignment(wrap_text=True, vertical="center"); s.column_dimensions[c.column_letter].width = w
s.row_dimensions[1].height = 34
for i, c in enumerate(C, 2):
    forces = [f for f in c.get('forces', []) if f != "Non précisée"]
    vals = [c['cote'], c['fn'], SEM.get(c['sem'], ""), c['ville'] or "Inconnue", c['adresse'] or "Inconnu", None, None, None,
            c['t'], None, ", ".join(c['violences']), ", ".join(forces) or None,
            "\n".join(f"{INF[k][0]} ({INF[k][1]})" if k in INF else k for k in c['infractions']), None,
            "\n".join(f"{REG[k][0]} ({REG[k][1]})" if k in REG else k for k in c['regles']),
            c['s'] or "—", "Oui" if c['tw'] else "", statut(c), "Oui", None]
    for j, v in enumerate(vals, 1):
        x = s.cell(i, j, v); x.font = F(size=10); x.alignment = Alignment(wrap_text=True, vertical="top"); x.border = B
        if cols[j - 1][2]: x.fill = J
n = len(C) + 1
s.freeze_panes = "C2"; s.auto_filter.ref = f"A1:T{n}"
dv = DataValidation(type="list", formula1='"CRS,BRAV-M,BAC,Police nationale,Gendarmerie mobile,Police municipale,Non identifiable"', allow_blank=True)
dv.showErrorMessage = False; s.add_data_validation(dv); dv.add(f"L2:L{n}")
d2 = DataValidation(type="list", formula1='"Oui,À modifier"', allow_blank=True); s.add_data_validation(d2); d2.add(f"N2:N{n}")
d3 = DataValidation(type="list", formula1='"Oui,Non"', allow_blank=True); s.add_data_validation(d3); d3.add(f"S2:S{n}")

for nom, dic, h in (("Infractions", INF, "Infraction présumée"), ("Règles", REG, "Règle d'intervention")):
    t = wb.create_sheet(nom)
    for j, v in enumerate(("Code", h, "Référence"), 1):
        c = t.cell(1, j, v); c.font = F(bold=True, color="FFFFFF"); c.fill = H
    for i, (k, (l, ref)) in enumerate(dic.items(), 2):
        t.cell(i, 1, k).font = F(); t.cell(i, 2, l).font = F(); t.cell(i, 3, ref).font = F()
    t.column_dimensions['A'].width = 14; t.column_dimensions['B'].width = 80; t.column_dimensions['C'].width = 55
wb.active = 1
wb.save(sys.argv[1])
print(len(C), "faits exportés")
