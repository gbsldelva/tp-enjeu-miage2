'''
Algorithmes de recherche locale.

Référence :
  Aarts, E. & Lenstra, J.K. (eds.) (1997). Local Search in Combinatorial
  Optimization. Wiley. — Chapitre 5 : descente de gradient et variantes.

@author: Vassilissa Lehoux
'''
from typing import Dict

from src.scheduling.optim.heuristics import Heuristic
from src.scheduling.instance.instance import Instance
from src.scheduling.solution import Solution
from src.scheduling.optim.constructive import NonDeterminist
from src.scheduling.optim.neighborhoods import MyNeighborhood1, MyNeighborhood2


class FirstNeighborLocalSearch(Heuristic):
    '''
    Recherche locale « premier améliorant » (First Improvement).

    Algorithme :
    1. Générer une solution initiale avec NonDeterminist.
    2. À chaque itération, trouver le PREMIER voisin qui améliore la
       solution courante (via MyNeighborhood1.first_better_neighbor).
    3. Remplacer la solution courante si un voisin améliorant est trouvé.
    4. S'arrêter quand aucun voisin n'améliore (optimum local).

    Paramètres :
      - max_iterations (int) : nombre maximum d'itérations (défaut : 500)
    '''

    def __init__(self, params: Dict = None):
        '''
        Constructeur.
        @param params: peut contenir 'max_iterations' (int)
        '''
        super().__init__(params)

    def run(self, instance: Instance, InitClass=NonDeterminist,
            NeighborClass=MyNeighborhood1, params: Dict = None) -> Solution:
        '''
        Exécute la recherche locale premier améliorant.
        @param instance:      instance du problème
        @param InitClass:     classe d'heuristique pour la solution initiale
        @param NeighborClass: classe de voisinage utilisée
        @param params:        peut contenir 'max_iterations' et paramètres
                              de InitClass ('k', 'seed')
        @return:              meilleure solution trouvée (optimum local)
        '''
        p              = {**self._params, **(params or {})}
        max_iterations = p.get('max_iterations', 500)

        # --- Solution initiale ---
        sol = InitClass().run(instance, p)

        neighborhood = NeighborClass(instance)

        # --- Descente premier améliorant ---
        for _ in range(max_iterations):
            voisin = neighborhood.first_better_neighbor(sol)
            if voisin is sol:
                # Aucun voisin améliorant → optimum local atteint
                break
            sol = voisin

        return sol


class BestNeighborLocalSearch(Heuristic):
    '''
    Recherche locale « meilleur améliorant » (Best Improvement).

    Algorithme :
    1. Générer une solution initiale avec NonDeterminist.
    2. À chaque itération, explorer les DEUX voisinages (MyNeighborhood1
       et MyNeighborhood2) et choisir le meilleur voisin global.
    3. Remplacer la solution courante si ce meilleur voisin améliore.
    4. S'arrêter quand aucun voisin n'améliore ou que la limite
       d'itérations est atteinte.

    Paramètres :
      - max_iterations (int) : nombre maximum d'itérations (défaut : 100)
    '''

    def __init__(self, params: Dict = None):
        '''
        Constructeur.
        @param params: peut contenir 'max_iterations' (int)
        '''
        super().__init__(params)

    def run(self, instance: Instance, InitClass=NonDeterminist,
            NeighborClass=MyNeighborhood1, params: Dict = None) -> Solution:
        '''
        Exécute la recherche locale meilleur améliorant (double voisinage).
        @param instance:      instance du problème
        @param InitClass:     classe d'heuristique pour la solution initiale
        @param NeighborClass: voisinage principal (MyNeighborhood1 par défaut)
        @param params:        peut contenir 'max_iterations' et paramètres
                              de InitClass
        @return:              meilleure solution trouvée (optimum local)
        '''
        p              = {**self._params, **(params or {})}
        max_iterations = p.get('max_iterations', 100)

        # --- Solution initiale ---
        sol = InitClass().run(instance, p)

        voisinage1 = MyNeighborhood1(instance)
        voisinage2 = MyNeighborhood2(instance)

        # --- Descente meilleur améliorant (double voisinage) ---
        for _ in range(max_iterations):
            meilleur1 = voisinage1.best_neighbor(sol)
            meilleur2 = voisinage2.best_neighbor(sol)

            # Choisir le meilleur des deux voisinages
            if meilleur1.objective <= meilleur2.objective:
                meilleur = meilleur1
            else:
                meilleur = meilleur2

            if meilleur is sol or meilleur.objective >= sol.objective:
                # Aucun voisin améliorant → optimum local atteint
                break
            sol = meilleur

        return sol


# ---------------------------------------------------------------------------
# Script de démonstration (exécution directe)
# ---------------------------------------------------------------------------

if __name__ == "__main__":  # pragma: no cover
    from src.scheduling.tests.test_utils import TEST_FOLDER_DATA
    from src.scheduling.instance.instance import Instance
    import os

    inst = Instance.from_file(TEST_FOLDER_DATA + os.path.sep + "jsp1")

    print("=== FirstNeighborLocalSearch ===")
    heur1 = FirstNeighborLocalSearch()
    sol1  = heur1.run(inst, NonDeterminist, MyNeighborhood1)
    print(sol1)

    print("\n=== BestNeighborLocalSearch ===")
    heur2 = BestNeighborLocalSearch()
    sol2  = heur2.run(inst, NonDeterminist, MyNeighborhood1)
    print(sol2)

    chart = sol2.gantt("tab20")
    chart.savefig("gantt.png")
    print("\nGantt sauvegardé dans gantt.png")
