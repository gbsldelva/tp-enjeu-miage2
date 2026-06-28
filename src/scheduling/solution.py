'''
Objet Solution pour le problème d'ordonnancement à contraintes énergétiques.

@author: Vassilissa Lehoux
'''
import os
import csv
from typing import List

from matplotlib import pyplot as plt
from matplotlib import colormaps

from src.scheduling.instance.instance import Instance
from src.scheduling.instance.operation import Operation
from src.scheduling.instance.machine import Machine


class Solution(object):
    '''
    Encapsule une solution complète du problème d'ordonnancement.
    Une solution associe à chaque opération une machine et une heure
    de démarrage tout en respectant les contraintes de précédence et
    les échéances des machines.
    '''

    def __init__(self, instance: Instance):
        '''
        Constructeur.
        @param instance: instance du problème à résoudre
        '''
        self._instance = instance
        # Snapshot figé de la solution (None tant qu'elle n'est pas figée).
        #
        # Problème résolu : l'état d'ordonnancement (machines/opérations) est
        # porté par les objets de l'Instance, partagés par toutes les Solution
        # construites sur cette instance. Sans snapshot, construire une nouvelle
        # solution écraserait l'état des précédentes et fausserait les
        # comparaisons d'objectif (bug d'aliasing). freeze() capture donc les
        # métriques et la séquence d'ordonnancement au moment où la solution est
        # active ; les lectures ultérieures s'appuient sur ce snapshot.
        self._cache = None

    # ------------------------------------------------------------------
    # Accesseur instance
    # ------------------------------------------------------------------

    @property
    def inst(self) -> Instance:
        '''Retourne l'instance associée à la solution.'''
        return self._instance

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def reset(self):
        '''
        Remet la solution à zéro : toutes les opérations et machines sont
        réinitialisées, les jobs repartent de leur première opération.
        '''
        for op in self._instance.operations:
            op.reset()
        for machine in self._instance.machines:
            machine.reset()
        for job in self._instance.jobs:
            job.reset()
        self._cache = None

    # ------------------------------------------------------------------
    # Opérations disponibles
    # ------------------------------------------------------------------

    @property
    def available_operations(self) -> List[Operation]:
        '''
        Retourne les opérations pouvant être planifiées maintenant :
        pour chaque job non terminé, sa prochaine opération (dont tous
        les prédécesseurs sont forcément planifiés par construction).
        '''
        result = []
        for job in self._instance.jobs:
            if not job.planned:
                result.append(job.next_operation)
        return result

    @property
    def all_operations(self) -> List[Operation]:
        '''Retourne toutes les opérations de l'instance.'''
        return self._instance.operations

    # ------------------------------------------------------------------
    # Planification d'une opération
    # ------------------------------------------------------------------

    def schedule(self, operation: Operation, machine: Machine):
        '''
        Planifie l'opération sur la machine donnée au plus tôt (en
        démarrant la machine si elle est éteinte).
        @param operation: opération disponible (doit être dans available_operations)
        @param machine:   machine choisie pour cette opération
        '''
        assert operation in self.available_operations, (
            f"L'opération {operation} n'est pas disponible pour la planification."
        )
        # Contrainte de précédence : l'opération ne peut démarrer qu'après
        # la fin de son prédécesseur (si applicable)
        min_start = operation.min_start_time
        machine.add_operation(operation, min_start)
        # Avancer le pointeur de planification du job
        self._instance.get_job(operation.job_id).schedule_operation()
        # Invalider le snapshot (la solution change)
        self._cache = None

    # ------------------------------------------------------------------
    # Snapshot : rend la solution indépendante de l'état partagé
    # ------------------------------------------------------------------

    def freeze(self):
        '''
        Fige la solution : capture la séquence d'ordonnancement et les
        métriques calculées à partir de l'état COURANT de l'instance.
        Doit être appelée lorsque cette solution est la solution active
        (l'état de l'instance correspond à cette solution).

        Une fois figée, toutes les métriques (objectif, Cmax, ΣCi, énergie,
        faisabilité) sont lues depuis le snapshot et ne dépendent plus des
        modifications ultérieures de l'instance.
        @return: self (pour chaînage)
        '''
        ops = sorted(
            (op for op in self._instance.operations if op.assigned),
            key=lambda op: op.start_time
        )
        feasible = self._compute_feasible()
        energy   = self._compute_energy()
        cmax     = self._compute_cmax()
        sum_ci   = self._compute_sum_ci()
        self._cache = {
            'sequence':  [(op.operation_id, op.assigned_to) for op in ops],
            'feasible':  feasible,
            'energy':    energy,
            'cmax':      cmax,
            'sum_ci':    sum_ci,
            'objective': self._aggregate(energy, cmax, sum_ci, feasible),
        }
        return self

    @property
    def schedule_sequence(self) -> List:
        '''
        Retourne la séquence d'ordonnancement (op_id, machine_id) de la
        solution, triée par heure de début. Lue depuis le snapshot si la
        solution est figée, sinon reconstruite depuis l'état courant.
        '''
        if self._cache is not None:
            return list(self._cache['sequence'])
        ops = sorted(
            (op for op in self._instance.operations if op.assigned),
            key=lambda op: op.start_time
        )
        return [(op.operation_id, op.assigned_to) for op in ops]

    def apply_sequence(self, sequence: List):
        '''
        Construit la solution en planifiant les opérations dans l'ordre de
        rang de la séquence donnée, tout en respectant les précédences
        (une opération n'est planifiée que lorsque ses prédécesseurs le sont).
        Ferme ensuite les machines au plus tôt puis fige la solution.
        @param sequence: liste de (operation_id, machine_id)
        @return:         self (pour chaînage)
        '''
        self.reset()
        rang   = {op_id: i for i, (op_id, _) in enumerate(sequence)}
        cible  = {op_id: machine_id for op_id, machine_id in sequence}

        while self.available_operations:
            op = min(
                self.available_operations,
                key=lambda o: rang.get(o.operation_id, float('inf'))
            )
            machine_id = cible.get(op.operation_id,
                                   next(iter(op._machine_options)))
            self.schedule(op, self._instance.get_machine(machine_id))

        self.close_machines()
        self.freeze()
        return self

    def close_machines(self):
        '''
        Éteint toutes les machines encore allumées juste après leur dernière
        opération (cf. Machine.close). Réduit l'énergie d'inactivité de fin
        de session sans modifier la faisabilité.
        '''
        for machine in self._instance.machines:
            machine.close()

    def restore(self):
        '''
        Réapplique le snapshot de la solution sur l'instance, de sorte que
        l'état de l'instance corresponde de nouveau à cette solution.
        Utile avant un affichage (gantt) ou un export (to_csv) lorsque
        d'autres solutions ont été construites entre-temps.
        '''
        if self._cache is not None:
            self.apply_sequence(self._cache['sequence'])

    # ------------------------------------------------------------------
    # Faisabilité
    # ------------------------------------------------------------------

    def _violations(self) -> int:
        '''
        Compte le nombre de contraintes violées (état courant de l'instance) :
          - chaque opération non planifiée compte pour une violation ;
          - chaque machine dont la dernière opération + teardown dépasse son
            échéance compte pour une violation.
        '''
        nb = sum(1 for op in self._instance.operations if not op.assigned)
        for machine in self._instance.machines:
            ops = machine.scheduled_operations
            if ops:
                last_end = max(op.end_time for op in ops)
                if last_end + machine.tear_down_time > machine.end_time:
                    nb += 1
        return nb

    def _compute_feasible(self) -> bool:
        '''Faisabilité calculée depuis l'état courant de l'instance.'''
        return self._violations() == 0

    @property
    def is_feasible(self) -> bool:
        '''
        Retourne True si la solution respecte toutes les contraintes :
        1. Toutes les opérations sont planifiées.
        2. Pour chaque machine utilisée : fin de la dernière opération +
           durée d'arrêt ≤ échéance de la machine.
        '''
        if self._cache is not None:
            return self._cache['feasible']
        return self._compute_feasible()

    # ------------------------------------------------------------------
    # Métriques
    # ------------------------------------------------------------------

    def _compute_cmax(self) -> int:
        '''Makespan calculé depuis l'état courant de l'instance.'''
        return max(job.completion_time for job in self._instance.jobs)

    def _compute_sum_ci(self) -> int:
        '''Somme des dates de fin calculée depuis l'état courant.'''
        return sum(job.completion_time for job in self._instance.jobs)

    def _compute_energy(self) -> float:
        '''Énergie totale calculée depuis l'état courant de l'instance.'''
        return sum(
            machine.total_energy_consumption
            for machine in self._instance.machines
        )

    @property
    def cmax(self) -> int:
        '''
        Retourne le makespan (Cmax) : date de fin du dernier job terminé.
        '''
        if self._cache is not None:
            return self._cache['cmax']
        return self._compute_cmax()

    @property
    def sum_ci(self) -> int:
        '''
        Retourne la somme des dates de fin de tous les jobs (ΣCi).
        '''
        if self._cache is not None:
            return self._cache['sum_ci']
        return self._compute_sum_ci()

    @property
    def total_energy_consumption(self) -> float:
        '''
        Retourne la consommation totale d'énergie de toutes les machines.
        '''
        if self._cache is not None:
            return self._cache['energy']
        return self._compute_energy()

    @property
    def evaluate(self) -> float:
        '''
        Calcule et retourne la valeur de la fonction objectif.
        Même valeur que objective (mise en cache).
        '''
        return self.objective

    # Grande pénalité lambda pour que toute solution vide / infaisable reste
    # nettement moins bonne qu'une solution réalisable.
    LAMBDA = 10_000_000
    PENALTY = LAMBDA

    def _aggregate(self, energy: float, cmax: int, sum_ci: int,
                   feasible: bool) -> float:
        '''
        Agrège les critères en une valeur scalaire.
        Une solution non réalisable est fortement pénalisée afin d'être
        toujours classée derrière une solution réalisable (réponse à la
        question 3 du TP : évaluation d'une solution non réalisable).

        L'énergie d'inactivité suit la formule littérale du modèle
        (min_consumption × durée_idle, cf. Machine.total_energy_consumption) ;
        les composantes sont agrégées avec des poids unitaires.
        '''
        w_e    = 1   # poids de la consommation énergétique
        w_cmax = 1   # poids du makespan
        w_ci   = 1   # poids de ΣCi
        value  = w_e * energy + w_cmax * cmax + w_ci * sum_ci
        if not feasible:
            value += self.PENALTY * self._violations()
        return value

    @property
    def objective(self) -> float:
        '''
        Fonction objectif : agrégation pondérée de l'énergie totale, du
        makespan (Cmax) et de la somme des dates de fin (ΣCi), augmentée
        d'une pénalité si la solution n'est pas réalisable.

        Poids par défaut = 1 pour chacun. Ils peuvent être adaptés selon
        les priorités de l'entreprise.
        '''
        if self._cache is not None:
            return self._cache['objective']
        return self._aggregate(
            self._compute_energy(), self._compute_cmax(),
            self._compute_sum_ci(), self._compute_feasible()
        )

    # ------------------------------------------------------------------
    # Représentation textuelle
    # ------------------------------------------------------------------

    def __str__(self) -> str:
        '''Représentation textuelle de la solution.'''
        if not all(op.assigned for op in self._instance.operations):
            return f"Solution partielle de {self._instance}"
        return (f"Solution de {self._instance} | "
                f"obj={self.objective:.1f} | "
                f"Cmax={self.cmax} | ΣCi={self.sum_ci} | "
                f"E={self.total_energy_consumption:.1f}")

    # ------------------------------------------------------------------
    # Sauvegarde / chargement CSV
    # ------------------------------------------------------------------

    def to_csv(self, output_folder: str = '.'):
        '''
        Sauvegarde la solution dans deux fichiers CSV :
          - sol_op.csv   : operation_id, machine_id, start_time
          - sol_mach.csv : machine_id, start_time, stop_time
        @param output_folder: répertoire de destination
        '''
        op_file   = os.path.join(output_folder, 'sol_op.csv')
        mach_file = os.path.join(output_folder, 'sol_mach.csv')

        # S'assurer que l'instance reflète bien CETTE solution avant export.
        self.restore()

        with open(op_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['operation_id', 'machine_id', 'start_time'])
            for op in self._instance.operations:
                if op.assigned:
                    writer.writerow([op.operation_id, op.assigned_to, op.start_time])

        with open(mach_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['machine_id', 'start_time', 'stop_time'])
            for machine in self._instance.machines:
                for start, stop in zip(machine.start_times, machine.stop_times):
                    writer.writerow([machine.machine_id, start, stop])

    def from_csv(self, inst_folder: str, operation_file: str, machine_file: str):
        '''
        Reconstruit une solution à partir de fichiers CSV.
        @param inst_folder:     répertoire de l'instance (non utilisé directement)
        @param operation_file:  chemin du fichier sol_op.csv
        @param machine_file:    chemin du fichier sol_mach.csv
        '''
        self.reset()

        # 1. Charger les sessions machines (machine_id → liste de (start, stop)),
        #    AVANT les opérations pour pouvoir y rattacher chaque opération.
        with open(machine_file, 'r') as f:
            reader = csv.reader(f)
            next(reader)
            for row in reader:
                machine_id = int(row[0])
                start_time = int(row[1])
                stop_time  = int(row[2])
                machine    = self._instance.get_machine(machine_id)
                machine._start_times.append(start_time)
                machine._stop_times.append(stop_time)
                machine._sessions_ops.append([])
        # Trier les sessions de chaque machine par heure de démarrage
        for machine in self._instance.machines:
            ordre = sorted(range(len(machine._start_times)),
                           key=lambda i: machine._start_times[i])
            machine._start_times = [machine._start_times[i] for i in ordre]
            machine._stop_times  = [machine._stop_times[i] for i in ordre]
            machine._sessions_ops = [[] for _ in ordre]
            machine._running = False

        # 2. Charger les affectations opération → (machine, start_time)
        assignments = {}
        with open(operation_file, 'r') as f:
            reader = csv.reader(f)
            next(reader)
            for row in reader:
                op_id      = int(row[0])
                machine_id = int(row[1])
                start_time = int(row[2])
                assignments[op_id] = (machine_id, start_time)

        # 3. Rejouer les opérations triées par start_time et les rattacher à
        #    la bonne session de leur machine (énergie correctement calculée).
        for op_id, (machine_id, start) in sorted(
                assignments.items(), key=lambda kv: kv[1][1]):
            op      = self._instance.get_operation(op_id)
            machine = self._instance.get_machine(machine_id)
            op.schedule(machine_id, start, check_success=False)
            machine._scheduled_operations.append(op)
            # Session contenant l'opération : dernière session démarrée avant start
            sess_index = 0
            for i, s in enumerate(machine._start_times):
                if s <= op.start_time:
                    sess_index = i
            if machine._sessions_ops:
                machine._sessions_ops[sess_index].append(op)
            machine._available_time = max(machine._available_time, op.end_time)

        # 4. Mettre à jour les pointeurs de planification des jobs
        for job in self._instance.jobs:
            for op in job.operations:
                if op.assigned:
                    job.schedule_operation()
                else:
                    break

        # 5. Figer la solution reconstruite
        self.freeze()

    # ------------------------------------------------------------------
    # Diagramme de Gantt
    # ------------------------------------------------------------------

    def gantt(self, colormapname: str):
        '''
        Génère un diagramme de Gantt de la solution.
        Les colormaps standard sont listées sur :
        https://matplotlib.org/stable/users/explain/colors/colormaps.html
        @param colormapname: nom de la colormap matplotlib (ex. "tab20")
        @return: objet plt prêt pour plt.show() ou plt.savefig()
        '''
        # S'assurer que l'instance reflète bien CETTE solution avant de tracer.
        self.restore()
        fig, ax = plt.subplots()
        colormap = colormaps[colormapname]

        for machine in self._instance.machines:
            machine_operations = sorted(
                machine.scheduled_operations, key=lambda op: op.start_time
            )
            for operation in machine_operations:
                operation_start    = operation.start_time
                operation_end      = operation.end_time
                operation_duration = operation_end - operation_start
                operation_label    = f"O{operation.operation_id}_J{operation.job_id}"

                # Couleur selon le job
                color_index = operation.job_id + 2
                if color_index >= colormap.N:
                    color_index = color_index % colormap.N
                color = colormap(color_index)

                ax.broken_barh(
                    [(operation_start, operation_duration)],
                    (machine.machine_id - 0.4, 0.8),
                    facecolors=color,
                    edgecolor='black'
                )
                middle_of_operation = operation_start + operation_duration / 2
                ax.text(
                    middle_of_operation, machine.machine_id,
                    operation_label,
                    rotation=90, ha='center', va='center', fontsize=8
                )

            set_up_time    = machine.set_up_time
            tear_down_time = machine.tear_down_time
            for (start, stop) in zip(machine.start_times, machine.stop_times):
                ax.broken_barh(
                    [(start, set_up_time)],
                    (machine.machine_id - 0.4, 0.8),
                    facecolors=colormap(0), edgecolor='black'
                )
                ax.broken_barh(
                    [(stop - tear_down_time, tear_down_time)],
                    (machine.machine_id - 0.4, 0.8),
                    facecolors=colormap(1), edgecolor='black'
                )
                ax.text(start + set_up_time / 2.0, machine.machine_id,
                        "setup", rotation=90, ha='center', va='center', fontsize=8)
                ax.text(stop - tear_down_time / 2.0, machine.machine_id,
                        "teardown", rotation=90, ha='center', va='center', fontsize=8)

        fig = ax.figure
        fig.set_size_inches(12, 6)
        ax.set_yticks(range(self._instance.nb_machines))
        ax.set_yticklabels(
            [f'M{m_id}' for m_id in range(self._instance.nb_machines)]
        )
        ax.set_xlabel('Temps')
        ax.set_ylabel('Machine')
        ax.set_title('Diagramme de Gantt')
        ax.grid(True)
        return plt
