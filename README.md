# TP — Ordonnancement de tâches sous contraintes énergétiques

Ce projet compare plusieurs algorithmes d'optimisation (glouton, non déterministe,
recherches locales) pour ordonnancer des opérations sur des machines en minimisant à
la fois la durée et la consommation d'énergie.

## Prérequis

- **Python 3.12** ou supérieur
- `pip` (ou [`uv`](https://docs.astral.sh/uv/))

## Installation

Depuis la racine du projet :

```powershell
# 1. Créer un environnement virtuel
python -m venv .venv

# 2. L'activer (Windows / PowerShell)
.venv\Scripts\Activate.ps1

# 3. Installer les dépendances
pip install -r requirements.txt
```

> Sous Linux/macOS, activez l'environnement avec `source .venv/bin/activate`.

## Lancer le projet

Le script principal [main.py](main.py) exécute le benchmark complet : il teste les
4 algorithmes sur les instances `jsp2` à `jsp51` du dossier [data/](data/), affiche
un tableau comparatif et exporte les résultats dans `resultats_benchmark.csv`.

```powershell
python main.py
```

Métriques affichées pour chaque algorithme :

| Métrique   | Description                          |
| ---------- | ------------------------------------ |
| `Objectif` | valeur de la fonction objectif       |
| `Cmax`     | makespan (date de fin la plus tardive) |
| `ΣCi`      | somme des dates de fin               |
| `Energie`  | énergie totale consommée             |
| `CPU`      | temps de calcul (secondes)           |

## Lancer les tests

Les tests unitaires (instances, jobs, machines, solution, optimisation) se trouvent
dans [src/scheduling/tests/](src/scheduling/tests/) et s'exécutent avec `pytest` :

```powershell
# Tous les tests
python -m pytest

# Avec rapport de couverture
python -m pytest --cov=src
```

## Structure du projet

```
main.py                      # Script de benchmark principal
requirements.txt             # Dépendances
data/                        # Instances jspX (fichiers *_op.csv et *_mach.csv)
src/scheduling/
    instance/                # Modélisation : Instance, Job, Machine, Operation
    optim/                   # Heuristiques, voisinages, recherches locales
    solution.py              # Représentation et évaluation d'une solution
    tests/                   # Tests unitaires (pytest / unittest)
```
