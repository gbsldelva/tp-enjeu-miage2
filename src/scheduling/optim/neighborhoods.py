'''
Voisinages de solutions pour la recherche locale.

Référence :
  Nowicki, E. & Smutnicki, C. (1996). A fast taboo search algorithm for
  the job shop problem. Management Science, 42(6), 797–813.
  — Pour l'idée générale des voisinages d'échange dans le Job-Shop.

@author: Vassilissa Lehoux
'''
from typing import Dict, List, Tuple

from src.scheduling.instance.instance import Instance
from src.scheduling.solution import Solution


class Neighborhood(object):
    '''
    Classe de base pour les voisinages de solutions.
    Ne pas modifier.
    '''

    def __init__(self, instance: Instance, params: Dict = None):
        '''
        Constructeur.
        @param instance: instance du problème
        @param params:   paramètres du voisinage
        '''
        self._instance = instance

    def best_neighbor(self, sol: Solution) -> Solution:
        '''
        Retourne la meilleure solution dans le voisinage de sol
        (peut être sol elle-même si aucun voisin n'est meilleur).
        '''
        raise NotImplementedError  # pragma: no cover

    def first_better_neighbor(self, sol: Solution) -> Solution:
        '''
        Retourne le premier voisin de sol qui améliore la valeur objectif,
        ou sol elle-même si aucun voisin n'est meilleur.
        '''
        raise NotImplementedError  # pragma: no cover

    # ------------------------------------------------------------------
    # Méthodes utilitaires partagées
    # ------------------------------------------------------------------

    def _get_schedule_sequence(self, sol: Solution) -> List[Tuple[int, int]]:
        '''
        Extrait la séquence de décisions de la solution sous la forme
        d'une liste de (operation_id, machine_id) triée par heure de début.
        S'appuie sur le snapshot de la solution (indépendant de l'état
        courant de l'instance) si elle est figée.
        '''
        return sol.schedule_sequence

    def _rebuild_from_sequence(self, sequence: List[Tuple[int, int]]) -> Solution:
        '''
        Reconstruit une solution en planifiant les opérations dans l'ordre
        de la séquence donnée, tout en respectant les contraintes de précédence
        (une opération ne peut être planifiée que si ses prédécesseurs le sont).

        La solution reconstruite est fermée (machines éteintes au plus tôt)
        puis figée, ce qui la rend indépendante de l'état partagé de l'instance.

        @param sequence: liste de (operation_id, machine_id)
        @return:         nouvelle Solution complète et figée
        '''
        new_sol = Solution(self._instance)
        new_sol.apply_sequence(sequence)
        return new_sol


# ===========================================================================
# Voisinage 1 : Réaffectation de machine (MachineReassignment)
# ===========================================================================

class MyNeighborhood1(Neighborhood):
    '''
    Voisinage par réaffectation de machine.

    Pour chaque opération planifiée, on essaie de l'affecter à chacune
    de ses machines alternatives (toutes sauf la machine actuelle).
    Pour chaque remplacement, on reconstruit la solution complète en
    rejouant la même séquence d'ordonnancement avec la nouvelle affectation.

    Taille du voisinage : O(N × M) où N = nb opérations, M = nb machines.
    Le voisinage est polynomial et couvre toutes les affectations possibles
    (connexe dans l'espace des solutions).
    '''

    def __init__(self, instance: Instance, params: Dict = None):
        '''
        Constructeur.
        @param instance: instance du problème
        @param params:   non utilisé
        '''
        super().__init__(instance, params)

    def best_neighbor(self, sol: Solution) -> Solution:
        '''
        Explore tous les voisins et retourne le meilleur.
        Si aucun voisin n'améliore, retourne sol.
        '''
        sequence      = self._get_schedule_sequence(sol)
        meilleure_sol = sol
        meilleur_obj  = sol.objective   # figé avant toute reconstruction

        for i, (op_id, machine_id_courant) in enumerate(sequence):
            op = self._instance.get_operation(op_id)
            for machine_id_alt in op._machine_options:
                if machine_id_alt == machine_id_courant:
                    continue
                # Nouvelle séquence avec la machine alternative
                new_sequence = sequence[:i] + [(op_id, machine_id_alt)] + sequence[i+1:]
                new_sol = self._rebuild_from_sequence(new_sequence)
                if new_sol.is_feasible and new_sol.objective < meilleur_obj:
                    meilleure_sol = new_sol
                    meilleur_obj  = new_sol.objective

        return meilleure_sol

    def first_better_neighbor(self, sol: Solution) -> Solution:
        '''
        Retourne le premier voisin qui améliore sol, ou sol si aucun ne
        l'améliore.
        '''
        sequence      = self._get_schedule_sequence(sol)
        objectif_ref  = sol.objective

        for i, (op_id, machine_id_courant) in enumerate(sequence):
            op = self._instance.get_operation(op_id)
            for machine_id_alt in op._machine_options:
                if machine_id_alt == machine_id_courant:
                    continue
                new_sequence = sequence[:i] + [(op_id, machine_id_alt)] + sequence[i+1:]
                new_sol = self._rebuild_from_sequence(new_sequence)
                if new_sol.is_feasible and new_sol.objective < objectif_ref:
                    return new_sol  # premier améliorant trouvé

        return sol


