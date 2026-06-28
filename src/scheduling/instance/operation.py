'''
Opération d'un job.
Sa durée et sa consommation d'énergie dépendent de la machine sur laquelle
elle est exécutée.
Quand l'opération est planifiée, ses informations de planification sont mises à jour.

@author: Vassilissa Lehoux
'''
from typing import List


class OperationScheduleInfo(object):
    '''
    Informations connues lorsque l'opération est planifiée sur une machine.
    Classe de données simple (pas de logique métier).
    '''

    def __init__(self, machine_id: int, schedule_time: int, duration: int,
                 energy_consumption: int):
        '''
        Constructeur.
        @param machine_id:          identifiant de la machine choisie
        @param schedule_time:       heure de début d'exécution
        @param duration:            durée de traitement sur cette machine
        @param energy_consumption:  énergie consommée sur cette machine
        '''
        self._machine_id   = machine_id
        self._start_time   = schedule_time
        self._duration     = duration
        self._energy       = energy_consumption


class Operation(object):
    '''
    Opération d'un job dans le problème d'ordonnancement flexible.
    Une opération peut être exécutée sur plusieurs machines ; ses
    caractéristiques (durée, énergie) dépendent du choix de la machine.
    '''

    def __init__(self, job_id: int, operation_id: int):
        '''
        Constructeur.
        @param job_id:        identifiant du job auquel appartient l'opération
        @param operation_id:  identifiant global de l'opération
        '''
        self._job_id         = job_id
        self._operation_id   = operation_id
        self._schedule_info  = None          # OperationScheduleInfo ou None
        self._predecessors   = []            # opérations devant se terminer avant
        self._successors     = []            # opérations qui dépendent de celle-ci
        # Options de machines : {machine_id: (processing_time, energy_consumption)}
        self._machine_options = {}

    # ------------------------------------------------------------------
    # Représentations textuelles
    # ------------------------------------------------------------------

    def __str__(self):
        '''
        Retourne une représentation textuelle de l'opération.
        '''
        base_str = f"O{self.operation_id}_J{self.job_id}"
        if self._schedule_info:
            return base_str + f"_M{self.assigned_to}_ci{self.processing_time}_e{self.energy}"
        return base_str

    def __repr__(self):
        return str(self)

    # ------------------------------------------------------------------
    # Ajout des options machine (appelé par Instance.from_file)
    # ------------------------------------------------------------------

    def add_machine_option(self, machine_id: int, processing_time: int,
                           energy_consumption: int):
        '''
        Enregistre la durée et l'énergie pour une machine éligible.
        @param machine_id:          identifiant de la machine
        @param processing_time:     durée de traitement sur cette machine
        @param energy_consumption:  énergie consommée sur cette machine
        '''
        self._machine_options[machine_id] = (processing_time, energy_consumption)

    # ------------------------------------------------------------------
    # Gestion des précédences
    # ------------------------------------------------------------------

    def add_predecessor(self, operation):
        '''
        Ajoute une opération prédécesseur (doit être terminée avant le début
        de cette opération).
        '''
        if operation not in self._predecessors:
            self._predecessors.append(operation)

    def add_successor(self, operation):
        '''
        Ajoute une opération successeur (ne peut démarrer qu'après la fin
        de cette opération).
        '''
        if operation not in self._successors:
            self._successors.append(operation)

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def reset(self):
        '''
        Supprime les informations de planification (l'opération redevient
        non planifiée).
        '''
        self._schedule_info = None

    # ------------------------------------------------------------------
    # Propriétés de base
    # ------------------------------------------------------------------

    @property
    def operation_id(self) -> int:
        '''Retourne l'identifiant de l'opération.'''
        return self._operation_id

    @property
    def job_id(self) -> int:
        '''Retourne l'identifiant du job auquel appartient l'opération.'''
        return self._job_id

    @property
    def predecessors(self) -> List:
        '''Retourne la liste des opérations prédécesseurs.'''
        return self._predecessors

    @property
    def successors(self) -> List:
        '''Retourne la liste des opérations successeurs.'''
        return self._successors

    # ------------------------------------------------------------------
    # Propriétés de planification
    # ------------------------------------------------------------------

    @property
    def assigned(self) -> bool:
        '''Retourne True si l'opération est planifiée, False sinon.'''
        return self._schedule_info is not None

    @property
    def assigned_to(self) -> int:
        '''
        Retourne l'identifiant de la machine sur laquelle l'opération est
        planifiée, ou -1 si elle ne l'est pas encore.
        '''
        if self._schedule_info is None:
            return -1
        return self._schedule_info._machine_id

    @property
    def processing_time(self) -> int:
        '''
        Retourne la durée de traitement si l'opération est planifiée,
        -1 sinon.
        '''
        if self._schedule_info is None:
            return -1
        return self._schedule_info._duration

    @property
    def start_time(self) -> int:
        '''
        Retourne l'heure de début si l'opération est planifiée,
        -1 sinon.
        '''
        if self._schedule_info is None:
            return -1
        return self._schedule_info._start_time

    @property
    def end_time(self) -> int:
        '''
        Retourne l'heure de fin si l'opération est planifiée,
        -1 sinon.
        '''
        if self._schedule_info is None:
            return -1
        return self._schedule_info._start_time + self._schedule_info._duration

    @property
    def energy(self) -> int:
        '''
        Retourne la consommation d'énergie si l'opération est planifiée,
        -1 sinon.
        '''
        if self._schedule_info is None:
            return -1
        return self._schedule_info._energy

    # ------------------------------------------------------------------
    # Contraintes de précédence
    # ------------------------------------------------------------------

    def is_ready(self, at_time: int) -> bool:
        '''
        Retourne True si tous les prédécesseurs sont planifiés ET terminés
        avant ou à at_time.
        '''
        return all(
            pred.assigned and pred.end_time <= at_time
            for pred in self._predecessors
        )

    @property
    def min_start_time(self) -> int:
        '''
        Heure minimale de démarrage imposée par les contraintes de précédence.
        Retourne le maximum des heures de fin des prédécesseurs (0 si aucun).
        '''
        if not self._predecessors:
            return 0
        return max(pred.end_time for pred in self._predecessors)

    # ------------------------------------------------------------------
    # Planification
    # ------------------------------------------------------------------

    def schedule(self, machine_id: int, at_time: int,
                 check_success: bool = True) -> bool:
        '''
        Planifie l'opération sur la machine donnée à l'heure at_time.
        @param machine_id:     machine choisie (doit être dans _machine_options)
        @param at_time:        heure de début souhaitée
        @param check_success:  si True, vérifie la cohérence des précédences
        @return:               True si la planification a réussi, False sinon
        '''
        if check_success:
            if not self.is_ready(at_time):
                return False
        pt, energy = self._machine_options[machine_id]
        self._schedule_info = OperationScheduleInfo(machine_id, at_time, pt, energy)
        return True

    def schedule_at_min_time(self, machine_id: int, min_time: int) -> bool:
        '''
        Planifie l'opération au plus tôt à partir de min_time (en respectant
        aussi les contraintes de précédence).
        @return: True si la planification a réussi, False si la machine n'est
                 pas éligible.
        '''
        if machine_id not in self._machine_options:
            return False
        actual_time = max(min_time, self.min_start_time)
        return self.schedule(machine_id, actual_time, check_success=False)
