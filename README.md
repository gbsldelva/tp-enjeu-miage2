# TP Ordonnancement de tâches — M2 MIAGE

> Problème d'ordonnancement flexible de type Job-Shop avec contraintes énergétiques.

---

## Lancer le projet

```bash
# Installer les dépendances (Python 3.12 requis)
uv sync

# Tests unitaires
uv run python -m pytest src/scheduling/tests/ -v

# Couverture de tests
uv run python -m pytest src/scheduling/tests/ --cov=src --cov-report=term-missing

# Heuristique constructive (génère gantt.png)
uv run python -m src.scheduling.optim.constructive

# Recherche locale (génère gantt.png)
uv run python -m src.scheduling.optim.local_search

# Benchmark comparatif
uv run python main.py
```

---

## Partie 1 — Modélisation

### 1) Variables de décision, contraintes, objectifs

**Variables de décision :**
- `x(i, m)` : booléen — l'opération `i` est-elle exécutée sur la machine `m` ?
- `s(i)` : entier — heure de début de l'opération `i`
- `u(m, t)` : booléen — la machine `m` est-elle allumée à l'instant `t` ?

**Contraintes :**
1. **Affectation unique** : chaque opération est exécutée sur exactement une machine éligible.
2. **Précédence intra-job** : pour chaque job, l'opération `k+1` commence après la fin de l'opération `k` : `s(k+1) ≥ s(k) + durée(k, machine(k))`.
3. **Disponibilité machine** : une machine doit être allumée (setup terminé) avant de commencer une opération.
4. **Échéance machine** : la dernière opération d'une machine + durée de teardown ≤ `end_time` de la machine.
5. **Non-chevauchement** : deux opérations ne s'exécutent pas simultanément sur la même machine.

**Objectifs (multi-critères) :**
- Minimiser la **consommation totale d'énergie** `E_total`
- Minimiser le **makespan** `Cmax = max(date de fin de chaque job)`
- Minimiser la **somme des dates de fin** `ΣCi`

### 2) Fonction objectif

On agrège les trois critères avec une pondération égale (les poids sont configurables dans `Solution.objective`) :

```
f(s) = w_e × E_total + w_cmax × Cmax + w_ci × ΣCi    (w_e = w_cmax = w_ci = 1 par défaut)
```

**Modèle d'énergie d'une machine** (par session allumage/extinction) :

```
E_session = énergie_setup + énergie_teardown
          + min_consumption × durée_idle
          + Σ énergie_opérations

durée_idle = (stop - start) - setup_time - teardown_time - Σ processing_times
```

### 3) Évaluation d'une solution

