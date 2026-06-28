'''
Job. Il est composé de plusieurs opérations devant être exécutées
dans un ordre strict (contrainte de précédence).

@author: Vassilissa Lehoux
'''
from typing import List

from src.scheduling.instance.operation import Operation


class Job(object):
    '''
    Représente un job dans le problème d'ordonnancement.
    Contient une liste ordonnée d'opérations et mémorise laquelle
    est la prochaine à planifier.
    '''

    def __init__(self, job_id: int):
        '''
        Constructeur.
        @param job_id: identifiant unique du job
        '''
        self._job_id      = job_id
        self._operations: List[Operation] = []
        self._next_index  = 0   # index de la prochaine opération à planifier

    # ------------------------------------------------------------------
    # Propriétés de base
    # ------------------------------------------------------------------

    @property
    def job_id(self) -> int:
        '''Retourne l'identifiant du job.'''
        return self._job_id

    @property
    def operations(self) -> List[Operation]:
        '''Retourne la liste ordonnée des opérations du job.'''
        return self._operations

    @property
    def operation_nb(self) -> int:
        '''Retourne le nombre d'opérations du job.'''
        return len(self._operations)

    # ------------------------------------------------------------------
    # Gestion des opérations
    # ------------------------------------------------------------------

    def add_operation(self, operation: Operation):
        '''
        Ajoute une opération à la fin de la liste du job et établit
        automatiquement le lien prédécesseur/successeur avec la dernière
        opération déjà présente.
        @param operation: opération à ajouter (dans l'ordre d'exécution)
        '''
        if self._operations:
            # La nouvelle opération dépend de la précédente
            prev_op = self._operations[-1]
            prev_op.add_successor(operation)
            operation.add_predecessor(prev_op)
        self._operations.append(operation)

    # ------------------------------------------------------------------
    # État de planification
    # ------------------------------------------------------------------

    def reset(self):
        '''
        Remet le pointeur de prochaine opération à zéro (aucune opération
        n'est considérée comme planifiée du point de vue du job).
        Note : le reset des OperationScheduleInfo est géré par Solution.reset().
        '''
        self._next_index = 0

    @property
    def next_operation(self) -> Operation:
        '''
        Retourne la prochaine opération à planifier.
        Retourne None si toutes les opérations sont planifiées.
        '''
        if self._next_index < len(self._operations):
            return self._operations[self._next_index]
        return None

    def schedule_operation(self):
        '''
        Marque la prochaine opération comme planifiée en avançant le
        pointeur d'index.
        '''
        if self._next_index < len(self._operations):
            self._next_index += 1

    @property
    def planned(self) -> bool:
        '''
        Retourne True si toutes les opérations du job sont planifiées.
        '''
        return self._next_index >= len(self._operations)

    # ------------------------------------------------------------------
    # Métriques
    # ------------------------------------------------------------------

    @property
    def completion_time(self) -> int:
        '''
        Retourne la date de fin du job (fin de la dernière opération planifiée).
        Retourne -1 si la dernière opération n'est pas encore planifiée.
        '''
        if not self._operations:
            return -1
        last_op = self._operations[-1]
        if not last_op.assigned:
            return -1
        return last_op.end_time
