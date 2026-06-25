# Calculateur de freinage transN

Outil de calcul du **freinage ferroviaire** pour le réseau **transN** (Flirt RABe 523/527, Domino RBDe 560, tracteur Tm 5235 077).
Disponible en **application web autonome** (installable comme app sur téléphone) et en **script Python**.

> Conçu comme aide de calcul et support de formation (préparation à la certification MEC). **Ne remplace pas** les documents officiels, le RADN, ni le jugement du mécanicien — voir l'[avertissement](#avertissement).

---

## À quoi ça sert

À partir d'une composition de train, d'une charge et d'une déclivité, l'outil calcule et affiche :

- le **rapport de freinage** (`Σ poids-frein ÷ Σ poids du train × 100`) ;
- la **catégorie de frein** atteinte (R / A / D) et la **série de freinage** (Bremsreihe) transN correspondante ;
- le **plafond de vitesse** lié à la catégorie, avec rappel que le rapport est un *pourcentage*, pas une vitesse (la vitesse réelle se lit dans le RADN) ;
- les **sabots d'arrêt**, le **stationnement** et l'**immobilisation** (frein à ressort) selon la pente ;
- les situations de **freins paralysés** et de **remorquage**.

Le tout calé sur le matériel et les prescriptions du réseau transN.

---

## Fonctionnalités

- **Composition du train** — rames complètes en un clic (Domino 2/3/4, Flirt 523/527), unités multiples (UM), ou véhicule par véhicule. La composition est nommée correctement (« Domino 3 · rame de 3 éléments », « UM : … »).
- **Charge** (à vide / en charge) et **déclivité réglable** avec pentes prédéfinies (20, 21, **27 ‰ La Chaux-de-Fonds** par défaut, 30, 40, 50).
- **Rapport de freinage, catégorie et Bremsreihe** calculés et expliqués (formules visibles).
- **Sabots d'arrêt / stationnement / immobilisation** selon la force de freinage et la pente.
- **Freins paralysés** — Flirt par bogie (§9.4) et Domino par véhicule (§9.2.1).
- **Mode remorqué** (rame en panne, frein à air seul) et **module de remorquage par un engin** :
  - train-navette Domino 2/3/4 (charge normale du RBDe 560),
  - tracteur Tm 5235 077 (charge normale par vitesse × rampe, limité à 18 ‰ avec charge),
  - rame Flirt remorqueuse, y compris configuration **sandwich** (§5.2.1),
  - contrôles de traction, de freinage du convoi, de vitesse et de composition (cat. R, conduite générale…).
- **Onglet « Autres dérangements »** — fiches mémo des dérangements §9 (suspension, frein électrique, batteries, protection contre les chocs, incendie, voiture de commande…).

---

## Les fichiers

| Fichier | Description |
|---|---|
| `freinage_transn.html` | Application web **autonome**, zéro dépendance, responsive. **Installable en PWA mono-fichier** (icône, manifeste et logo embarqués). |
| `freinage_transn.py` | Script **Python** miroir : mêmes formules et mêmes données, avec auto-validation intégrée. |

Les deux partagent exactement les mêmes données réglementaires et donnent les mêmes résultats.

---

## Utilisation

**Application web**
- Ouvrir `freinage_transn.html` dans n'importe quel navigateur (ordinateur ou téléphone).
- Pour l'installer sur **iPhone** : héberger le fichier (par ex. *tiiny.host*, *Netlify Drop* ou *GitHub Pages* en le renommant `index.html`), l'ouvrir dans **Safari**, puis *Partager → Sur l'écran d'accueil*. L'app fonctionne ensuite hors-ligne.
- Les fichiers ouverts depuis Dropbox / Drive / iCloud ne s'exécutent pas : passer par un hébergeur statique.

**Script Python**
```bash
python3 freinage_transn.py
```

---

## Sur quoi c'est basé

L'outil reprend les formules, barèmes et données des documents officiels suivants.

### Réglementation (PCT / DE / PE)

