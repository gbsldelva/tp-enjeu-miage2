# CLAUDE.md

Ce fichier fournit les directives à Claude Code (claude.ai/code) pour travailler dans ce dépôt.

## Présentation du projet

TP de Master 2 MIAGE portant sur l'**ordonnancement de tâches avec contraintes énergétiques** (variante du Job-Shop Problem). L'objectif est de construire un système d'optimisation qui planifie des opérations d'usine sur des machines tout en minimisant la consommation d'énergie, sous contrainte de délais.

Chaque classe du squelette contient des `raise "Not implemented error"` (levées de chaîne, pas d'exception — quirk du squelette fourni) : la mission est de les implémenter intégralement.

## Commandes

Le projet utilise **uv** comme gestionnaire de dépendances (Python 3.12).

```bash
# Installer les dépendances
uv sync

# Lancer le point d'entrée principal
uv run python main.py

# Lancer tous les tests
uv run python -m pytest src/scheduling/tests/

# Lancer un fichier de tests précis
uv run python -m pytest src/scheduling/tests/test_solution.py

# Lancer un test unitaire précis
uv run python -m pytest src/scheduling/tests/test_solution.py::TestSolution::test_schedule_op

# Lancer une heuristique constructive (génère gantt.png)
uv run python src/scheduling/optim/constructive.py

# Lancer une recherche locale (génère gantt.png)
uv run python src/scheduling/optim/local_search.py

# Ajouter une dépendance
uv add <paquet>
```

## Architecture

```
src/scheduling/
├── instance/              # Modèle de données du problème (lecture seule après construction)
│   ├── instance.py        # Instance : chargement CSV, agrège machines/jobs/opérations
│   ├── machine.py         # Machine : planification (heures de démarrage/arrêt, opérations)
│   ├── job.py             # Job : liste ordonnée d'opérations avec contraintes de précédence
│   └── operation.py       # Operation + OperationScheduleInfo : durée et énergie par machine
├── solution.py            # Solution : encapsule une instance, gère l'état du planning
├── optim/
│   ├── heuristics.py      # Classe abstraite Heuristic(params) → .run(instance) → Solution
│   ├── constructive.py    # Greedy (déterministe) et NonDeterminist
│   ├── neighborhoods.py   # Classe de base Neighborhood + MyNeighborhood1/2 à implémenter
│   └── local_search.py    # FirstNeighborLocalSearch et BestNeighborLocalSearch
└── tests/
    ├── test_utils.py      # TEST_FOLDER_DATA pointe vers tests/data/
    ├── data/jsp1/         # Petite instance de test (1 job, 4 machines) pour les tests unitaires
    ├── test_instance.py
    ├── test_job.py
    ├── test_machine.py
    └── test_solution.py
data/                      # 51 instances de problèmes (jsp2–jsp51), utilisées pour le benchmarking
```

## Concepts métier clés

**Format des données d'instance** (fichiers CSV dans `data/jspX/`) :
- `jspX_op.csv` : colonnes `job, operation, machine, processing_time, energy_consumption` — une ligne par triplet (job, opération, machine) ; chaque opération a donc autant de lignes que de machines éligibles
- `jspX_mach.csv` : colonnes `machine_id, set_up_time, set_up_energy, tear_down_time, tear_down_energy, min_consumption, end_time`

**Contraintes d'ordonnancement** :
- Les opérations d'un même job s'exécutent en séquence stricte (contrainte de précédence)
- Une machine doit être démarrée (`set_up_time` de délai) avant toute opération, puis arrêtée (`tear_down_time`) en fin d'utilisation
- Chaque machine a une échéance ferme `end_time` : elle doit être éteinte avant cette limite
- Une machine peut être démarrée et arrêtée plusieurs fois dans un même planning

**Modèle de consommation énergétique d'une machine** :
```
énergie_totale = énergie_démarrage + (min_consumption × durée_idle) + énergie_opérations + énergie_arrêt
```

**Fonction objectif** : agrégation pondérée de la consommation totale d'énergie, du Cmax (makespan — date de fin du dernier job) et du ΣCi (somme des dates de fin de chaque job).

**`Solution.schedule(operation, machine)`** : planifie l'opération au plus tôt sur la machine (en la démarrant si elle est éteinte). Seules les opérations retournées par `available_operations` peuvent être planifiées.

**`Machine.available_time`** : premier instant auquel la machine peut accepter une nouvelle opération (après la fin de la dernière opération planifiée).

## Méthodologie TDD — niveau de confiance ≥ 95 %

**Toute implémentation suit le cycle Rouge → Vert → Remaniement :**

1. **Écrire le test avant le code** : compléter les modules `test_machine.py`, `test_job.py` et `test_solution.py` avant d'implémenter les classes correspondantes.
2. **Vérifier l'échec** : le test doit échouer avec une erreur explicite avant toute implémentation (`pytest` doit retourner rouge).
3. **Implémenter le minimum suffisant** pour faire passer le test.
4. **Remanier** sans casser aucun test existant.

**Couverture attendue ≥ 95 %** :

```bash
# Vérifier la couverture de tests
uv run python -m pytest src/scheduling/tests/ --cov=src --cov-report=term-missing
```

Chaque méthode publique doit être couverte par au moins un test unitaire dédié. Les cas limites à couvrir obligatoirement :
- Planification d'une opération sur une machine éteinte (déclenchement du démarrage automatique)
- Dépassement de `end_time` (solution non réalisable)
- Opération planifiée avant la fin de son prédécesseur (violation de précédence)
- Instance sans solution réalisable

## Ordre d'implémentation recommandé

Suivre cet ordre pour respecter les dépendances entre classes :

1. `instance/operation.py` → `OperationScheduleInfo`, puis `Operation`
2. `instance/machine.py` → `Machine`
3. `instance/job.py` → `Job`
4. `instance/instance.py` → `Instance.from_file()`
5. `solution.py` → `Solution`
6. `optim/constructive.py` → `Greedy`, puis `NonDeterminist`
7. `optim/neighborhoods.py` → `MyNeighborhood1`, `MyNeighborhood2`
8. `optim/local_search.py` → `FirstNeighborLocalSearch`, `BestNeighborLocalSearch`

## Notes importantes

- Les `raise "Not implemented error"` du squelette lèvent une chaîne de caractères, pas une exception Python : ne pas les conserver dans le code final.
- L'instance de test `jsp1` (dans `tests/data/`) contient 1 job et 2 opérations sur 4 machines — les valeurs attendues dans `test_schedule_op` font foi pour vérifier l'implémentation de `Machine` et `Solution`.
- Le recours à l'IA générative est autorisé **pour le code uniquement** (pas pour le rapport). Les commentaires dans le code doivent préciser explicitement ce qui a été généré et pourquoi.
- Les commentaires et la documentation des classes/méthodes doivent être rédigés **en français**.
- Si un algorithme connu est utilisé (glouton, recherche locale, voisinage swap…), **une référence bibliographique doit figurer en commentaire** dans le code.
