'''
Heuristiques constructives : construisent une solution de zéro.

Référence :
  Pinedo, M. (2016). Scheduling: Theory, Algorithms, and Systems (5th ed.).
  Springer. — Chapitre 2 : algorithmes gloutons pour le Job-Shop.

@author: Vassilissa Lehoux
'''
from typing import Dict, List, Tuple
import random

from src.scheduling.instance.instance import Instance
from src.scheduling.instance.machine import Machine
from src.scheduling.instance.operation import Operation
from src.scheduling.solution import Solution
from src.scheduling.optim.heuristics import Heuristic


def _estimated_start(op: Operation, machine: Machine) -> int:
    '''
    Estime l'heure de début effective d'une opération sur une machine
    sans modifier l'état de la machine.
    Reproduit la logique de Machine.add_operation().
    '''
    min_start = op.min_start_time
    return machine.estimate_start_time(min_start)


def _build_candidates(available_ops, instance: Instance) -> List[Tuple]:
    '''
    Construit la liste de tous les couples (op, machine_id, pt, energy,
    faisable) en estimant les heures de début pour filtrer les options
    qui violeraient l'échéance de la machine.

    Un couple est faisable si :
        start_estimé + pt + teardown_time ≤ end_time
    '''
    candidats = []
    for op in available_ops:
        for machine_id, (pt, energy) in op._machine_options.items():
            machine   = instance.get_machine(machine_id)
            start_est = _estimated_start(op, machine)
            faisable  = (start_est + pt + machine.tear_down_time
                         <= machine._end_time)
            candidats.append((op, machine_id, pt, energy, faisable))
    return candidats


class Greedy(Heuristic):
    '''
    Algorithme glouton déterministe.

    Principe (glouton) : à chaque étape, on choisit le couple
    (opération disponible, machine) qui minimise la consommation
    d'énergie de l'opération sur cette machine, en favorisant d'abord
    les options réalisables (qui respectent l'échéance de la machine).
    En cas d'égalité on départage par (job_id, operation_id) pour
    garantir la reproductibilité.

    Complexité : O(N² x M) avec N = nb opérations, M = nb machines.
    '''

    def __init__(self, params: Dict = None):
        '''
        Constructeur.
        @param params: dictionnaire de paramètres (non utilisé dans cette
                       version, réservé pour extensions futures)
        '''
        super().__init__(params)

    def run(self, instance: Instance, params: Dict = None) -> Solution:
        '''
        Construit une solution gloutonne déterministe.
        @param instance: instance du problème
        @param params:   paramètres (ignorés ici)
        @return:         solution construite
        '''
        sol = Solution(instance)
        sol.reset()

        while sol.available_operations:
            candidats = _build_candidates(sol.available_operations, instance)

            # Préférer les candidats réalisables ; si aucun, tous acceptés
            faisables = [c for c in candidats if c[4]]
            pool = faisables if faisables else candidats

            # Choisir le couple de moindre énergie (tie-break par job_id, op_id)
            meilleur = min(
                pool,
                key=lambda c: (c[3], c[0].job_id, c[0].operation_id)
            )
            op, machine_id, _, _, _ = meilleur
            sol.schedule(op, instance.get_machine(machine_id))

        # Éteindre les machines au plus tôt puis figer la solution
        # (la rend indépendante de l'état partagé de l'instance).
        sol.close_machines()
        sol.freeze()
        return sol


class NonDeterminist(Heuristic):
    '''
    Heuristique non déterministe (type GRASP — Greedy Randomized Adaptive
    Search Procedure).

    Référence :
      Feo, T.A. & Resende, M.G.C. (1995). Greedy Randomized Adaptive
      Search Procedures. Journal of Global Optimization, 6(2), 109–133.

    Principe : à chaque étape, on construit une liste restreinte de
    candidats (les k meilleurs couples op/machine par énergie), puis on
    en choisit un au hasard. Cela introduit de la diversité tout en
    gardant un biais vers les bonnes solutions.

    Paramètres :
      - k    (int)  : taille de la liste restreinte (défaut : 3)
      - seed (int)  : graine aléatoire optionnelle pour la reproductibilité
    '''

    def __init__(self, params: Dict = None):
        '''
        Constructeur.
        @param params: peut contenir 'k' (int) et 'seed' (int)
        '''
        super().__init__(params)

    def run(self, instance: Instance, params: Dict = None) -> Solution:
        '''
        Construit une solution non déterministe.
        @param instance: instance du problème
        @param params:   peut contenir 'k' et 'seed' (surcharge le constructeur)
        @return:         solution construite
        '''
        p = {**self._params, **(params or {})}
        k    = p.get('k', 5)
        seed = p.get('seed', None)
        if seed is not None:
            random.seed(seed)

        sol = Solution(instance)
        sol.reset()

        while sol.available_operations:
            # Construire la liste élargie (op, machine_id, pt, energy, faisable)
            candidats = _build_candidates(sol.available_operations, instance)

            # Préférer les candidats réalisables
            faisables = [c for c in candidats if c[4]]
            pool = faisables if faisables else candidats

            # Trier par énergie et garder les k meilleurs
            pool.sort(key=lambda c: c[3])
            top_k = pool[:k]

            # Choisir au hasard parmi le top-k
            op, machine_id, _, _, _ = random.choice(top_k)
            sol.schedule(op, instance.get_machine(machine_id))

        # Éteindre les machines au plus tôt puis figer la solution.
        sol.close_machines()
        sol.freeze()
        return sol


# ---------------------------------------------------------------------------
# Script de démonstration (exécution directe)
# ---------------------------------------------------------------------------

if __name__ == "__main__":  # pragma: no cover
    from src.scheduling.tests.test_utils import TEST_FOLDER_DATA
    import os

    inst = Instance.from_file(TEST_FOLDER_DATA + os.path.sep + "jsp1")
    heur = NonDeterminist()
    sol  = heur.run(inst)
    print(sol)
    chart = sol.gantt("tab20")
    chart.savefig("gantt.png")
    print("Gantt sauvegardé dans gantt.png")
