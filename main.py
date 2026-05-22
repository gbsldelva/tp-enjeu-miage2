'''
Script principal : comparaison des algorithmes d'optimisation sur les
instances du répertoire data/.

Algorithmes comparés :
  1. Greedy         — déterministe, solution unique
  2. NonDeterminist — NB_RUNS runs, meilleur gardé
  3. FirstNeighborLocalSearch — NB_RUNS runs, meilleur gardé
  4. BestNeighborLocalSearch  — NB_RUNS runs, meilleur gardé

Métriques affichées :
  - valeur de la fonction objectif
  - Cmax (makespan)
  - ΣCi (somme des dates de fin)
  - énergie totale
  - temps CPU (secondes)
'''
import os
import time

from src.scheduling.instance.instance import Instance
from src.scheduling.optim.constructive import Greedy, NonDeterminist
from src.scheduling.optim.local_search import (
    FirstNeighborLocalSearch, BestNeighborLocalSearch
)


# ---------------------------------------------------------------------------
# Paramètres du benchmark
# ---------------------------------------------------------------------------

NB_RUNS     = 30    # nombre de runs pour les algorithmes non déterministes
DATA_FOLDER = os.path.join(os.path.dirname(__file__), 'data')
# Instances à tester (jsp2 à jsp10 pour un benchmark rapide)
INSTANCES   = [f"jsp{i}" for i in range(2, 11)]


def run_once(AlgoClass, instance, params=None):
    '''Exécute l'algorithme une fois, retourne (solution, temps_cpu).'''
    debut = time.time()
    sol   = AlgoClass().run(instance, params=params or {})
    return sol, time.time() - debut


def meilleur_sur_n_runs(AlgoClass, instance, n=NB_RUNS, params=None):
    '''
    Exécute l'algorithme n fois, retourne (meilleure solution, temps total).
    Chaque run utilise un seed différent pour la reproductibilité.
    '''
    meilleur_sol = None
    temps_total  = 0.0
    for run in range(n):
        p = {**(params or {}), 'seed': run}
        sol, t = run_once(AlgoClass, instance, p)
        temps_total += t
        if meilleur_sol is None or sol.objective < meilleur_sol.objective:
            meilleur_sol = sol
    return meilleur_sol, temps_total


def afficher_ligne(instance_name, algo_name, sol, temps):
    '''Affiche une ligne formatée dans le tableau de résultats.'''
    if sol is None or not sol.is_feasible:
        print(f"  {instance_name:<8} | {algo_name:<30} | NON RÉALISABLE")
        return
    print(
        f"  {instance_name:<8} | {algo_name:<30} | "
        f"obj={sol.objective:8.1f} | "
        f"Cmax={sol.cmax:5d} | "
        f"ΣCi={sol.sum_ci:6d} | "
        f"E={sol.total_energy_consumption:8.1f} | "
        f"t={temps:.3f}s"
    )


def main():
    print("=" * 105)
    print("  COMPARAISON DES ALGORITHMES — TP ORDONNANCEMENT À CONTRAINTES ÉNERGÉTIQUES")
    print("=" * 105)
    print(f"  {'Instance':<8} | {'Algorithme':<30} | {'Objectif':>10} | "
          f"{'Cmax':>7} | {'ΣCi':>8} | {'Energie':>10} | {'CPU':>8}")
    print("-" * 105)

    for inst_name in INSTANCES:
        inst_folder = os.path.join(DATA_FOLDER, inst_name)
        if not os.path.isdir(inst_folder):
            continue

        instance = Instance.from_file(inst_folder)

        sol_g,  t_g  = run_once(Greedy, instance)
        afficher_ligne(inst_name, "Greedy", sol_g, t_g)

        sol_nd, t_nd = meilleur_sur_n_runs(NonDeterminist, instance)
        afficher_ligne(inst_name, f"NonDeterminist (×{NB_RUNS})", sol_nd, t_nd)

        sol_fn, t_fn = meilleur_sur_n_runs(FirstNeighborLocalSearch, instance)
        afficher_ligne(inst_name, f"FirstNeighborLS (×{NB_RUNS})", sol_fn, t_fn)

        sol_bn, t_bn = meilleur_sur_n_runs(BestNeighborLocalSearch, instance)
        afficher_ligne(inst_name, f"BestNeighborLS (×{NB_RUNS})", sol_bn, t_bn)

        print("-" * 105)

    print("Benchmark terminé.")


if __name__ == "__main__":
    main()