- **PCT — Prescriptions suisses de circulation des trains**, R 300.1 à R 300.15 (édition A2025).
- **DE PCT NIOP transN** — Dispositions d'exécution, *R I-30111-transN* (valable dès le 14.12.2025).
- **PE PCT IOP transN** — Prescriptions d'exploitation, *P 35 011 099* (valable dès le 14.12.2025).
  → caractéristiques du matériel, charges normales (RBDe 560, Tm 5235 077), règles de composition.
- **Livret CFF Infrastructure (GI IOP)** — *CH I-30001* (caractéristiques réseau, catégories de vitesse).

### Matériel roulant (LMR / manuels)

- **Flirt 521-524, 527 — Livret de matériel roulant (LMR)**, *P 20003126* (14.12.2025).
- **Domino — Livret de matériel roulant (LMR)**, *P 20005282* (14.12.2025).
- **RBDe 560 Domino — Manuel d'utilisation**, *P 20004076* (01.07.2021).
- **Flirt 521, 522, 523 — Manuel d'utilisation**, *P 20003014* (18.11.2022).
- **Flirt transN — Mise en service**, *P 35004528* (06.07.2018).

### Profils de ligne

- **RADN** — Renseignements pour le calcul des déclivités déterminantes, *I-30131*.
  ⚠️ Seul le document de **modifications** (pages 140-146) a servi de référence ; le profil complet Buttes–Neuchâtel n'y figure pas. Les pentes prédéfinies du Val-de-Travers ne sont donc **pas** validées par le RADN dans cette version.

---

## Données et formules validées

Quelques éléments-clés repris dans l'outil (références entre parenthèses) :

- **Rapport de freinage** : `Σ poids-frein ÷ Σ poids du train × 100` (R 300.5 §3.2).
- **Effort de retenue** : `K_ret ≈ 0,01385 × poids[t] × déclivité[‰]` (validé sur LMR / Complément 1 DE PCT NIOP).
- **Catégories de freinage (Bremsreihe)** :
  - R : `150, 135, 125, 115, 105`
  - A et D : `115, 105, 95, 85, 80, 75, 70, 65, 60, 50`
- **Plafonds de vitesse par catégorie** : R = 160, A = 120, **D = 80 km/h** (D = 80 spécifique à transN, *CH I-30001*).
- **Sabots** : Flirt 19 / 25 kN (à vide / chargé), Domino 18 / 21 kN — nombre calculé par la force (LMR §5.5 / §5.7).
- **Stationnement** : frein à air seul admis uniquement < 2 ‰ et < 30 min ; sinon frein à ressort.
- **Charge normale** : RBDe 560 (table par rampe, LMR §5.2) ; Tm 5235 077 (table vitesse × rampe, PE PCT IOP, max 18 ‰).
- **Remorquage** : Flirt §5.2.1 (1 ou 2 FLIRT → 1 rame, rampe max 30 ‰, vmax 100 km/h) ; §5.2.2 (autre véhicule moteur) ; §5.6.1 (poids-frein) ; règles de composition PE PCT IOP (cat. R = max 1 véhicule moteur remorqué).
- **Dérangements** : fiches §9 des LMR Flirt et Domino.

---

## Avertissement

⚠️ **Outil personnel d'aide et de formation, sans valeur officielle.**

- Il **ne remplace pas** les documents en vigueur, le **RADN**, ni les supports de formation transN.
- Le **mécanicien (MEC) reste seul responsable** du calcul de freinage réel et de la conduite.
- Les valeurs et barèmes peuvent évoluer : **toujours vérifier** par rapport aux documents officiels à jour et au RADN de la ligne concernée.
- En cas de divergence entre cet outil et un document officiel, **le document officiel fait foi**.

---

## Limites connues

- Réseau et matériel **transN uniquement** (Flirt RABe 523/527, Domino RBDe 560, Tm 5235 077).
- Le module de remorquage couvre les configurations courantes ; certaines combinaisons rares (cumul remorqué + frein paralysé, moteurs isolés sur l'engin remorqueur, sandwich avec rames 523) ne sont pas automatisées.

---

*Projet personnel, transN, région Neuchâtel / Val-de-Travers.*
