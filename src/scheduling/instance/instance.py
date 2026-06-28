'''
Instance du problème d'optimisation.
Charge les données depuis les fichiers CSV et agrège machines, jobs
et opérations.

@author: Vassilissa Lehoux
'''
from typing import List
import os
import csv

from src.scheduling.instance.job import Job
from src.scheduling.instance.operation import Operation
from src.scheduling.instance.machine import Machine


class Instance(object):
    '''
    Représente une instance complète du problème d'ordonnancement.
    Contient la liste des machines, des jobs et des opérations.
    '''

    def __init__(self, instance_name: str):
        '''
        Constructeur.
        @param instance_name: nom de l'instance (ex. "jsp1")
        '''
        self._instance_name = instance_name
        self._jobs:       List[Job]       = []
        self._machines:   List[Machine]   = []
        self._operations: List[Operation] = []

    # ------------------------------------------------------------------
    # Chargement depuis les fichiers CSV
    # ------------------------------------------------------------------

    @classmethod
    def from_file(cls, folderpath: str):
        '''
        Construit une Instance à partir d'un répertoire contenant :
          - <nom>_op.csv   : opérations (job, operation, machine, pt, energy)
          - <nom>_mach.csv : machines   (id, setup_t, setup_e, teardown_t,
                                         teardown_e, min_conso, end_time)

        Format _op.csv : chaque opération (job_id, op_id) apparaît une fois
        par machine éligible.
        '''
        inst = cls(os.path.basename(folderpath))

        # --- Lecture des opérations ---
        # ops_dict : (job_id, op_id) → Operation
        # jobs_dict : job_id → Job
        ops_dict:  dict = {}
        jobs_dict: dict = {}

        op_filepath = (folderpath + os.path.sep
                       + inst._instance_name + '_op.csv')
        with open(op_filepath, 'r') as csv_file:
            csv_reader = csv.reader(csv_file)
            next(csv_reader)   # skip header
            for row in csv_reader:
                job_id     = int(row[0])
                op_id      = int(row[1])
                machine_id = int(row[2])
                pt         = int(row[3])
                energy     = int(row[4])

                key = (job_id, op_id)
                if key not in ops_dict:
                    ops_dict[key] = Operation(job_id, op_id)
                # Enregistre les caractéristiques pour cette machine
                ops_dict[key].add_machine_option(machine_id, pt, energy)

        # Construction des jobs dans l'ordre trié (job_id, op_id)
        for (job_id, op_id), op in sorted(ops_dict.items()):
            if job_id not in jobs_dict:
                jobs_dict[job_id] = Job(job_id)
            # add_operation pose automatiquement les liens prédécesseur/successeur
            jobs_dict[job_id].add_operation(op)

        # --- Lecture des machines ---
        mach_filepath = (folderpath + os.path.sep
                         + inst._instance_name + '_mach.csv')
        with open(mach_filepath, 'r') as csv_file:
            csv_reader = csv.reader(csv_file)
            next(csv_reader)   # skip header
            for row in csv_reader:
                machine_id   = int(row[0])
                set_up_time  = int(row[1])
                set_up_energy= int(row[2])
                tear_down_t  = int(row[3])
                tear_down_e  = int(row[4])
                min_conso    = int(row[5])
                end_time     = int(row[6])
                inst._machines.append(
                    Machine(machine_id, set_up_time, set_up_energy,
                            tear_down_t, tear_down_e, min_conso, end_time)
                )

        # --- Finalisation ---
        inst._jobs       = [jobs_dict[j] for j in sorted(jobs_dict)]
        inst._operations = [op for _, op in sorted(ops_dict.items())]

        return inst

    # ------------------------------------------------------------------
    # Propriétés
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        '''Retourne le nom de l'instance.'''
        return self._instance_name

    @property
    def machines(self) -> List[Machine]:
        '''Retourne la liste des machines.'''
        return self._machines

    @property
    def jobs(self) -> List[Job]:
        '''Retourne la liste des jobs.'''
        return self._jobs

    @property
    def operations(self) -> List[Operation]:
        '''Retourne la liste de toutes les opérations.'''
        return self._operations

    @property
    def nb_jobs(self) -> int:
        '''Retourne le nombre de jobs.'''
        return len(self._jobs)

    @property
    def nb_machines(self) -> int:
        '''Retourne le nombre de machines.'''
        return len(self._machines)

    @property
    def nb_operations(self) -> int:
        '''Retourne le nombre total d'opérations (uniques).'''
        return len(self._operations)

    # ------------------------------------------------------------------
    # Accesseurs par identifiant
    # ------------------------------------------------------------------

    def get_machine(self, machine_id: int) -> Machine:
        '''
        Retourne la machine correspondant à l'identifiant donné.
        Les identifiants sont supposés contigus à partir de 0.
        '''
        return self._machines[machine_id]

    def get_job(self, job_id: int) -> Job:
        '''
        Retourne le job correspondant à l'identifiant donné.
        '''
        for job in self._jobs:
            if job.job_id == job_id:
                return job
        raise ValueError(f"Job {job_id} introuvable dans l'instance.")

    def get_operation(self, operation_id: int) -> Operation:
        '''
        Retourne l'opération correspondant à l'identifiant donné.
        '''
        for op in self._operations:
            if op.operation_id == operation_id:
                return op
        raise ValueError(f"Opération {operation_id} introuvable dans l'instance.")

    # ------------------------------------------------------------------
    # Représentation textuelle
    # ------------------------------------------------------------------

    def __str__(self) -> str:
        return (f"{self.name}_M{self.nb_machines}"
                f"_J{self.nb_jobs}_O{self.nb_operations}")

    def __repr__(self) -> str:
        return str(self)