# ===========================================================================
# Voisinage 2 : Échange de l'ordre de deux opérations (OperationSwap)
# ===========================================================================

class MyNeighborhood2(Neighborhood):
    '''
    Voisinage par échange de l'ordre de deux opérations.

    On permute la position de deux opérations consécutives (dans la
    séquence de planification) qui appartiennent à des jobs différents.
    Cela change l'ordre dans lequel les ressources sont sollicitées sans
    toucher aux affectations de machines.

    On ne permute que des opérations de jobs différents (les contraintes
    de précédence intra-job sont immuables).

    Taille du voisinage : O(N) — on n'examine que les N-1 paires d'opérations
    CONSÉCUTIVES dans la séquence (et non toutes les paires). Le voisinage est
    donc polynomial mais pas nécessairement connexe (atteindre certaines
    permutations peut passer par des solutions infaisables).
    '''

    def __init__(self, instance: Instance, params: Dict = None):
        '''
        Constructeur.
        @param instance: instance du problème
        @param params:   non utilisé
        '''
        super().__init__(instance, params)

    def best_neighbor(self, sol: Solution) -> Solution:
        '''
        Explore toutes les permutations de paires d'opérations de jobs
        différents et retourne la meilleure solution trouvée.
        '''
        sequence      = self._get_schedule_sequence(sol)
        meilleure_sol = sol
        meilleur_obj  = sol.objective   # figé avant toute reconstruction

        for i in range(len(sequence) - 1):
            op_i = self._instance.get_operation(sequence[i][0])
            op_j = self._instance.get_operation(sequence[i+1][0])
            # Permuter seulement si les deux ops appartiennent à des jobs différents
            if op_i.job_id == op_j.job_id:
                continue
            new_sequence = (sequence[:i]
                            + [sequence[i+1], sequence[i]]
                            + sequence[i+2:])
            new_sol = self._rebuild_from_sequence(new_sequence)
            if new_sol.is_feasible and new_sol.objective < meilleur_obj:
                meilleure_sol = new_sol
                meilleur_obj  = new_sol.objective

        return meilleure_sol

    def first_better_neighbor(self, sol: Solution) -> Solution:
        '''
        Retourne la première permutation améliorante, ou sol si aucune
        n'améliore.
        '''
        sequence     = self._get_schedule_sequence(sol)
        objectif_ref = sol.objective

        for i in range(len(sequence) - 1):
            op_i = self._instance.get_operation(sequence[i][0])
            op_j = self._instance.get_operation(sequence[i+1][0])
            if op_i.job_id == op_j.job_id:
                continue
            new_sequence = (sequence[:i]
                            + [sequence[i+1], sequence[i]]
                            + sequence[i+2:])
            new_sol = self._rebuild_from_sequence(new_sequence)
            if new_sol.is_feasible and new_sol.objective < objectif_ref:
                return new_sol

        return sol
