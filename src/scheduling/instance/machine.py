'''
Machine sur laquelle les opérations sont exécutées.

@author: Vassilissa Lehoux
'''
from typing import List
from src.scheduling.instance.operation import Operation


class Machine(object):
    '''
    Représente une machine dans le problème d'ordonnancement.

    Une machine est éteinte au début du planning et doit être allumée
    (setup) avant toute opération. Elle consomme un minimum d'énergie
    lorsqu'elle est allumée mais sans opération (idle). Elle peut être
    allumée et éteinte plusieurs fois.

    Modèle de sessions :
    - À chaque démarrage, start_times reçoit l'instant de mise en route,
      stop_times reçoit end_time (la machine restera allumée jusqu'à sa
      fin de planning sauf arrêt explicite).
    - Chaque session conserve ses propres opérations pour le calcul
      d'énergie (sessions_ops).
    '''

    def __init__(self, machine_id: int, set_up_time: int, set_up_energy: int,
                 tear_down_time: int, tear_down_energy: int,
                 min_consumption: int, end_time: int):
        '''
        Constructeur.
        La machine est éteinte en début de planning.
        @param end_time: échéance de la machine — elle doit être éteinte avant
                         ce moment.
        '''
        self._machine_id       = machine_id
        self._set_up_time      = set_up_time
        self._set_up_energy    = set_up_energy
        self._tear_down_time   = tear_down_time
        self._tear_down_energy = tear_down_energy
        self._min_consumption  = min_consumption
        self._end_time         = end_time

        # État courant
        self._running          = False   # True si une session est ouverte
        self._available_time   = 0       # fin de la dernière opération planifiée
        self._scheduled_operations: List[Operation] = []

        # Gestion des sessions multiples (allumage/extinction)
        self._start_times: List[int]       = []   # instants de démarrage
        self._stop_times: List[int]        = []   # instants d'arrêt
        self._sessions_ops: List[List]     = []   # opérations par session

    def reset(self):
        '''
        Remet la machine dans son état initial (aucune opération planifiée).
        '''
        self._running                = False
        self._available_time         = 0
        self._scheduled_operations   = []
        self._start_times            = []
        self._stop_times             = []
        self._sessions_ops           = []

    # ------------------------------------------------------------------
    # Propriétés simples
    # ------------------------------------------------------------------

    @property
    def machine_id(self) -> int:
        '''Retourne l'identifiant de la machine.'''
        return self._machine_id

    @property
    def set_up_time(self) -> int:
        '''Retourne la durée du démarrage (setup).'''
        return self._set_up_time

    @property
    def tear_down_time(self) -> int:
        '''Retourne la durée de l'arrêt (teardown).'''
        return self._tear_down_time

    @property
    def end_time(self) -> int:
        '''Retourne l'échéance de la machine (instant limite d'extinction).'''
        return self._end_time

    @property
    def scheduled_operations(self) -> List[Operation]:
        '''Retourne la liste de toutes les opérations planifiées sur la machine.'''
        return self._scheduled_operations

    @property
    def start_times(self) -> List[int]:
        '''
        Retourne les instants de démarrage de la machine (dans l'ordre
        chronologique).
        '''
        return self._start_times

    @property
    def stop_times(self) -> List[int]:
        '''
        Retourne les instants d'arrêt de la machine (dans l'ordre
        chronologique).
        '''
        return self._stop_times

    @property
    def available_time(self) -> int:
        '''
        Retourne le premier instant à partir duquel la machine peut accepter
        une nouvelle opération (fin de la dernière opération ou du dernier
        setup).
        '''
        return self._available_time

    @property
    def running(self) -> bool:
        '''Retourne True si une session de la machine est ouverte (allumée).'''
        return self._running

    # ------------------------------------------------------------------
    # Ajout d'une opération (cœur du comportement)
    # ------------------------------------------------------------------

    def _should_interrupt(self, next_start_time: int) -> bool:
        '''
        Retourne True si la machine doit être interrompue avant la prochaine
        opération.

        Une interruption automatique est créée si la plage d'inactivité est
        suffisante pour effectuer un teardown complet puis un nouveau setup,
        sans retarder le démarrage de la prochaine opération. Cela évite de
        garder la machine allumée inutilement pendant les grands trous.
        '''
        if not self._running:
            return False
        gap = next_start_time - self._available_time
        if gap < self._tear_down_time + self._set_up_time:
            return False
        next_machine_start = max(
            self._available_time + self._tear_down_time,
            next_start_time - self._set_up_time
        )
        return next_machine_start < self._end_time

    def estimate_start_time(self, start_time: int) -> int:
        '''
        Estime l'heure de début effective d'une prochaine opération sans
        modifier l'état de la machine.
        '''
        if self._should_interrupt(start_time):
            previous_stop = self._available_time + self._tear_down_time
            machine_start = max(previous_stop, start_time - self._set_up_time)
            return max(machine_start + self._set_up_time, start_time)

        if not self._running:
            previous_stop = self._stop_times[-1] if self._stop_times else 0
            machine_start = max(previous_stop, start_time - self._set_up_time, 0)
            return max(machine_start + self._set_up_time, start_time)

        return max(start_time, self._available_time)

    def add_operation(self, operation: Operation, start_time: int) -> int:
        '''
        Ajoute une opération à la fin du planning de la machine, au plus tôt
        à partir de start_time.
        Démarre la machine (setup) si elle est éteinte.
        @param operation:   opération à planifier
        @param start_time:  contrainte minimale de démarrage (issues des
                            précédences ou d'une contrainte externe)
        @return:            heure de début effective de l'opération
        '''
        if self._should_interrupt(start_time):
            self.stop(self._available_time)

        if not self._running:
            # Démarrer la machine le plus tard possible (minimise l'idle au
            # début) : le démarrage se termine juste à temps pour start_time.
            previous_stop = self._stop_times[-1] if self._stop_times else 0
            machine_start = max(previous_stop, start_time - self._set_up_time, 0)
            actual_start  = machine_start + self._set_up_time
            # Si start_time < set_up_time, la machine démarre en t=0 et
            # l'opération attend la fin du setup.
            actual_start  = max(actual_start, start_time)

            self._start_times.append(machine_start)
            # Par défaut la machine fonctionne jusqu'à end_time (échéance)
            self._stop_times.append(self._end_time)
            self._sessions_ops.append([])
            self._running        = True
            self._available_time = actual_start
        else:
            # Machine déjà en route : l'opération démarre dès que possible
            actual_start = max(start_time, self._available_time)

        # Planifier l'opération (sans re-vérifier les précédences ici)
        operation.schedule(self._machine_id, actual_start, check_success=False)

        # Enregistrement
        self._sessions_ops[-1].append(operation)
        self._scheduled_operations.append(operation)
        self._available_time = actual_start + operation.processing_time

        return actual_start

    def stop(self, at_time: int):
        '''
        Lance l'arrêt de la machine à l'instant at_time.
        Utile pour la stratégie multi-session (allumer/éteindre pour économiser
        de l'énergie pendant les grandes plages d'inactivité).
        @param at_time: instant où le teardown commence (doit être ≥ à la fin
                        de la dernière opération planifiée). L'instant stocké
                        dans stop_times est l'instant où la machine est
                        complètement éteinte, donc at_time + tear_down_time.
        '''
        assert self._running, "Impossible d'arrêter une machine déjà éteinte."
        assert at_time >= self._available_time, (
            f"Impossible d'arrêter la machine à t={at_time} : dernière opération "
            f"termine à t={self._available_time}."
        )
        self._stop_times[-1] = at_time + self._tear_down_time
        self._running        = False
        # La prochaine available_time ne change pas : la machine est éteinte,
        # add_operation redémarrera au besoin.

    def close(self):
        '''
        Ferme la session courante au plus tôt : le teardown démarre juste après
        la dernière opération planifiée (à available_time).

        Par défaut, add_operation laisse la machine allumée jusqu'à son échéance
        (end_time), ce qui maximise l'idle de fin de session. close() supprime
        cet idle inutile : la machine est au moins allumée en début de planning
        et éteinte dès la fin de sa dernière opération (cf. énoncé du TP).
        '''
        if not self._running:
            return
        self.stop(self._available_time)

    # ------------------------------------------------------------------
    # Métriques
    # ------------------------------------------------------------------

    @property
    def working_time(self) -> int:
        '''
        Durée totale pendant laquelle la machine est allumée
        (somme des durées de toutes les sessions).
        '''
        return sum(
            stop - start
            for start, stop in zip(self._start_times, self._stop_times)
        )

    @property
    def total_energy_consumption(self) -> float:
        '''
        Consommation totale d'énergie sur toutes les sessions.

        Formule par session (conforme au modèle du squelette : le terme
        d'inactivité est min_consumption × durée_idle, sans conversion
        d'unité — c'est l'interprétation littérale attendue par les tests) :
          E = setup_energy + teardown_energy
            + min_consumption × durée_idle
            + Σ op.energy
        où durée_idle = (stop - start) - setup_time - teardown_time - Σ pt
        '''
        total = 0.0
        for i, (start, stop) in enumerate(zip(self._start_times, self._stop_times)):
            session_ops = self._sessions_ops[i]
            total_pt    = sum(op.processing_time for op in session_ops)
            idle_time   = (stop - start) - self._set_up_time - self._tear_down_time - total_pt
            idle_time   = max(0, idle_time)   # sécurité (ne doit pas être négatif)

            total += (
                self._set_up_energy
                + self._tear_down_energy
                + self._min_consumption * idle_time
                + sum(op.energy for op in session_ops)
            )
        return total

    # ------------------------------------------------------------------
    # Représentations textuelles
    # ------------------------------------------------------------------

    def __str__(self):
        return f"M{self._machine_id}"

    def __repr__(self):
        return str(self)
