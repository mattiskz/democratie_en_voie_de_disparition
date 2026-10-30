#!/usr/bin/env python3
"""Prépare src/carte.json à partir de l'inventaire du dossier Drive « VIOLENCES POLICIÈRES ».

  src/carte_drive.json        inventaire des fichiers (id Drive, nom, dossier ville, période, source)
  src/carte_corrections.json  corrections à la main, par nom de fichier (adresse précise, jour, forces, etc.)

Le nom de chaque fichier suit la convention LIEU_FAIT(_FAIT…)(_N) ; INCONNU = lieu inconnu ; TW_ = images choquantes.
Le lieu, les types de violence, les infractions présumées et les règles en cause en sont déduits,
puis les corrections écrasent ce qui a été déduit. Tout ce qui est déduit doit être relu avant publication.
Usage : python3 tools/preparer_carte.py
"""
import json, os, re, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'src')

VILLES = {"PARIS": "Paris", "LYON": "Lyon", "MARSEILLE": "Marseille", "STRASBOURG": "Strasbourg", "NANTES": "Nantes",
          "BESANÇON": "Besançon", "DIJON": "Dijon", "GRENOBLE": "Grenoble", "LE MANS": "Le Mans", "MONTPELLIER": "Montpellier",
          "MULHOUSE": "Mulhouse", "NICE": "Nice", "SAINT-DENIS": "Saint-Denis", "SAINT-ÉTIENNE": "Saint-Étienne",
          "TOULOUSE": "Toulouse", "AMIENS": "Amiens", "BORDEAUX": "Bordeaux", "CAEN": "Caen", "CHAMBÉRY": "Chambéry",
          "CLERMONT FERRAND": "Clermont-Ferrand", "LA ROCHELLE": "La Rochelle", "LILLE": "Lille", "LIMOGES": "Limoges",
          "METZ": "Metz", "NANCY": "Nancy", "ORLÉANS": "Orléans", "PAU": "Pau", "POITIERS": "Poitiers", "REIMS": "Reims",
          "RENNES": "Rennes", "ROUEN": "Rouen", "AUTRES": None}

