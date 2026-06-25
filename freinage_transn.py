#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
  CALCULATEUR DE FREINAGE transN  —  FLIRT (RABe 523/527) & Domino (RBDe 560)
================================================================================
Outil d'entraînement / révision (formation MEC). Implémente les formules
officielles PCT R 300.5 (A2025) et reproduit les tables des Livrets de matériel
roulant (LMR) Flirt P 20003126 v17 et Domino P 20005282 v12, ainsi que la table
"Effort de retenue minimal" (Complément 1, INFRA DE PCT NIOP R I-30111).

CE QU'IL CALCULE pour n'importe quelle composition (rame seule, UM, Domino +0/1/2
INOVA), sur une déclivité quelconque réglable (défaut = 28 ‰) :
  1. Rapport de freinage          -> formule exacte + verdict catégorie
  2. Rupture d'attelage           -> rapport de freinage PARTIEL (R 300.5 §3.5.4)
  3. Peut-on rouler / remorqué ?  -> selon rapport + tableau de freinage
  4. Immobilisation               -> effort de retenue requis, sabots nécessaires

------------------------------------------------------------------------------
AVERTISSEMENT (lis-le) : c'est un AIDE-MÉMOIRE de formation, PAS une autorité
opérationnelle. La référence reste le BULLETIN DE CHARGE PERMANENT du LMR, les
tables du LMR et le tableau de freinage du GI. Vérifie toujours toute valeur
"limite" avant un usage réel. Les données véhicule sont éditables ci-dessous.
------------------------------------------------------------------------------
"""

import math

# =============================================================================
#  1. BASE DE DONNÉES VÉHICULES  (éditable — source citée par valeur)
# =============================================================================
#  total      = poids total = poids à pleine charge (t)            -> cas "chargé"
#  tare       = poids à vide (t)                                   -> cas "vide"
#  pf_R       = poids-frein en position R (t)
#  pf_RMg     = poids-frein R + frein magnétique (t)   (None si absent)
#  ressort_v/c= frein à ressort (frein d'immobilisation) à vide / chargé (kN)
#  freine     = True si le véhicule possède un frein automatique actif
# -----------------------------------------------------------------------------
VEHICLES = {
    # --- Domino RBDe 560 DO ---
    "RBDe560": dict(nom="RBDe 560 (motrice)", role="motrice", cat="R", vmax=140,
                    tare=72, total=80, pf_R=124, pf_RMg=None, remorque=72, rq_vmax=80,
                    ressort_v=27, ressort_c=27, sabot_v=18, sabot_c=21, freine=True,
                    src="LMR Domino P20005282 §1.1.1"),
    "INOVA":   dict(nom="INOVA (interm.)", role="interm", cat="R", vmax=140,
                    tare=36, total=50, pf_R=70, pf_RMg=92, remorque=70, rq_vmax=80,
                    ressort_v=21, ressort_c=25, sabot_v=18, sabot_c=21, freine=True,
                    src="LMR Domino P20005282 §1.1.3"),
    "ABt":     dict(nom="ABt DO (voiture de commande)", role="commande", cat="R", vmax=140,
                    tare=38, total=43, pf_R=55, pf_RMg=76, remorque=55, rq_vmax=80,
                    ressort_v=21, ressort_c=21, sabot_v=18, sabot_c=21, freine=True,
                    src="LMR Domino P20005282 §1.1.2"),
    # --- Flirt transN (rames indissociables -> 1 unité freinée) ---
    "RABe523": dict(nom="RABe 523 (rame automotrice, 074-077)", role="rame", cat="R", vmax=160,
                    tare=121, total=145, pf_R=245, pf_RMg=281, remorque=179, rq_vmax=140,
                    ressort_v=124, ressort_c=124, sabot_v=19, sabot_c=25, freine=True,
                    note="frein à ressort 124 kN jusqu'à 50 ‰ (rame ligne forte pente)",
                    src="LMR Flirt P20003126 §1.1.7"),
    "RABe527": dict(nom="RABe 527 (rame automotrice, 331-333)", role="rame", cat="R", vmax=160,
                    tare=120, total=141, pf_R=226, pf_RMg=241, remorque=96, rq_vmax=140,
                    ressort_v=73, ressort_c=80, sabot_v=19, sabot_c=25, freine=True,
                    note="pf_R max 251 t ; cat. homologuée R 150%",
                    src="LMR Flirt P20003126 §1.1.7"),
}

# =============================================================================
#  2. EFFORT DE RETENUE MINIMAL  (Complément 1, INFRA DE PCT NIOP R I-30111)
#     poids du train [t] x déclivité [‰] -> kN requis pour immobiliser
# =============================================================================
RETENUE_DECL = [3, 5, 10, 12, 15, 18, 20, 23, 25, 27, 30, 32, 35, 38, 40, 43, 45, 50]
RETENUE_TABLE = {
    25:  [2, 2, 4, 5, 6, 7, 7, 8, 9, 10, 11, 11, 13, 14, 14, 15, 16, 18],
    50:  [3, 4, 7, 9, 11, 13, 14, 16, 18, 19, 21, 22, 25, 27, 28, 30, 31, 35],
    75:  [5, 6, 11, 13, 16, 19, 21, 24, 26, 28, 31, 33, 37, 40, 42, 45, 47, 52],
    100: [6, 8, 14, 17, 21, 25, 28, 32, 35, 38, 42, 44, 49, 53, 55, 60, 62, 69],
    125: [7, 10, 18, 21, 26, 31, 35, 40, 43, 47, 52, 55, 61, 66, 69, 74, 78, 86],
    150: [9, 12, 21, 25, 31, 38, 42, 48, 52, 56, 62, 66, 73, 79, 83, 89, 93, 104],
}
RETENUE_POIDS = sorted(RETENUE_TABLE)
# Coefficient validé : kN_requis ≈ k * poids[t] * decl[‰]  (reproduit la table
# et les tables LMR §5.7 au kN près). Utilisé pour extrapoler au-delà de 150 t.
K_RETENUE = 0.01385

# =============================================================================
#  3. PARAMÈTRES
# =============================================================================
SABOT_KN_VIDE = 18.0      # sabot par défaut à vide ; valeur par engin dans VEHICLES (Domino 18/21, Flirt 19/25)
SABOT_KN_CHARGE = 21.0    # 1 sabot d'arrêt (LMR Domino §5.7, chargé)
DECL_CAP = 50.0           # plafond des tables (‰)

# Catégories de train transN (CH I-30001 LP GI IOP, compl. réseau transN) :
#   catégorie -> (rapport_min %, vmax km/h)
BANDS = {"R": (105, 160), "A": (50, 120), "D": (50, 80)}
# Catégories de freinage transN (Bremsreihen) = paliers discrets (CH I-30001,
# compl. TPF/transN/Travys). Règle : on retient le palier <= rapport calculé.
BREMS = {"R": [150, 135, 125, 115, 105],
         "AD": [115, 105, 95, 85, 80, 75, 70, 65, 60, 50]}

# Tableau de freinage IIA (DE-OCF transN), colonne 25 km/h : rapport de freinage
# PARTIEL minimal exigé (%) par déclivité déterminante (DE PCT NIOP §3.1 ;
# seuil R 300.5 §3.5.4). Lecture par tranche : 1re déclivité >= déclivité considérée.
PARTIEL_IIA_25 = [(0, 12), (5, 16), (10, 19), (15, 23), (20, 27), (25, 31),
                  (30, 36), (35, 42), (40, 48), (45, 53), (50, 59)]


def seuil_partiel(decl):
    """Renvoie (tranche_‰, seuil_%) ou (None, None) si > 50 ‰ (hors tableau IIA)."""
    for g, v in PARTIEL_IIA_25:
        if decl <= g:
            return g, v
    return None, None

# =============================================================================
#  MOTEURS DE TRACTION  (RBDe 560 & Flirt 4 él. = 4 moteurs, 2 bogies)
# =============================================================================
MOTRICES = {"RBDe560", "RABe523", "RABe527"}
# Charge normale RBDe 560 (LMR Domino §5.2) : rampe ‰ -> charge remorquée max (t)
CN_DOMINO = [(0, 300), (18, 300), (20, 280), (22, 250), (24, 230), (26, 210),
             (28, 190), (30, 180), (35, 150), (36, 145), (37, 140), (38, 135),
             (45, 110), (50, 100)]
TOL_CHARGE = 4.0   # tolérance +4 t sur charge remorquée NORMALE (PE PCT IOP §1.5) ;
                   # NE s'applique PAS à la charge normale réduite (moteurs HS)

def charge_normale_domino(d):
    if d <= CN_DOMINO[0][0]:
        return CN_DOMINO[0][1]
    if d >= CN_DOMINO[-1][0]:
        return CN_DOMINO[-1][1]
    for (a, va), (b, vb) in zip(CN_DOMINO, CN_DOMINO[1:]):
        if a <= d <= b:
            return va + (d - a) / (b - a) * (vb - va)
    return CN_DOMINO[-1][1]

def domino_motor(m):
    """m = [b1m1, b1m2, b2m1, b2m2] (True = isolé). LMR Domino §9.3."""
    n = sum(m)
    b1, b2 = m[0] + m[1], m[2] + m[3]
    if n == 0:
        return dict(n=n, traction=1.0, freinE=1.0, lbl="tous moteurs OK")
    if n == 1:
        return dict(n=n, traction=0.75, freinE=0.75, lbl="1 moteur isolé -> 3/4 traction")
    if n == 2 and (b1 == 2 or b2 == 2):
        return dict(n=n, traction=0.5, freinE=0.5, lbl="2 moteurs (même bogie) -> 1/2 traction")
    if n == 2:
        return dict(n=n, traction=0.5, freinE=0.0,
                    lbl="1 moteur/bogie (commande de secours) -> 1/2 traction, frein E=0")
    if n == 3:
        return dict(n=n, traction=None, freinE=0.0,
                    lbl="3 moteurs isolés -> hors table (remorquage/dégager)")
    return dict(n=n, traction=0.0, freinE=0.0, lbl="4 moteurs isolés -> aucune traction (remorqué)")

def flirt_motor(m):
    """LMR Flirt §9.2."""
    n = sum(m)
    if n <= 1:
        return dict(n=n, max_decl=float("inf"),
                    lbl=("tous moteurs OK" if n == 0 else "1 moteur isolé -> aucune restriction"))
    if n == 2:
        return dict(n=n, max_decl=30.0,
                    lbl="2 moteurs isolés -> rampes <=30 ‰ (>30 ‰ pour dégager)")
    return dict(n=n, max_decl=0.0, lbl=f"{n} moteurs isolés -> hors table (remorqué/dégager)")

# Flirt — freins paralysés PAR BOGIE (LMR §9.4.1, RABe 521/523/524/527 4 él.).
# Donne la catégorie dégradée OFFICIELLE (non recalculée).
FLIRT_BRAKE = {
    "none": dict(lbl="aucun frein paralysé", train=None, reihe=None, remorque=False, ressort_red=0.0),
    "m1":   dict(lbl="1 bogie moteur (frein à ressort)", train="R", reihe=115, remorque=False, ressort_red=0.5),
    "p15":  dict(lbl="1½ bogie porteur", train="R", reihe=115, remorque=False, ressort_red=0.0),
    "p3":   dict(lbl="3 bogies porteurs", train="A", reihe=75, remorque=False, ressort_red=0.0),
    "m2":   dict(lbl="2 bogies moteurs (frein à ressort)", train=None, reihe=None, remorque=True, ressort_red=1.0),
}

def effective_category(train, flirt_brakes=None):
    """Train Flirt (rames) -> catégorie officielle par rame (nominale ou §9.4 si
    bogie paralysé), convoi = la plus restrictive. Train Domino -> mode 'calc'."""
    flirt_brakes = flirt_brakes or {}
    flirts = [(i, v) for i, v in enumerate(train) if v["role"] == "rame"]
    has_domino = any(v["role"] in ("motrice", "interm", "commande") for v in train)
    if flirts and not has_domino:
        per = []
        for i, v in flirts:
            key = flirt_brakes.get(i, "none")
            s = FLIRT_BRAKE[key]
            if key != "none":
                per.append(dict(name=v["nom"], train=s["train"], reihe=s["reihe"],
                                remorque=s["remorque"], note=s["lbl"]))
            else:
                cg = categorie(arrondi_pct(v["pf_R"] / v["total"] * 100))
                per.append(dict(name=v["nom"], train=cg["train"], reihe=cg["reihe"],
                                remorque=False, note="nominal"))
        score = lambda p: -1 if p["remorque"] else (1000 if p["train"] == "R" else 0) + (p["reihe"] or 0)
        worst = min(per, key=score)
        return dict(mode="flirt", per=per, worst=worst,
                    scenario=any(flirt_brakes.get(i, "none") != "none" for i, _ in flirts))
    return dict(mode="calc")

# =============================================================================
#  4. CONSTRUCTION DU TRAIN
# =============================================================================
def build_train(units):
    """units = liste de clés VEHICLES, ex: ['RBDe560','INOVA','ABt'] ou
    ['RABe523','RABe523'] (UM). Renvoie la liste des dicts véhicule."""
    train = []
    for u in units:
        if u not in VEHICLES:
            raise KeyError(f"Véhicule inconnu : {u} (dispo: {list(VEHICLES)})")
        train.append(dict(VEHICLES[u], _key=u))
    return train

def poids_train(train, charge="total"):
    return sum(v[charge] for v in train)

def poids_frein_total(train, mg=False):
    s = 0.0
    for v in train:
        if not v["freine"]:
            continue
        s += v["pf_RMg"] if (mg and v.get("pf_RMg")) else v["pf_R"]
    return s

# =============================================================================
#  5. RAPPORT DE FREINAGE  (R 300.5 §3.2)
# =============================================================================
def arrondi_pct(x):
    """Arrondi PCT : >=0.5 -> haut, <0.5 -> bas."""
    return math.floor(x + 0.5)

def rapport_de_freinage(train, charge="total", mg=False):
    P = poids_train(train, charge)
    PF = poids_frein_total(train, mg=mg)
    rf = PF / P * 100.0
    return {
        "poids": P, "poids_frein": PF, "rf_exact": rf, "rf": arrondi_pct(rf),
        "formule": f"Rapport de freinage = Poids-frein / Poids du train x 100 "
                   f"= {PF:.0f} / {P:.0f} x 100 = {rf:.1f} % -> {arrondi_pct(rf)} %",
    }

def categorie(rf):
    """Catégorie de train + de freinage selon le rapport de freinage (indépendant
    de la déclivité). Renvoie un dict, ou {'train': None} si insuffisant."""
    if rf >= BANDS["R"][0]:
        tr = "R"
    elif rf >= BANDS["A"][0]:
        tr = "A"
    else:
        return {"train": None}
    steps = BREMS["R"] if tr == "R" else BREMS["AD"]   # décroissants
    reihe = next((s for s in steps if rf >= s), None)
    return {"train": tr, "reihe": reihe, "vmax": BANDS[tr][1], "min": BANDS[tr][0]}

# =============================================================================
#  6. RUPTURE D'ATTELAGE — RAPPORT DE FREINAGE PARTIEL  (R 300.5 §3.5.4)
# =============================================================================
def controle_partiel(train, decl=27, freins_paralyses=None, flirt_brakes=None):
    """
    Règle R 300.5 §3.5.4 :
      - Si TOUS les véhicules sont pleinement freinés -> rapport partiel ATTEINT,
        pas de calcul (cas normal Flirt/Domino).
      - Sinon, calculer le rapport partiel à chaque attelage (partie avant / arrière)
        et le comparer au minimum exigé à 25 km/h pour la déclivité.
    freins_paralyses = index (0-based) de véhicules Domino au frein de service paralysé.
    flirt_brakes     = {index: scénario} de bogies Flirt paralysés (§9.4), p.ex. {1:"p3"}.
    """
    freins_paralyses = set(freins_paralyses or [])
    flirt_brakes = flirt_brakes or {}

    def fb_of(i, v):
        return flirt_brakes.get(i, "none") if v["role"] == "rame" else "none"

    etat = []        # True = pleinement freiné (poids-frein nominal)
    for i, v in enumerate(train):
        freine = v["freine"] and (i not in freins_paralyses) and fb_of(i, v) == "none"
        etat.append(freine)

    if all(etat):
        return {"ok": True, "auto": True,
                "msg": "Tous les véhicules sont freinés -> rapport de freinage "
                       "partiel ATTEINT par principe (R 300.5 §3.5.4), aucun "
                       "calcul requis. Une rupture d'attelage déclenche le frein "
                       "d'urgence (rupture CG) sur les DEUX parties, chacune "
                       "restant freinée."}

    # --- Cas avec frein(s) paralysé(s) : rapport partiel à CHAQUE attelage ---
    def eff_pf(i, v):
        # poids-frein effectif : 0 si paralysé/non freiné ; catégorie dégradée §9.4
        # pour un Flirt à bogies paralysés (les bogies sains freinent) ; sinon nominal.
        if (i in freins_paralyses) or not v["freine"]:
            return 0.0
        fb = fb_of(i, v)
        if fb != "none":
            s = FLIRT_BRAKE[fb]
            return (s["reihe"] / 100 * v["total"]) if s["reihe"] is not None else v["remorque"]
        return v["pf_R"]

    P = [v["total"] for v in train]
    PF = [eff_pf(i, v) for i, v in enumerate(train)]
    n = len(train)
    g_br, seuil = seuil_partiel(decl)
    # détail par attelage : coupure entre le véhicule i et i+1 -> partie avant / arrière
    coupures = []
    for i in range(n - 1):
        fpf = sum(PF[j] for j in range(0, i + 1)); fw = sum(P[j] for j in range(0, i + 1))
        rpf = sum(PF[j] for j in range(i + 1, n)); rw = sum(P[j] for j in range(i + 1, n))
        coupures.append({"i": i,
                         "fr": fpf / fw * 100 if fw else 0,
                         "rr": rpf / rw * 100 if rw else 0})
    rf_min = min(min(c["fr"], c["rr"]) for c in coupures)
    if seuil is None:   # > 50 ‰ : hors tableau de freinage IIA
        verdict = (f"plus petit rapport partiel = {rf_min:.0f} % — au-delà de 50 ‰, "
                   f"hors tableau de freinage IIA (à évaluer selon prescriptions).")
        ok = None
    elif rf_min <= 0:
        verdict = ("une rupture peut isoler une partie SANS frein actif -> risque "
                   "de dérive, à sécuriser (R 300.5 §12.2).")
        ok = False
    else:
        ok = rf_min >= seuil
        br_txt = (f"{g_br} ‰" if g_br == int(round(decl))
                  else f"{decl:.0f} ‰ -> tranche {g_br} ‰")
        verdict = (f"pire coupure : plus petit rapport partiel = {rf_min:.0f} % "
                   f"({'>=' if ok else '<'} {seuil} % requis ; tableau de freinage "
                   f"IIA, 25 km/h, {br_txt}) -> {'OK, suffisant' if ok else 'INSUFFISANT'}")
    return {"ok": ok, "auto": False, "rf_min": rf_min,
            "coupures": coupures, "seuil": seuil, "msg": verdict}

# =============================================================================
#  7. PEUT-ON ROULER ?
# =============================================================================
def peut_rouler(train, decl=27, charge="total", mg=False):
    rf = rapport_de_freinage(train, charge, mg)
    vmax_veh = min(v["vmax"] for v in train)
    cg = categorie(rf["rf"])
    if cg["train"] is None:
        return {"rf": rf, "cg": cg, "roule": False,
                "msg": f"Rapport {rf['rf']} % insuffisant (min. 105 % cat. R, "
                       f"50 % cat. A) -> REMORQUÉ (ou catégorie inférieure)."}
    plafond = min(cg["vmax"], vmax_veh)
    reihe = f"{cg['train']} {cg['reihe']}"
    return {"rf": rf, "cg": cg, "roule": True, "vmax": plafond, "reihe": reihe,
            "msg": f"Rapport {rf['rf']} % -> catégorie {reihe} (le « {cg['reihe']} » "
                   f"est un % de freinage, PAS une vitesse). PEUT rouler ; plafond "
                   f"cat. {cg['train']} sur transN = {cg['vmax']} km/h"
                   + (f", véhicule {vmax_veh} km/h" if plafond < cg["vmax"] else "")
                   + f". Vitesse réelle de la classe {reihe} à {decl:.0f} ‰ : RADN "
                   f"(souvent < plafond pour les classes basses)."}

# =============================================================================
#  8. IMMOBILISATION — EFFORT DE RETENUE  (Complément 1)
# =============================================================================
def effort_requis(poids, decl):
    """kN requis pour immobiliser 'poids' t à 'decl' ‰ (table Complément 1,
    interpolée ; extrapolée linéairement en poids >150 t et en pente >50 ‰)."""
    if decl > DECL_CAP:                       # au-delà de la table : formule validée
        return K_RETENUE * poids * decl
    d = min(decl, DECL_CAP)

    def interp_decl(row):
        if d <= RETENUE_DECL[0]:
            return row[0]
        if d >= RETENUE_DECL[-1]:
            return row[-1]
        for k in range(len(RETENUE_DECL) - 1):
            a, b = RETENUE_DECL[k], RETENUE_DECL[k + 1]
            if a <= d <= b:
                t = (d - a) / (b - a)
                return row[k] + t * (row[k + 1] - row[k])
        return row[-1]

    if poids <= RETENUE_POIDS[-1]:
        # interpolation bilinéaire dans la table
        if poids <= RETENUE_POIDS[0]:
            return interp_decl(RETENUE_TABLE[RETENUE_POIDS[0]]) * poids / RETENUE_POIDS[0]
        for k in range(len(RETENUE_POIDS) - 1):
            a, b = RETENUE_POIDS[k], RETENUE_POIDS[k + 1]
            if a <= poids <= b:
                va = interp_decl(RETENUE_TABLE[a])
                vb = interp_decl(RETENUE_TABLE[b])
                t = (poids - a) / (b - a)
                return va + t * (vb - va)
    # poids > 150 t : la valeur est proportionnelle au poids (linéaire validé)
    v150 = interp_decl(RETENUE_TABLE[150])
    return v150 * poids / 150.0

def effort_disponible(train, charge="total", n_sabots=0, flirt_brakes=None,
                      freins_ressort_paralyses=None):
    flirt_brakes = flirt_brakes or {}
    rpar = set(freins_ressort_paralyses or [])
    ressort = 0.0
    for i, v in enumerate(train):
        if i in rpar:                       # frein à ressort paralysé -> ne contribue pas
            continue
        r = v["ressort_c"] if charge == "total" else v["ressort_v"]
        if v["role"] == "rame":
            r *= (1 - FLIRT_BRAKE[flirt_brakes.get(i, "none")]["ressort_red"])
        ressort += r
    skey = "sabot_c" if charge == "total" else "sabot_v"
    sabot1 = max((v.get(skey, SABOT_KN_CHARGE if charge == "total" else SABOT_KN_VIDE)
                  for v in train), default=(SABOT_KN_CHARGE if charge == "total" else SABOT_KN_VIDE))
    return ressort + n_sabots * sabot1, ressort, sabot1

def immobilisation(train, decl=27, charge="total", flirt_brakes=None,
                   freins_ressort_paralyses=None, towed=False):
    P = poids_train(train, charge)
    req = effort_requis(P, decl)
    _, ressort_full, sabot1 = effort_disponible(train, charge, 0, flirt_brakes,
                                                freins_ressort_paralyses)
    # remorqué : le frein à ressort doit être DESSERRÉ pour permettre le remorquage -> ne retient pas
    ressort = 0.0 if towed else ressort_full
    # nombre de sabots basé sur la FORCE (échelle LMR §5.5/§5.7)
    manque = max(0.0, req - ressort)
    n_sabots = math.ceil(manque / sabot1) if manque > 0 else 0
    dispo = ressort + n_sabots * sabot1
    decl_max_ressort = math.floor(min(DECL_CAP, ressort / (K_RETENUE * P))) if P else 0
    decl_max_full = math.floor(min(DECL_CAP, ressort_full / (K_RETENUE * P))) if P else 0
    if towed:
        if n_sabots == 0:
            msg = (f"Frein à ressort desserré (remorquage) = 0 kN ; requis {req:.0f} kN "
                   f"à {decl:.0f} ‰ -> aucune retenue nécessaire (terrain plat).")
        else:
            msg = (f"Frein à ressort DESSERRÉ (remorquage) = 0 kN, requis {req:.0f} kN "
                   f"à {decl:.0f} ‰ -> immobiliser aux {n_sabots} sabot(s) "
                   f"(= {dispo:.0f} kN >= {req:.0f} kN). Resserré à l'arrêt : "
                   f"tient seul jusqu'à {decl_max_full:.0f} ‰.")
    elif n_sabots == 0:
        msg = (f"Frein à ressort seul = {ressort:.0f} kN >= requis {req:.0f} kN "
               f"à {decl:.0f} ‰ -> tient jusqu'à {decl_max_ressort:.0f} ‰, aucun sabot.")
    else:
        msg = (f"Frein à ressort seul = {ressort:.0f} kN, requis {req:.0f} kN "
               f"à {decl:.0f} ‰ -> INSUFFISANT, ajouter {n_sabots} sabot(s) "
               f"(= {dispo:.0f} kN >= {req:.0f} kN).")
    return {
        "poids": P, "requis": req, "ressort": ressort, "sabot1": sabot1,
        "n_sabots": n_sabots, "dispo": dispo,
        "decl_max_ressort": decl_max_ressort, "decl_max_full": decl_max_full,
        "ressort_full": ressort_full, "towed": towed,
        "ok_ressort": ressort >= req,
        "msg": msg,
    }

# =============================================================================
#  9. RAPPORT COMPLET
# =============================================================================
def analyse_remorque(units, decl=27, charge="total"):
    """Rame en panne TRACTÉE (remorquée) : seul le frein à air freine (pas de
    frein électrique). Vérifie rapport, catégorie et risque en forte pente."""
    train = build_train(units)
    noms = " + ".join(v["nom"] for v in train)
    P = poids_train(train, charge)
    pf_rq = sum(v["remorque"] for v in train if v["freine"])
    pf_nom = sum(v["pf_R"] for v in train if v["freine"])
    rf_rq = arrondi_pct(pf_rq / P * 100) if P else 0
    rf_nom = arrondi_pct(pf_nom / P * 100) if P else 0
    cg_rq, cg_nom = categorie(rf_rq), categorie(rf_nom)
    tow_cap = min(v["rq_vmax"] for v in train)
    cat_vmax = cg_rq["vmax"] if cg_rq["train"] else 0
    plafond = min(cat_vmax, tow_cap) if cg_rq["train"] else 0
    im = immobilisation(train, decl, charge, towed=True)

    def cat_txt(cg): return f"{cg['train']} {cg['reihe']}" if cg["train"] else "SOUS MIN (<50%)"
    L = ["=" * 70, f"REMORQUÉ (rame tractée, en panne) : {noms}",
         f"Charge : {'pleine' if charge == 'total' else 'à vide'}  |  Déclivité : {decl:.0f} ‰",
         "=" * 70,
         "[1] RAPPORT DE FREINAGE (frein à air seul, sans frein électrique)",
         f"    Poids-frein remorqué = {pf_rq:.0f} t (LMR « Remorqué »)",
         f"    Rapport = {pf_rq:.0f} / {P:.0f} x 100 = {rf_rq} %  ->  {cat_txt(cg_rq)}",
         f"    (frein normal = {rf_nom} % -> {cat_txt(cg_nom)})"]
    if (cg_rq["train"], cg_rq.get("reihe")) != (cg_nom["train"], cg_nom.get("reihe")):
        L.append("    /!\\ Freinage REDUIT en remorqué -> catégorie dégradée, attention en forte pente.")
    L.append("[2] CIRCULATION")
    if cg_rq["train"]:
        L.append(f"    Plafond = min(catégorie {cg_rq['train']} {cat_vmax} km/h, "
                 f"procédure remorquage {tow_cap} km/h) = {plafond} km/h")
        L.append(f"    Vitesse réelle pour {cat_txt(cg_rq)} à {decl:.0f} ‰ : voir RADN (plus basse en forte pente).")
    else:
        L.append("    Rapport < 50 % -> ne peut rouler sous ses propres freins.")
    L.append("[3] IMMOBILISATION (frein à ressort desserré pour le remorquage)")
    L.append("    " + im["msg"])
    L.append("    Pour remorquer, le frein à ressort doit être desserré -> il ne retient "
             "pas le convoi. Immobiliser aux sabots, ou resserrer le frein à ressort à "
             "l'arrêt (air purgé, frein non bloqué mécaniquement).")
    L.append("[4] RUPTURE D'ATTELAGE")
    if all(v["freine"] for v in train):
        L.append("    Tous les véhicules freinent (frein à air) -> freine des 2 côtés. Une "
                 "rupture déchire la conduite générale -> frein d'urgence (air) sur chaque "
                 "partie, avec le poids-frein REMORQUÉ (réduit, pas de frein électrique).")
    else:
        L.append("    Véhicule non freiné présent -> vérifier le rapport partiel "
                 "(frein à air seul, poids-frein remorqué).")
    return "\n".join(L)


# Charge normale Tm 5235 077 (t) : lignes = vitesse, colonnes = rampe ‰ (PE PCT IOP §1.11)
TM_SPEEDS = [1, 2, 3, 5, 8, 10, 12, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80]
TM_RAMPES = [0, 6, 12, 14, 18]
TM_CN = [
    [1637, 1637, 1637, 1637, 1637, 1637, 1637, 1637, 1637, 1637, 1637, 1637, 1637, 1594, 1326, 1119, 966, 833, 725, 636, 561],
    [935, 935, 935, 935, 935, 935, 935, 935, 843, 667, 547, 452, 383, 328, 284, 248, 221, 196, 175, 156, 140],
    [645, 645, 645, 645, 645, 645, 645, 595, 434, 341, 279, 229, 192, 163, 139, 120, 106, 92, 81, 71, 62],
    [583, 583, 583, 583, 583, 583, 574, 509, 370, 290, 236, 193, 161, 135, 115, 99, 86, 75, 65, 56, 48],
    [487, 487, 487, 487, 487, 487, 442, 391, 282, 219, 176, 142, 117, 98, 82, 69, 59, 50, 42, 35, 29],
]


def tm_cap(si, rampe):
    if rampe <= 0:
        return TM_CN[0][si]
    if rampe >= 18:
        return TM_CN[-1][si]
    for i in range(1, len(TM_RAMPES)):
        if rampe <= TM_RAMPES[i]:
            r0, r1 = TM_RAMPES[i - 1], TM_RAMPES[i]
            c0, c1 = TM_CN[i - 1][si], TM_CN[i][si]
            return c0 + (c1 - c0) * (rampe - r0) / (r1 - r0)
    return TM_CN[-1][si]


def tm_max_speed(load, rampe):
    """Vitesse max (km/h) où le Tm tracte `load` t à `rampe` ‰ ; None si impossible/hors table."""
    if rampe > 18:
        return None
    for i in range(len(TM_SPEEDS) - 1, -1, -1):
        if tm_cap(i, rampe) >= load:
            return TM_SPEEDS[i]
    return None


# type=domino : keys (1er=motrice) ; type=tm : poids/brake ; type=flirt : keys actives, n=nb
TRACTEURS = {
    "d2":   {"lbl": "Domino 2",       "type": "domino", "keys": ["RBDe560", "ABt"]},
    "d3":   {"lbl": "Domino 3",       "type": "domino", "keys": ["RBDe560", "INOVA", "ABt"]},
    "d4":   {"lbl": "Domino 4",       "type": "domino", "keys": ["RBDe560", "INOVA", "INOVA", "ABt"]},
    "tm":   {"lbl": "Tm 5235 077",    "type": "tm", "poids": 49.9, "brake": 60, "vmax": 80},
    "f527": {"lbl": "1 FLIRT 527 (active)", "type": "flirt", "keys": ["RABe527"], "n": 1},
    "f523": {"lbl": "1 FLIRT 523 (active)", "type": "flirt", "keys": ["RABe523"], "n": 1},
    "f2":   {"lbl": "2 FLIRT (sandwich)",   "type": "flirt", "keys": ["RABe527", "RABe527"], "n": 2},
}
TRACTEUR_LBL = {k: v["lbl"] for k, v in TRACTEURS.items()}


def rampe_max(load):
    """Rampe max (‰) où une charge `load` t passe encore (inverse charge normale RBDe)."""
    for i, (g, c) in enumerate(CN_DOMINO):
        if c < load:
            return CN_DOMINO[i - 1][0] if i > 0 else 0
    return 50


def analyse_remorquage_convoi(units, tracteur, decl=27, charge="total"):
    """Convoi de secours : tracteur SAIN + rame EN PANNE (frein à air seul). Vérifie
    traction (rampe) + freinage (convoi) + vitesse. Gère 3 types de tracteur :
      - Domino (RBDe/D3/D4) : charge normale du RBDe par rampe (§5.2) ;
      - Tm 5235 077 : charge normale par vitesse x rampe, max 18 ‰ (PE PCT IOP) ;
      - FLIRT (1 ou 2 actives) : remorque 1 rame FLIRT, rampe max 30 ‰ (§5.2.1)."""
    t = TRACTEURS[tracteur]
    train = build_train(units)
    w = "total" if charge == "total" else "tare"
    d_weight = poids_train(train, charge)
    d_brake = sum(v["remorque"] for v in train if v["freine"])
    d_name = "+".join(units)
    d_is_flirt = any(k.startswith("RABe") for k in units)
    d_is_domino = any(not k.startswith("RABe") for k in units)
    n_flirt_towed = sum(1 for k in units if k.startswith("RABe"))

    # Frein + poids du tracteur
    if t["type"] == "tm":
        t_brake, t_weight = t["brake"], t["poids"]
    else:
        t_brake = sum(VEHICLES[k]["pf_R"] for k in t["keys"] if VEHICLES[k]["freine"])
        t_weight = sum(VEHICLES[k][w] for k in t["keys"])

    # Traction
    vmax_traction = None
    if t["type"] == "domino":
        t_trail = sum(VEHICLES[k][w] for k in t["keys"][1:])
        load = t_trail + d_weight
        cap = charge_normale_domino(decl)
        traction_ok = load <= cap
        traction_line = (f"Remorques tracteur {t_trail:.0f} t + rame {d_weight:.0f} t = {load:.0f} t  vs  "
                         f"charge normale RBDe {cap:.0f} t -> {'OK' if traction_ok else f'NON (limite {rampe_max(load)} ‰)'}")
    elif t["type"] == "tm":
        if decl > 18:
            traction_ok = False
            traction_line = f"Tm hors table > 18 ‰ : ne peut pas tracter de charge à {decl:.0f} ‰."
        else:
            vmax_traction = tm_max_speed(d_weight, decl)
            traction_ok = vmax_traction is not None
            traction_line = (f"Charge normale Tm >= {d_weight:.0f} t -> "
                             + (f"OK jusqu'à {vmax_traction} km/h à {decl:.0f} ‰" if traction_ok else "NON (trop lourd)"))
    else:  # flirt
        traction_ok = decl <= 30
        traction_line = f"1-2 FLIRT remorquent 1 rame FLIRT jusqu'à 30 ‰ (§5.2.1). À {decl:.0f} ‰ -> {'OK' if traction_ok else 'dépassé'}."

    # Freinage convoi
    c_rf = arrondi_pct((t_brake + d_brake) / (t_weight + d_weight) * 100)
    c_cg = categorie(c_rf)

    # Vitesse + attelage
    if t["type"] == "domino":
        ident = not d_is_flirt
        tow_cap = 80 if ident else 100
        coupler = ("Domino-Domino, attelage UIC -> 80 km/h (§5.3.1.1)." if ident
                   else "Flirt-Domino (coupleurs incompatibles), attelage de secours -> 100 km/h (§5.3.2.2).")
    elif t["type"] == "tm":
        tow_cap = min(t["vmax"], vmax_traction if vmax_traction is not None else t["vmax"])
        coupler = "Tm = autre véhicule moteur (§5.2.2), attelage de secours ; pousse 20 km/h max."
    else:
        tow_cap = 100
        coupler = ("FLIRT remorque FLIRT (§5.2.1) : 100 km/h, rampe max 30 ‰, serrage frein élec. max 50 %."
                   + (" Sandwich : 1 active devant + 1 remorquée + 1 active derrière." if t["n"] == 2 else ""))
    plafond = min(tow_cap, c_cg["vmax"]) if c_cg["train"] else 0
    if t["type"] == "tm" and vmax_traction is not None:
        plafond = min(plafond, vmax_traction)

    # Restriction de composition
    hard_stop = t["type"] == "flirt" and n_flirt_towed > 1
    warns = []
    if hard_stop:
        warns.append(f"⚠ §5.2.1 : 1-2 FLIRT actives ne remorquent qu'UNE rame FLIRT (ici {n_flirt_towed}).")
    elif t["type"] in ("domino", "tm") and d_is_domino and d_is_flirt:
        warns.append("⚠ Rame mixte Domino+Flirt : vérifier la compatibilité d'attelage.")
    # PE PCT IOP : cat. R = max 1 véhicule moteur remorqué
    if t["type"] in ("domino", "tm") and n_flirt_towed > 1 and c_cg["train"] == "R":
        warns.append("⚠ Cat. R : max 1 véhicule moteur remorqué (PE PCT IOP). 2 rames FLIRT -> cat. A/D (<=20 essieux).")
    note40 = ("PE PCT IOP : véhicule moteur remorqué — si tous les véhicules ne sont pas reliés à la "
              "conduite générale, Vmax 40 km/h.") if d_is_flirt else None

    def ct(cg): return f"{cg['train']} {cg['reihe']}" if cg["train"] else "INSUFFISANT (<50%)"
    global_ok = traction_ok and bool(c_cg["train"]) and not hard_stop
    verdict = ("COMPOSITION NON ADMISE" if hard_stop
               else "REMORQUAGE POSSIBLE" if global_ok
               else "TRACTION INSUFFISANTE" if not traction_ok
               else "FREINAGE INSUFFISANT")
    L = ["=" * 70,
         f"REMORQUAGE : {t['lbl']} (sain) + {d_name} (en panne, frein air seul)",
         f"Charge : {'pleine' if charge == 'total' else 'à vide'}  |  Rampe/pente : {decl:.0f} ‰",
         "=" * 70,
         "[1] TRACTION : " + traction_line,
         "[2] FREINAGE : "
         f"(frein {t_brake:.0f} t + frein air {d_brake:.0f} t) / ({t_weight:.0f}+{d_weight:.0f} t) = {c_rf} % -> {ct(c_cg)}",
         "[3] VITESSE  : " + (f"plafond {plafond} km/h (cap {tow_cap}, cat. {ct(c_cg)})" if c_cg["train"] else "freinage insuffisant"),
         "             " + coupler]
    if note40:
        L.append("             " + note40)
    for wn in warns:
        L.append("             " + wn)
    L += ["=" * 70, f"VERDICT : {verdict}"]
    return "\n".join(L)


def analyse(units, decl=27, charge="total", freins_paralyses=None, mg=False,
            motors=None, flirt_brakes=None, freins_ressort_paralyses=None):
    train = build_train(units)
    noms = " + ".join(v["nom"] for v in train)
    L = []
    L.append("=" * 70)
    L.append(f"COMPOSITION : {noms}")
    L.append(f"Charge : {'pleine (poids total)' if charge=='total' else 'à vide (tare)'}"
             f"   |   Déclivité : {decl:.0f} ‰ (réglable)")
    L.append("=" * 70)

    # 1) Rapport / catégorie de freinage
    ec = effective_category(train, flirt_brakes)
    if ec["mode"] == "calc":
        pr = peut_rouler(train, decl, charge, mg)
        rf = pr["rf"]; cg = pr["cg"]
        reihe = f"{cg['train']} {cg['reihe']}" if cg["train"] else "aucune (remorqué)"
        L.append("\n[1] RAPPORT & CATÉGORIE DE FREINAGE")
        L.append("    " + rf["formule"])
        L.append(f"    Catégorie de freinage = palier <= {rf['rf']} %  ->  {reihe}")
        L.append("\n[2] PEUT-ON ROULER ?")
        L.append("    " + pr["msg"])
    else:
        w = ec["worst"]
        reihe = "remorqué" if w["remorque"] else f"{w['train']} {w['reihe']}"
        src = "LMR §9.4 (frein paralysé par bogie)" if ec["scenario"] else "nominale"
        L.append(f"\n[1] CATÉGORIE DE FREINAGE (Flirt) — officielle, {src}")
        for p in ec["per"]:
            pc = "remorqué" if p["remorque"] else f"{p['train']} {p['reihe']}"
            L.append(f"    {p['name']} : {pc}  ({p['note']})")
        L.append(f"    -> convoi (la plus restrictive) : {reihe}")
        L.append("\n[2] PEUT-ON ROULER ?")
        if w["remorque"]:
            L.append("    Catégorie insuffisante -> REMORQUÉ (ou vitesse réduite selon RADN).")
        else:
            vmax_veh = min(v["vmax"] for v in train)
            plafond = min(BANDS[w["train"]][1], vmax_veh)
            L.append(f"    Catégorie {reihe} (le « {w['reihe']} » est un % de freinage, "
                     f"PAS une vitesse). Plafond cat. {w['train']} transN = "
                     f"{BANDS[w['train']][1]} km/h, véhicule {vmax_veh}. "
                     f"Vitesse réelle à {decl:.0f} ‰ : RADN.")

    # 3) Rupture d'attelage
    cp = controle_partiel(train, decl, freins_paralyses, flirt_brakes)
    L.append("\n[3] RAPPORT DE FREINAGE PARTIEL (en cas de rupture d'attelage)")
    L.append("    " + cp["msg"])
    if cp.get("coupures"):
        seuil = cp.get("seuil")
        fp = set(freins_paralyses or [])
        fb = flirt_brakes or {}
        courts = [v["nom"].split("(")[0].strip() for v in train]

        def _mark(i, v, c):
            if v["role"] == "rame" and fb.get(i, "none") != "none":
                s = FLIRT_BRAKE[fb[i]]
                tag = f"{s['train']} {s['reihe']}" if s["reihe"] is not None else "remorqué"
                return f"{c} [{tag} §9.4]"
            if i in fp or not v["freine"]:
                return f"{c}*"
            return c

        seq = " | ".join(_mark(i, v, courts[i]) for i, v in enumerate(train))
        L.append(f"    Train : [ {seq} ]   (* = frein paralysé ; [§9.4] = Flirt bogies paralysés)")

        def _ftxt(rap):
            if rap <= 0:
                return f"{rap:3.0f}% NE FREINE PAS"
            if seuil is not None and rap < seuil:
                return f"{rap:3.0f}% insuffisant"
            return f"{rap:3.0f}% freine"

        for c in cp["coupures"]:
            i = c["i"]
            L.append(f"      coupure apres veh.{i+1} «{courts[i]}» : "
                     f"avant {_ftxt(c['fr'])}  |  arriere {_ftxt(c['rr'])}")

    # 4) Immobilisation
    im = immobilisation(train, decl, charge, flirt_brakes, freins_ressort_paralyses)
    L.append(f"\n[4] IMMOBILISATION à {decl:.0f} ‰")
    L.append("    " + im["msg"])
    # échelle officielle : frein à ressort seul, +1, +2, +3 sabots -> rampe max
    L.append(f"    Échelle (frein à ressort {im['ressort']:.0f} kN · 1 sabot = "
             f"{im['sabot1']:.0f} kN {'chargé' if charge=='total' else 'vide'}) :")
    for n in range(0, 4):
        e = im["ressort"] + n * im["sabot1"]
        dmax = math.floor(min(DECL_CAP, e / (K_RETENUE * im["poids"]))) if im["poids"] else 0
        tag = "  <-- requis ici" if n == im["n_sabots"] else ""
        label = "frein à ressort seul" if n == 0 else f"+ {n} sabot{'s' if n > 1 else ''}"
        L.append(f"      {label:<22} {e:>5.0f} kN  ->  <= {dmax:.0f} ‰{tag}")
        if dmax >= DECL_CAP:
            break
    # frein paralysé Domino = frein de service (poids-frein, §9.2.1), pas le frein à ressort
    _par = freins_paralyses or []
    _par_idx = set(_par.keys()) if isinstance(_par, dict) else set(_par)
    if any(i < len(train) and not train[i]["_key"].startswith("RABe") for i in _par_idx):
        L.append("    Note : un frein de service paralysé isole le poids-frein "
                 "(§9.2.1) -> agit sur le rapport, pas sur l'immobilisation. Le frein à "
                 "ressort (§5.7) est un circuit indépendant. Pour le retirer aussi, utiliser "
                 "freins_ressort_paralyses.")
    _rpar = set(freins_ressort_paralyses or [])
    if _rpar:
        n = len(_rpar)
        L.append(f"    Frein à ressort paralysé sur {n} véhicule(s) -> exclu(s) de "
                 f"l'immobilisation (frein à ressort réduit à {im['ressort']:.0f} kN ci-dessus).")
    if decl > 20:
        L.append(f"    (Mise en garage prolongée — R 300.4 §1.7.2 : poser en outre >= 1 "
                 f"sabot pour tout véhicule garé sur pente > 20 ‰ ; ici le frein à "
                 f"ressort seul tient jusqu'à {im['decl_max_ressort']:.0f} ‰ selon la LMR.)")
    L.append("    Frein a air seul : autorise uniquement < 2 ‰ et remise en garage "
             "< 30 min (R 300.5 §2.4).")
    if decl > DECL_CAP:
        L.append("    /!\\ au-delà de 50 ‰ : hors table Compl.1 et hors "
                 "certification frein à ressort Flirt (50 ‰) -> valeur extrapolée.")

    # 5) Traction (moteurs isolés)
    if motors:
        L.append(f"\n[5] TRACTION à {decl:.0f} ‰ (moteurs isolés)")
        for idx, m in motors.items():
            v = train[idx]
            if v["role"] == "rame":                      # Flirt
                fmr = flirt_motor(m)
                if fmr["max_decl"] == float("inf"):
                    verdict = "aucune restriction de pente"
                elif decl <= fmr["max_decl"]:
                    verdict = f"pente {decl:.0f} ‰ <= {fmr['max_decl']:.0f} ‰ -> PEUT rouler"
                else:
                    verdict = (f"pente {decl:.0f} ‰ > {fmr['max_decl']:.0f} ‰ -> "
                               "uniquement pour dégager le tronçon")
                L.append(f"    {v['nom']} : {fmr['lbl']}")
                L.append(f"      -> {verdict}")
            else:                                        # Domino motrice
                dmr = domino_motor(m)
                towed = 0.0
                for k in range(idx + 1, len(train)):
                    if train[k]["_key"] in MOTRICES:
                        break
                    towed += train[k][charge]
                if dmr["traction"] in (0.0, None):
                    verdict = "aucune traction exploitable -> REMORQUÉ / dégager"
                else:
                    cn = charge_normale_domino(decl) * dmr["traction"]
                    ok = towed <= cn
                    verdict = (f"charge remorquée max = {charge_normale_domino(decl):.0f} "
                               f"× {dmr['traction']} = {cn:.0f} t "
                               f"vs {towed:.0f} t -> "
                               f"{'PEUT monter' if ok else 'NE PEUT PAS monter'}")
                fe = "0 (désactivé)" if dmr["freinE"] == 0 else f"×{dmr['freinE']}"
                L.append(f"    {v['nom']} : {dmr['lbl']} · frein E {fe}")
                L.append(f"      -> {verdict}")
        L.append("    NB: charge normale réduite -> ni charge augmentée ni tolérance "
                 "+4 t (PE PCT IOP §1.5).")
        L.append("    NB: moteur isolé != frein paralysé (n'affecte pas le rapport "
                 "de freinage R, seulement traction + frein E).")

    L.append("")
    return "\n".join(L)


# =============================================================================
#  DÉMO + AUTO-VALIDATION
# =============================================================================
DERANGEMENTS = {
    "Domino": [
        ("§9.1.1", "Suspension défectueuse — voiture de commande (ABt)",
         "Vmax 80 km/h",
         "La suspension pneumatique passe sur rappel mécanique (« suspension en marche de secours » = état de la suspension, pas un mode de conduite du train) -> Vmax 80 km/h. Évacuer la voiture de commande à la prochaine gare (plus de voyageurs). Remplacer au terminus ; rebroussement exceptionnel permis."),
        ("§9.1.2", "Suspension défectueuse — voiture Inova",
         "Pas de limite de vitesse ; poids-frein réduit",
         "Poids-frein Inova = frein R 51 t (au lieu de 70). Freinage auto de la charge inactif → recalculer le rapport avec 51 t."),
        ("§9.4", "Tension des batteries insuffisante (remorquage)",
         "Freins en service -> centre d'entretien",
         "Pas de prise ligne de train côté cabine -> pas de RIC. Freins laissés en service (non freiné en queue interdit). Éviter les forts freinages (méplats)."),
        ("§9.5", "Dispositif de protection contre les chocs",
         "Traction simple : marche impossible",
         "Perceptible par abaissement du pantographe (manomètre 503). Traction multiple -> commuter l'automotrice en panne en voiture de commande. Voir P 20005399."),
    ],
    "Flirt": [
        ("§9.1", "Suspension pneumatique défectueuse",
         "R 125 % · vmax 90 km/h (marche de secours)",
         "Suspendre la rame au plus tard à la gare terminus."),
        ("§9.3", "Panne du frein électrique",
         "1 convertisseur 130 km/h · 2 convertisseurs 90 km/h",
         "À combiner avec moteurs de traction isolés (§9.2)."),
        ("§9.3.1", "Panne du frein électrique — fortes pentes",
         "Vmax 40 km/h",
         "Frein électrique HS en forte pente -> 40 km/h."),
        ("§9.5.2/9.5.3", "Protection incendie — Flirt transN (523 & 527)",
         "Aucune restriction",
         "523 (installation fixe) : déclenchement sans feu avéré ou dérangement -> marche sans restriction (§9.5.2). 527 331-333 transN : pas d'installation fixe, extincteurs seulement (§9.5.3). -> Aucune restriction de circulation liée à l'anti-incendie pour les Flirt transN. (Si déclenchement réel : §9.5.1, s'arrêter et délimiter.)"),
        ("§9.6", "Exploitation comme voiture de commande",
         "Vider la rame dès que possible",
         "Ventilation des compartiments voyageurs hors service."),
    ],
}


def memo_derangements():
    """Fiches mémo des dérangements §9 NON couverts par le calcul (restrictions
    fixes du Livret de matériel roulant)."""
    L = ["=" * 70, "AUTRES DÉRANGEMENTS (§9 LMR) — restrictions fixes, pas des calculs", "=" * 70]
    for engin, items in DERANGEMENTS.items():
        L.append(f"\n--- {engin} ---")
        for ref, titre, val, proc in items:
            L.append(f"  {ref:8s} {titre}")
            L.append(f"           >> {val}")
            L.append(f"           {proc}")
    L.append("\n(Déjà calculés ailleurs : freins paralysés, moteurs isolés, remorqué.")
    L.append(" Vitesses par tronçon : RADN I-30131.)")
    return "\n".join(L)


if __name__ == "__main__":
    # --- Validation contre le bulletin de charge permanent Domino (LMR §5.6) ---
    print("##### VALIDATION : bulletin de charge permanent Domino (LMR §5.6) #####")
    attendu = {("RBDe560", "ABt"): 146,
               ("RBDe560", "INOVA", "ABt"): 144,
               ("RBDe560", "INOVA", "INOVA", "ABt"): 143}
    for comp, ref in attendu.items():
        rf = rapport_de_freinage(build_train(list(comp)))
        ok = "OK" if rf["rf"] == ref else "ECART"
        print(f"  {'+'.join(comp):35s} -> {rf['rf']} %  (réf LMR {ref} %)  [{ok}]")

    # --- Cas types ---
    print("\n\n" + analyse(["RBDe560", "INOVA", "ABt"], decl=27))
    print(analyse(["RABe523"], decl=27))
    print(analyse(["RABe527", "RABe527"], decl=27))   # UM 2x Flirt 527
    # Cas dérangement : un frein paralysé (INOVA) sur le Domino
    print(analyse(["RBDe560", "INOVA", "ABt"], decl=27, freins_paralyses=[1]))
    # Cas traction : Domino 3 avec 2 moteurs isolés (même bogie) sur 28 ‰
    print(analyse(["RBDe560", "INOVA", "ABt"], decl=27,
                  motors={0: [True, True, False, False]}))
    # Cas traction : UM 2x Flirt 527, 2 moteurs isolés sur la 1re rame, 28 ‰
    print(analyse(["RABe527", "RABe527"], decl=27,
                  motors={0: [True, True, False, False]}))
    # Cas frein paralysé Flirt PAR BOGIE (§9.4) : RABe 523, 1 bogie moteur, puis 3 porteurs
    print(analyse(["RABe523"], decl=27, flirt_brakes={0: "m1"}))
    print(analyse(["RABe523"], decl=27, flirt_brakes={0: "p3"}))
    # Cas immobilisation forte pente (sabots) : Domino 3 chargé 45 ‰ ; Flirt 527 chargé 50 ‰
    print(analyse(["RBDe560", "INOVA", "ABt"], decl=45, charge="total"))
    print(analyse(["RABe527"], decl=50, charge="total"))
    # Cas REMORQUÉ (rame en panne, tractée) : Domino 4, Domino 2, Flirt 527, Flirt 523
    print("\n\n########## MODE REMORQUÉ ##########")
    print(analyse_remorque(["RBDe560", "INOVA", "INOVA", "ABt"], decl=27))
    print(analyse_remorque(["RBDe560", "ABt"], decl=27))
    print(analyse_remorque(["RABe527"], decl=27))
    print(analyse_remorque(["RABe523"], decl=27))
    # Fiches mémo des autres dérangements (§9 LMR)
    print("\n\n" + memo_derangements())
    # Convoi de secours : tracteur + rame en panne (tous types de tracteur)
    print("\n\n########## REMORQUAGE PAR UN TRACTEUR ##########")
    print(analyse_remorquage_convoi(["RABe527"], "d2", decl=27))   # RBDe seule + Flirt 527 -> OK
    print(analyse_remorquage_convoi(["RABe527"], "d4", decl=27))     # Domino 4 + Flirt 527 -> NON (traction)
    print(analyse_remorquage_convoi(["RABe527"], "tm", decl=27))     # Tm + Flirt 527 @27 -> NON (>18 ‰)
    print(analyse_remorquage_convoi(["RABe527"], "tm", decl=18))     # Tm + Flirt 527 @18 -> OK 35 km/h
    print(analyse_remorquage_convoi(["RABe523"], "f527", decl=27))   # 1 Flirt 527 + Flirt 523 -> OK
    print(analyse_remorquage_convoi(["RABe523"], "f2", decl=27))     # 2 Flirt sandwich + 523 -> OK
    print(analyse_remorquage_convoi(["RABe527", "RABe523"], "f527", decl=27))  # 1 Flirt + 2 remorquées -> NON ADMIS