- **Solution réalisable** : toutes les contraintes sont satisfaites → valeur de la fonction objectif `f(s)`.
- **Solution non réalisable** : au moins une contrainte est violée (ex. dépassement d'échéance). Dans notre implémentation, `is_feasible` retourne `False` et la solution est exclue des comparaisons. Pour un traitement pénalisé, on pourrait utiliser `f(s) + λ × nombre_de_violations`.

### 4) Instance sans solution réalisable

Exemple : une instance avec **1 job, 1 opération, 1 machine** où :
- `setup_time = 50`, `teardown_time = 50`, `processing_time = 10`
- `end_time = 100`

La machine doit terminer son teardown avant `t = 100`, mais le minimum nécessaire est `50 + 10 + 50 = 110 > 100`. Aucune planification n'est possible.

### 5) Implémentation des classes

Les classes ont été implémentées en suivant la méthodologie TDD (Rouge → Vert → Remaniement) :

| Classe | Fichier | Rôle |
|--------|---------|------|
| `OperationScheduleInfo` | `instance/operation.py` | Données de planification d'une opération |
| `Operation` | `instance/operation.py` | Opération avec options de machines et précédences |
| `Machine` | `instance/machine.py` | Machine avec gestion de sessions multiples |
| `Job` | `instance/job.py` | Job avec liste ordonnée d'opérations |
| `Instance` | `instance/instance.py` | Chargement CSV et accès aux données |
| `Solution` | `solution.py` | Encapsule une solution, calcule les métriques |

---

## Partie 2 — Premières heuristiques

### 1) Algorithme glouton déterministe — `Greedy`

**Principe glouton** : à chaque étape, parmi tous les couples (opération disponible, machine éligible), on choisit celui qui **minimise la consommation d'énergie** de l'opération sur cette machine. En cas d'égalité, on départage par `(job_id, operation_id)` pour garantir la reproductibilité.

**Glouton car** : la décision est prise localement à chaque étape sans retour arrière, en maximisant immédiatement un critère local (minimisation d'énergie), sans tenir compte de l'impact sur les étapes suivantes.

**Contrainte de faisabilité** : avant de sélectionner un couple, on estime si l'opération peut se terminer + faire le teardown avant l'échéance de la machine. On préfère les options réalisables ; si aucune n'existe, on choisit la moins mauvaise.

**Complexité** : O(N² × M) avec N = nombre d'opérations, M = nombre de machines.

### 2) Algorithme non déterministe — `NonDeterminist`

**Principe (GRASP — Greedy Randomized Adaptive Search Procedure)** :

> Feo, T.A. & Resende, M.G.C. (1995). *Greedy Randomized Adaptive Search Procedures*. Journal of Global Optimization, 6(2), 109–133.

À chaque étape :
1. Calculer le coût (énergie) de tous les couples disponibles, en filtrant les options réalisables.
2. Construire une **liste restreinte des k meilleurs** couples (k=5 par défaut).
3. **Choisir aléatoirement** parmi cette liste.

Cela garantit des solutions différentes à chaque appel (seeds différents) tout en gardant un biais vers de bonnes solutions.

**Paramètres** : `k` (taille de la liste restreinte), `seed` (reproductibilité).

### 3) Complexités

| Algorithme | Complexité par itération | Nb itérations | Total |
|------------|--------------------------|----------------|-------|
| Greedy | O(N × M) | N | **O(N² × M)** |
| NonDeterminist | O(N × M × log(N×M)) | N | **O(N² × M × log(NM))** |

---

## Partie 3 — Recherche locale

### 1) Deux voisinages

#### Voisinage 1 — `MyNeighborhood1` : Réaffectation de machine (*MachineReassignment*)

**Définition** : pour chaque opération planifiée, on génère un voisin en la réaffectant à une de ses machines alternatives (toutes sauf la machine actuelle). La solution voisine est reconstruite en rejouant la même séquence de planification avec la nouvelle affectation.

| Propriété | Valeur |
|-----------|--------|
| **Taille** | O(N × M) — pour chaque opération (N), on essaie toutes les machines alternatives (M-1) |
| **Polynomiale ?** | ✅ Oui — O(N × M) est polynomial |
| **Espace connexe ?** | ✅ Oui — toute combinaison d'affectations est atteignable en appliquant N mouvements successifs |

#### Voisinage 2 — `MyNeighborhood2` : Échange d'ordre (*OperationSwap*)

**Définition** : on parcourt la séquence de planification et on permute deux opérations consécutives appartenant à **des jobs différents** (les permutations intra-job sont interdites car elles violeraient les précédences).

| Propriété | Valeur |
|-----------|--------|
| **Taille** | O(N²) dans le pire cas — nombre de paires d'ops de jobs différents |
| **Polynomiale ?** | ✅ Oui |
| **Espace connexe ?** | ❌ Partiellement — toutes les ordonnances sont théoriquement atteignables mais le chemin peut passer par des solutions infaisables |

### 2) Implémentation — `optim/neighborhoods.py`

Les deux voisinages partagent la méthode utilitaire `_rebuild_from_sequence(sequence)` qui reconstruit une solution à partir d'une séquence `(operation_id, machine_id)` en respectant les contraintes de précédence (planification par ordre de rang dans la séquence).

### 3) Deux algorithmes de recherche locale — `optim/local_search.py`

#### `FirstNeighborLocalSearch` — Premier améliorant

```
sol ← NonDeterminist().run(instance)
Répéter (max_iterations fois) :
    voisin ← MyNeighborhood1.first_better_neighbor(sol)
    Si voisin.objectif < sol.objectif : sol ← voisin
    Sinon : arrêt (optimum local)
Retourner sol
```

#### `BestNeighborLocalSearch` — Meilleur améliorant (double voisinage)

```
sol ← NonDeterminist().run(instance)
Répéter (max_iterations fois) :
    meilleur1 ← MyNeighborhood1.best_neighbor(sol)
    meilleur2 ← MyNeighborhood2.best_neighbor(sol)
    meilleur ← argmin(meilleur1, meilleur2)
    Si meilleur.objectif < sol.objectif : sol ← meilleur
    Sinon : arrêt (optimum local)
Retourner sol
```

Critère d'arrêt supplémentaire : `max_iterations = 100` pour éviter les boucles infinies sur de grandes instances.

### 4) Comparaison des algorithmes

Résultats expérimentaux (meilleure solution sur plusieurs runs, `f = E + Cmax + ΣCi`) :

| Instance | Greedy | NonDet ×30 | FirstNeighLS ×10 | BestNeighLS ×10 |
|----------|--------|------------|-----------------|-----------------|
| **jsp1** (4M, 2J, 4op) | 433 / 0.000s | 284 / 0.001s | 269 / 0.005s | **250** / 0.010s |
| **jsp5** (4M, 10J, 40op) | — | 2706 / 0.03s | **2259** / 4.6s | 2654 / 1.0s |
| **jsp9** (4M, 20J, 80op) | — | 3277 / 0.03s | **2439** / 2.9s | 3092 / 0.7s |

**Observations :**

- Le **Greedy** est très rapide mais ne trouve pas de solution réalisable sur les grandes instances (il fait des choix localement optimaux qui bloquent les opérations suivantes).
- **NonDeterminist** trouve rapidement des solutions réalisables grâce à la diversité des seeds.
- **FirstNeighborLocalSearch** produit les **meilleures solutions** mais est le plus lent : explorer toutes les réaffectations de machines à chaque itération est coûteux sur de grandes instances.
- **BestNeighborLocalSearch** offre un bon compromis qualité/temps : le double voisinage permet d'explorer plus largement, mais le critère "meilleur améliorant" implique d'évaluer tous les voisins avant de se déplacer.

**Conclusion** : pour les instances du TP, `FirstNeighborLocalSearch` avec le voisinage de réaffectation de machine offre le meilleur rapport qualité/effort algorithmique, à condition d'avoir une bonne solution initiale (NonDeterminist avec plusieurs seeds).

---

## Architecture du code

```
src/scheduling/
├── instance/
│   ├── operation.py      # Operation + OperationScheduleInfo
│   ├── machine.py        # Machine (sessions multiples, énergie)
│   ├── job.py            # Job (précédences automatiques)
│   └── instance.py       # Instance (chargement CSV)
├── solution.py            # Solution (schedule, is_feasible, gantt, CSV)
├── optim/
│   ├── heuristics.py     # Classe abstraite Heuristic
│   ├── constructive.py   # Greedy + NonDeterminist (GRASP)
│   ├── neighborhoods.py  # MachineReassignment + OperationSwap
│   └── local_search.py   # FirstNeighborLS + BestNeighborLS
└── tests/
    ├── test_instance.py
    ├── test_machine.py   # testWorkingTime, testTotalEnergyConsumption
    ├── test_job.py       # testCompletionTime, précédences
    ├── test_solution.py  # test_schedule_op (valeurs numériques), objectif, gantt
    ├── test_optim.py     # tests de tous les algorithmes
    └── test_coverage.py  # couverture des branches secondaires
```

**Couverture de tests : 99%** (71 tests, méthodologie TDD rouge→vert→remaniement)

---

## Note sur l'utilisation de l'IA générative

Conformément aux instructions du TP, l'IA générative (Claude Sonnet 4.6) a été utilisée **pour le code uniquement** (pas pour le rapport). Elle a assisté dans :
- La structuration des classes et l'organisation du code
- L'implémentation des algorithmes (Greedy, GRASP, recherche locale)
- La rédaction des tests unitaires
- La correction des bugs d'implémentation

Toutes les décisions algorithmiques (choix des critères gloutons, définition des voisinages, paramétrage des recherches locales) ont été réfléchies et validées manuellement.

---

## Références bibliographiques

- Pinedo, M. (2016). *Scheduling: Theory, Algorithms, and Systems* (5th ed.). Springer.
- Feo, T.A. & Resende, M.G.C. (1995). *Greedy Randomized Adaptive Search Procedures*. Journal of Global Optimization, 6(2), 109–133.
- Nowicki, E. & Smutnicki, C. (1996). *A fast taboo search algorithm for the job shop problem*. Management Science, 42(6), 797–813.
- Aarts, E. & Lenstra, J.K. (eds.) (1997). *Local Search in Combinatorial Optimization*. Wiley.