# Préfixe du nom de fichier → nom de la voie tel qu'affiché (et cherché dans la Base Adresse Nationale)
# Un triplet (nom, lat, lng) fixe l'emplacement quand ce n'est pas une adresse postale.
LIEUX = {
 "RUE_GRESSET": "Rue Gresset", "RUE_BATTANT": "Rue Battant", "RUE_GRANGES": "Rue des Granges",
 "PLACE_BOURSE": "Place de la Bourse", "QUAI_DOUANE": "Quai de la Douane",
 "AVENUE_EDOUARD_MICHELIN": "Avenue Édouard-Michelin", "BOULEVARD_CARNOT": "Boulevard Carnot",
 "BOULEVARD_JEAN_PAIN": "Boulevard Jean-Pain", "PARVIS_ABBÉ_PIERRE": "Parvis Abbé-Pierre",
 "PLACE_GUSTAVE_RIVET": "Place Gustave-Rivet", "PLACE_VERDUN": "Place de Verdun", "RUE_BAS_JARDIN": "Rue du Bas-Jardin",
 "AVENUE_JEAN_JAURES": "Avenue Jean-Jaurès", "PLACE_ANTONIN_PONCET": "Place Antonin-Poncet",
 "PLACE_JEAN_MACÉ": "Place Jean-Macé", "PLACE_MAZAGRAN": "Place Mazagran", "PONT_GUILLOTIÈRE": "Pont de la Guillotière",
 "QUAI_CLAUDE_BERNARD": "Quai Claude-Bernard", "RUE_MADELEINE": "Rue de la Madeleine",
 "RUE_UNIVERSITÉ": "Rue de l'Université", "RUE_ÉMILE_ZOLA": "Rue Émile-Zola",
 "LA_CANEBIÈRE": "La Canebière", "CANEBIÈRE": "La Canebière", "PLACE_JULES_GUESDE": "Place Jules-Guesde",
 "RUE_FORBIN": "Rue Forbin", "RUE_SAINT_FERREOL": "Rue Saint-Ferréol",
 "PLACE_ARMES": "Place d'Armes", "PLACE_RÉPUBLIQUE": "Place de la République",
 "ESPLANADE_CHARLES_DE_GAULLE": "Esplanade Charles-de-Gaulle", "PLACE_COMÉDIE": "Place de la Comédie",
 "PONT_JEAN_ZUCCARELLI": "Pont Jean-Zuccarelli", "RUE_LOGE": "Rue de la Loge", "RUE_MAGUELONE": "Rue Maguelone",
 "RUE_SAUVAGE": "Rue du Sauvage", "RUE_GAMBETTA": "Rue Gambetta",
 "ALLÉE_DUGUAY_TROUIN": "Allée Duguay-Trouin", "ALLÉE_FLESSELLES": "Allée Flesselles",
 "PLACE_COMMERCE": "Place du Commerce", "PONT_ARISTIDE_BRIAND": "Pont Aristide-Briand", "RUE_AFFRE": "Rue Affre",
 "RUE_COUËDIC": "Rue du Couëdic", "RUE_JEAN_FONTAINE": "Rue Jean-de-La-Fontaine",
 "AVENUE_JEAN_MÉDECIN": "Avenue Jean-Médecin", "PROMENADE_ANGLAIS": "Promenade des Anglais",
 "AVENUE_CHAMPS_ELYSÉES": "Avenue des Champs-Élysées", "AVENUE_CHAMPS_ÉLYSÉES": "Avenue des Champs-Élysées",
 "AVENUE_PARMENTIER": "Avenue Parmentier", "AVENUE_ÉMILE_LAURENT": "Avenue Émile-Laurent",
 "BOULEVARD_BONNE_NOUVELLE": "Boulevard de Bonne-Nouvelle", "BOULEVARD_CHARONNE": "Boulevard de Charonne",
 "BOULEVARD_HÔPITAL": "Boulevard de l'Hôpital", "BOULEVARD_MADELEINE": "Boulevard de la Madeleine",
 "BOULEVARD_SOULT": "Boulevard Soult", "COURS_VINCENNES": "Cours de Vincennes",
 "METRO_SAINT_PHILIPPE_DU_ROULE": ("Métro Saint-Philippe-du-Roule", 48.87225, 2.31010),
 "PASSAGE_SAINT_ROCH": "Passage Saint-Roch", "PLACE_HÔTEL_VILLE": "Place de l'Hôtel-de-Ville",
 "PLACE_MADELEINE": "Place de la Madeleine", "PLACE_NATION": "Place de la Nation",
 "PORTE_BERGER": ("Porte Berger, Forum des Halles", 48.86160, 2.34620),
 "RUE_BEAUREPAIRE": "Rue Beaurepaire", "RUE_BERGERE": "Rue Bergère", "RUE_BOURSE": "Rue de la Bourse",
 "RUE_CHATEAU_D'EAU": "Rue du Château-d'Eau", "RUE_DAUNOU": "Rue Daunou", "RUE_DIEU": "Rue Dieu",
 "RUE_DUPHOT": "Rue Duphot", "RUE_FAUBOURG_SAINT_DENIS": "Rue du Faubourg-Saint-Denis",
 "RUE_FAUBOURG_TEMPLE": "Rue du Faubourg-du-Temple", "RUE_FLORÉAL": "Rue Floréal", "RUE_LAFAYETTE": "Rue La Fayette",
 "RUE_PICARDIE": "Rue de Picardie", "RUE_PÉPINIÈRE": "Rue de la Pépinière", "RUE_RAMBUTEAU": "Rue Rambuteau",
 "RUE_RIVOLI": "Rue de Rivoli", "RUE_ROUGEMONT": "Rue Rougemont", "RUE_SAINT_AUGUSTIN": "Rue Saint-Augustin",
 "RUE_SAINT_DENIS": "Rue Saint-Denis", "RUE_SAINT_HONORÉ": "Rue Saint-Honoré", "RUE_SAINT_LAZARE": "Rue Saint-Lazare",
 "RUE_TURBIGO": "Rue de Turbigo", "RUE_VIEUX_COLOMBIER": "Rue du Vieux-Colombier",
 "SCIENCES_PO": ("Sciences Po, rue Saint-Guillaume", 48.85410, 2.32840),
 "AVENUE_JEAN_JANVIER": "Avenue Jean-Janvier", "BOULEVARD_LIBERTÉ": "Boulevard de la Liberté", "RUE_ALMA": "Rue de l'Alma",
 "PLACE_CARMES": "Place des Carmes", "RUE_SAINT_LÔ": "Rue Saint-Lô", "PLACE_TILLEULS": "Place des Tilleuls",
 "PASSAGE_SAINTE_CATHERINE": "Passage Sainte-Catherine", "QUAI_PÊCHEURS": "Quai des Pêcheurs", "RUE_ZURICH": "Rue de Zurich",
 "ALLÉE_PRÉSIDENT_FRANKLIN_ROOSEVELT": "Allée du Président-Franklin-Roosevelt",
 "AVENUE_ÉTIENNE_BILLIÈRES": "Avenue Étienne-Billières", "BOULEVARD_LASCROSSES": "Boulevard Lascrosses",
 "BOULEVARD_STRASBOURG": "Boulevard de Strasbourg", "RUE_CUGNAUX": "Rue de Cugnaux", "PLACE_ÉMILE_MALE": "Place Émile-Mâle",
}

