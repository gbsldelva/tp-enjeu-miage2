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
        # Valeur de la fonction objectif (None tant que non calculée)
        self._objective_value = None

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
        self._objective_value = None

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
        # Invalider le cache de la valeur objectif
        self._objective_value = None

    # ------------------------------------------------------------------
    # Faisabilité
    # ------------------------------------------------------------------

    @property
    def is_feasible(self) -> bool:
        '''
        Retourne True si la solution respecte toutes les contraintes :
        1. Toutes les opérations sont planifiées.
        2. Pour chaque machine utilisée : fin de la dernière opération +
           durée d'arrêt ≤ échéance de la machine.
        '''
        # 1. Toutes les opérations planifiées ?
        if not all(op.assigned for op in self._instance.operations):
            return False

        # 2. Respect des échéances de chaque machine
        for machine in self._instance.machines:
            ops = machine.scheduled_operations
            if ops:
                last_end = max(op.end_time for op in ops)
                if last_end + machine.tear_down_time > machine._end_time:
                    return False
        return True

    # ------------------------------------------------------------------
    # Métriques
    # ------------------------------------------------------------------

    @property
    def cmax(self) -> int:
        '''
        Retourne le makespan (Cmax) : date de fin du dernier job terminé.
        '''
        return max(job.completion_time for job in self._instance.jobs)

    @property
    def sum_ci(self) -> int:
        '''
        Retourne la somme des dates de fin de tous les jobs (ΣCi).
        '''
        return sum(job.completion_time for job in self._instance.jobs)

    @property
    def total_energy_consumption(self) -> float:
        '''
        Retourne la consommation totale d'énergie de toutes les machines.
        '''
        return sum(
            machine.total_energy_consumption
            for machine in self._instance.machines
        )

    @property
    def evaluate(self) -> float:
        '''
        Calcule et retourne la valeur de la fonction objectif.
        Même valeur que objective (mise en cache).
        '''
        return self.objective

    @property
    def objective(self) -> float:
        '''
        Fonction objectif : agrégation pondérée de l'énergie totale, du
        makespan (Cmax) et de la somme des dates de fin (ΣCi).

        Poids par défaut = 1 pour chacun. Ils peuvent être adaptés selon
        les priorités de l'entreprise.
        '''
        if self._objective_value is None:
            w_e    = 1   # poids de la consommation énergétique
            w_cmax = 1   # poids du makespan
            w_ci   = 1   # poids de ΣCi
            self._objective_value = (
                w_e    * self.total_energy_consumption
                + w_cmax * self.cmax
                + w_ci   * self.sum_ci
            )
        return self._objective_value

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

        # Charger les affectations opération → (machine, start_time)
        assignments = {}
        with open(operation_file, 'r') as f:
            reader = csv.reader(f)
            next(reader)
            for row in reader:
                op_id      = int(row[0])
                machine_id = int(row[1])
                start_time = int(row[2])
                assignments[op_id] = (machine_id, start_time)

        # Rejouer les opérations triées par start_time
        sorted_ops = sorted(
            [(start, op_id, machine_id)
             for op_id, (machine_id, start) in assignments.items()]
        )
        for _, op_id, machine_id in sorted_ops:
            op      = self._instance.get_operation(op_id)
            machine = self._instance.get_machine(machine_id)
            op.schedule(machine_id, assignments[op_id][1], check_success=False)
            machine._scheduled_operations.append(op)
            machine._sessions_ops[-1].append(op) if machine._sessions_ops else None
            machine._available_time = op.end_time

        # Charger les sessions machines
        with open(machine_file, 'r') as f:
            reader = csv.reader(f)
            next(reader)
            for row in reader:
                machine_id = int(row[0])
                start_time = int(row[1])
                stop_time  = int(row[2])
                machine    = self._instance.get_machine(machine_id)
                if start_time not in machine.start_times:
                    machine._start_times.append(start_time)
                    machine._stop_times.append(stop_time)
                    machine._sessions_ops.append([])
                    machine._running = True

        # Mettre à jour les jobs
        for job in self._instance.jobs:
            for op in job.operations:
                if op.assigned:
                    job.schedule_operation()
                else:
                    break

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