# Fait → (libellé, catégories, infractions présumées, règles en cause). Les plus longs sont reconnus en premier.
F = {
 "GAZ_MASSIF_SIT_IN": ("gaz lacrymogène en masse sur un sit-in", ["Gaz lacrymogène"], ["222-13"], ["R211-13", "R434-18"]),
 "GAZ_SANS_SOMMATION": ("gaz lacrymogène sans sommation", ["Gaz lacrymogène", "Sans sommation"], [], ["L211-9", "R211-11"]),
 "GAZ_MASSIF": ("gaz lacrymogène en masse", ["Gaz lacrymogène"], [], ["R211-13", "R434-18"]),
 "GAZ_ABUSIF": ("gaz lacrymogène disproportionné", ["Gaz lacrymogène"], ["222-13"], ["R434-18"]),
 "GAZ_APPARTEMENT": ("gaz lacrymogène dans un appartement", ["Gaz lacrymogène", "Mise en danger"], ["222-13", "223-1"], ["R434-10", "R434-18"]),
 "GAZ_POMPIERS": ("gaz lacrymogène sur des pompiers", ["Gaz lacrymogène"], ["222-13"], ["R434-18"]),
 "MALAISE_GAZ": ("malaise après un gazage", ["Gaz lacrymogène"], ["222-13"], ["R434-18"]),
 "CARTOUCHE_GAZ": ("tir de grenade lacrymogène", ["Gaz lacrymogène", "Grenade"], ["222-13"], ["R434-18"]),
 "LACRYMOGENE": ("gaz lacrymogène", ["Gaz lacrymogène"], ["222-13"], ["R434-18"]),
 "GAZ": ("gaz lacrymogène", ["Gaz lacrymogène"], ["222-13"], ["R434-18"]),
 "CANON_EAU_DANGEREUX": ("canon à eau dangereux", ["Canon à eau", "Mise en danger"], ["223-1"], ["R434-18"]),
 "CANON_EAU": ("canon à eau", ["Canon à eau"], [], ["R434-18"]),
 "MATRAQUE_PERSONNE_EN_BÉQUILLES": ("coups de matraque sur une personne en béquilles", ["Coups"], ["222-13"], ["R434-18"]),
 "MATRAQUE_PRESSE": ("coups de matraque sur un journaliste", ["Coups", "Atteinte à la presse"], ["222-13", "431-1"], ["SNMO-2.2"]),
 "MATRAQUE_BLESSURE_GRAVE": ("coups de matraque, blessure grave", ["Coups", "Blessure grave"], ["222-12"], ["R434-18"]),
 "BLESSURE_GRAVE_MATRAQUE": ("coups de matraque, blessure grave", ["Coups", "Blessure grave"], ["222-12"], ["R434-18"]),
 "ENFANT_MATRAQUE": ("coups de matraque sur un enfant", ["Coups"], ["222-13"], ["R434-18"]),
 "MATRAQUE": ("coups de matraque", ["Coups"], ["222-13"], ["R434-18"]),
 "TABASSAGES_DONT_PERSONNE_DÉJÀ_BLESSÉE": ("passages à tabac, dont une personne déjà blessée", ["Passage à tabac"], ["222-13"], ["R434-17", "R434-18"]),
 "TABASSAGE_AVEC_MILITANTS_ULTRADROITE": ("passage à tabac aux côtés de militants d'ultradroite", ["Passage à tabac", "Ultradroite"], ["222-13"], ["R434-11", "R434-18"]),
 "TABASSAGES": ("passages à tabac", ["Passage à tabac"], ["222-13"], ["R434-18"]),
 "TABASSAGE": ("passage à tabac", ["Passage à tabac"], ["222-13"], ["R434-18"]),
 "COUP_DE_TÊTE": ("coup de tête", ["Coups"], ["222-13"], ["R434-18"]),
 "COUP_PIED": ("coup de pied", ["Coups"], ["222-13"], ["R434-18"]),
 "COUPS": ("coups", ["Coups"], ["222-13"], ["R434-18"]),
 "COUP": ("coup", ["Coups"], ["222-13"], ["R434-18"]),
 "FRAPPE": ("coups", ["Coups"], ["222-13"], ["R434-18"]),
 "GIFLE": ("gifle", ["Coups"], ["222-13"], ["R434-14", "R434-18"]),
 "ATTAQUE": ("attaque", ["Coups"], ["222-13"], ["R434-18"]),
 "INSULTES": ("insultes", ["Insultes"], ["injure"], ["R434-14"]),
 "PLAQUAGE_DANGEREUX": ("plaquage dangereux", ["Plaquage, maintien au sol"], ["222-13"], ["R434-18"]),
 "PLAQUAGE": ("plaquage au sol", ["Plaquage, maintien au sol"], ["222-13"], ["R434-18"]),
 "ÉCRASEMENT_MAINTIEN_AU_SOL": ("personne écrasée et maintenue au sol", ["Plaquage, maintien au sol"], ["222-13"], ["R434-17", "R434-18"]),
 "MAINTIEN_AU_SOL": ("maintien au sol", ["Plaquage, maintien au sol"], ["222-13"], ["R434-17"]),
 "TENTATIVE_DE_DISSIMULATION": ("tentative de dissimulation", [], [], []),
 "JET_AU_SOL": ("personne jetée au sol", ["Plaquage, maintien au sol"], ["222-13"], ["R434-18"]),
 "BALAYETTE": ("balayette", ["Plaquage, maintien au sol"], ["222-13"], ["R434-18"]),
 "ÉTRANGLEMENT": ("étranglement", ["Étranglement"], ["222-13"], ["R434-17", "R434-18"]),
 "TRAÎNAGE": ("personne traînée au sol", ["Personne traînée"], ["222-13"], ["R434-17"]),
 "TRAINAGE": ("personne traînée au sol", ["Personne traînée"], ["222-13"], ["R434-17"]),
 "GRENADES_TENDUES": ("tirs tendus de grenades", ["Grenade", "Mise en danger"], ["222-13", "223-1"], ["R434-18"]),
 "GRENADE_DANGEREUSE": ("grenade lancée dangereusement", ["Grenade", "Mise en danger"], ["223-1"], ["R434-18"]),
 "GRENADE_PERTE_MAIN": ("grenade, main arrachée", ["Grenade", "Blessure grave"], ["222-10"], ["R434-18"]),
 "MAIN_ARRACHÉE": ("main arrachée", ["Grenade", "Blessure grave"], ["222-10"], ["R434-18"]),
 "GRENADE_BLESSURE_MAIN": ("grenade, blessure à la main", ["Grenade", "Blessure grave"], ["222-12"], ["R434-18"]),
 "GRENADE_BLESSURE_GRAVE_OEIL": ("grenade, blessure grave à l'œil", ["Grenade", "Blessure grave"], ["222-12"], ["R434-18"]),
 "GRENADE_ENFANT": ("grenade, enfant exposé", ["Grenade", "Mise en danger"], ["223-1"], ["R434-10", "R434-18"]),
 "GRENADE_APPARTEMENT": ("grenade tirée dans un appartement", ["Grenade", "Mise en danger"], ["223-1"], ["R434-10", "R434-18"]),
 "TOURISTE_GRENADE": ("grenade sur un touriste", ["Grenade"], ["222-13"], ["R434-18"]),
 "TIR_TENDU_GRENADE": ("tir tendu de grenade", ["Grenade", "Mise en danger"], ["222-13", "223-1"], ["R434-18"]),
 "GRENADES": ("grenades", ["Grenade"], [], ["R434-18"]),
 "GRENADE": ("grenade", ["Grenade"], [], ["R434-18"]),
 "TIR_TENDU_LBD": ("tir tendu de LBD", ["LBD"], ["222-13", "223-1"], ["SNMO-3.3.2", "R434-18"]),
 "TIR_TENDU": ("tir tendu de LBD", ["LBD"], ["222-13", "223-1"], ["SNMO-3.3.2", "R434-18"]),
 "BLESSURE_MAIN_LBD": ("LBD, blessure à la main", ["LBD", "Blessure grave"], ["222-12"], ["SNMO-3.3.2"]),
 "LBD": ("tir de LBD", ["LBD"], ["222-13"], ["SNMO-3.3.2"]),
 "TASER": ("usage du Taser", ["Taser"], ["222-13"], ["R434-18"]),
 "NASSE": ("nasse", ["Nasse"], [], ["SNMO-3.1.4"]),
 "MISE_EN_JOUE_IRRÉGULIÈRE": ("mise en joue irrégulière", ["Mise en joue"], [], ["R434-18"]),
 "MISE_EN_JOUE": ("mise en joue", ["Mise en joue"], [], ["R434-18"]),
 "INTIMIDATION_PRESSE": ("intimidation d'un journaliste", ["Atteinte à la presse", "Intimidation, menaces"], ["431-1"], ["SNMO-2.2"]),
 "EMPÊCHEMENT_LIBRE_CIRCULATION_PRESSE": ("journalistes empêchés de circuler", ["Atteinte à la presse"], ["431-1"], ["SNMO-2.2.3.3"]),
 "INTIMIDATION_MENACES": ("intimidation et menaces", ["Intimidation, menaces"], ["222-17"], ["R434-14"]),
 "MENACES_INTIMIDATION": ("menaces et intimidation", ["Intimidation, menaces"], ["222-17"], ["R434-14"]),
 "INTIMIDATION": ("intimidation", ["Intimidation, menaces"], [], ["R434-14"]),
 "INFILTRATION_POLICE": ("policiers infiltrés dans le cortège", ["Infiltration"], [], ["R434-15"]),
 "INFILTRATION": ("policiers infiltrés dans le cortège", ["Infiltration"], [], ["R434-15"]),
 "AGRESSION_SEXUELLE": ("agression sexuelle", ["Agression sexuelle"], ["222-28"], ["R434-17"]),
 "POUSSETTE_DANGEREUSE_ESCALIERS": ("poussette mise en danger dans des escaliers", ["Mise en danger"], ["223-1"], ["R434-10"]),
 "POUSSETTE_DANGEREUSE": ("poussette mise en danger", ["Mise en danger"], ["223-1"], ["R434-10"]),
 "POUSSETTE": ("intervention près d'une poussette", ["Mise en danger"], ["223-1"], ["R434-10"]),
 "RISQUE_CHUTE": ("risque de chute", ["Mise en danger"], ["223-1"], ["R434-10"]),
 "VÉHICULE": ("véhicule de police dans la foule", ["Mise en danger"], ["223-1"], ["R434-10"]),
 "CHARGE_SANS_SOMMATION": ("charge sans sommation", ["Charge", "Sans sommation"], [], ["L211-9", "R211-11"]),
 "PERSONNE_GRAVEMENT_BLESSÉE_CHARGE_POLICIÈRE": ("personne gravement blessée lors d'une charge", ["Charge", "Blessure grave"], ["222-12"], ["R434-18"]),
 "CHARGEMENT_MOTO": ("charge de policiers à moto", ["Charge"], [], ["R434-18"]),
 "ARRESTATIONS_ABUSIVES": ("arrestations abusives", ["Arrestation abusive"], ["432-4"], ["R434-17"]),
 "ARRESTATION_ABUSIVE": ("arrestation abusive", ["Arrestation abusive"], ["432-4"], ["R434-17"]),
 "SOUTIEN_MILITANTS_ULTRADROITE": ("soutien apparent à des militants d'ultradroite", ["Ultradroite"], [], ["R434-11"]),
 "DÉFENSE_MILITANTS_ULTRADROITE": ("protection de militants d'ultradroite", ["Ultradroite"], [], ["R434-11"]),
 "FOUILLE_ABUSIVE": ("fouille abusive", ["Contrôle, fouille abusifs"], [], ["R434-10", "R434-14"]),
 "CONTRÔLE_ABUSIF": ("contrôle abusif", ["Contrôle, fouille abusifs"], [], ["R434-10", "R434-14"]),
 "CONFISCATION_CONTRÔLE": ("confiscation lors d'un contrôle", ["Contrôle, fouille abusifs"], [], ["R434-14"]),
 "TENTATIVE_ENTRÉE_EN_FORCE_CAFÉ": ("tentative d'entrée en force dans un café", ["Entrée en force"], [], ["R434-10", "R434-18"]),
 "ENTRÉE_EN_FORCE_IMMEUBLE": ("entrée en force dans un immeuble", ["Entrée en force"], ["432-8"], ["R434-10"]),
 "ENTRÉE_EN_FORCE_RESTAURANT": ("entrée en force dans un restaurant", ["Entrée en force"], [], ["R434-10", "R434-18"]),
 "EXPULSION_VIOLENTE_BAR": ("expulsion violente d'un bar", ["Coups", "Entrée en force"], ["222-13"], ["R434-18"]),
 "MANIFESTANT_INCONSCIENT": ("manifestant inconscient", ["Blessure grave"], [], ["R434-17"]),
 "NON_ASSISTANCE_PERSONNE_EN_DANGER": ("non-assistance à personne en danger", ["Non-assistance"], ["223-6"], ["R434-17"]),
 "DISSIMULATION_MARTEAU": ("dissimulation d'un marteau", [], [], []),
 "PANCARTE": ("intervention autour d'une pancarte", [], [], []),
 "DÉCÈS": ("décès d'un manifestant", ["Décès"], [], []),
}
CLES = sorted(F, key=len, reverse=True)

def sans_accent(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')

def lire_faits(reste):
    labels, cats, inf, reg, inconnus = [], [], [], [], []
    toks = reste
    while toks:
        k = next((k for k in CLES if toks == k or toks.startswith(k + "_")), None)
        if not k:
            mot, _, toks = toks.partition("_"); inconnus.append(mot); continue
        l, c, i, r = F[k]
        labels.append(l); cats += c; inf += i; reg += r
        toks = toks[len(k) + 1:]
    u = lambda xs: list(dict.fromkeys(xs))
    return labels, u(cats), u(inf), u(reg), inconnus

def titre(labels):
    if not labels: return "Fait à préciser"
    t = labels[0] if len(labels) == 1 else ", ".join(labels[:-1]) + " et " + labels[-1]
    return t[0].upper() + t[1:]

inv = json.load(open(os.path.join(SRC, 'carte_drive.json')))
corr_p = os.path.join(SRC, 'carte_corrections.json')
corr = json.load(open(corr_p)) if os.path.exists(corr_p) else {}
out, a_revoir = [], []
n_ville = {}
for x in inv:
    fn = unicodedata.normalize('NFC', x['fn'])
    tw = fn.startswith("TW_")
    nom = fn[3:] if tw else fn
    nom = re.sub(r"_\d+$", "", nom)
    ville = VILLES.get(x['ville'], x['ville'].title())
    lieu = None; lat = lng = None
    if nom.startswith("INCONNU_"):
        reste = nom[8:]
    else:
        k = next((k for k in sorted(LIEUX, key=len, reverse=True) if nom.startswith(k + "_")), None)
        if not k:
            a_revoir.append(f"lieu non reconnu : {fn}"); reste = nom
        else:
            v = LIEUX[k]
            if isinstance(v, tuple): lieu, lat, lng = v
            else: lieu = v
            reste = nom[len(k) + 1:]
    labels, cats, inf, reg, inconnus = lire_faits(reste)
    if inconnus: a_revoir.append(f"mots non reconnus {inconnus} : {fn}")
    c = {
        "id": x['id'], "fn": fn, "ville": ville, "adresse": lieu, "sem": x['periode'],
        "t": titre(labels), "violences": cats, "infractions": inf, "regles": reg, "forces": [],
        "s": x.get('source') or "", "tw": tw,
        "k": "Vidéo" if x['mime'].startswith('video/') else ("Image" if x['mime'].startswith('image/') else "Article (PDF)"),
    }
    if lat is not None: c["lat"], c["lng"] = lat, lng
    c.update(corr.get(fn, {}))
    out.append(c)

# cotes : VP- puis numéro, dans l'ordre semaine / ville / nom
out.sort(key=lambda c: (c['sem'], c['ville'] or "~", c['fn']))
for i, c in enumerate(out, 1): c['cote'] = f"VP-{i:03d}"
json.dump(out, open(os.path.join(SRC, 'carte.json'), 'w'), ensure_ascii=False, indent=0)
print(len(out), "faits ;", sum(1 for c in out if c['adresse']), "avec un lieu ;", sum(1 for c in out if c['tw']), "avec avertissement")
for r in a_revoir: print("À REVOIR —", r)
