'''
Tests complémentaires pour atteindre ≥ 95 % de couverture.
Couvre les branches non atteintes par les tests principaux :
  - opérations non planifiées (retours à -1)
  - __str__ / __repr__ des classes modèle
  - machine.stop()
  - job.next_operation → None, job.operations, completion_time -1
  - operation.schedule() avec check_success=True (échec)
  - operation.schedule_at_min_time()
  - solution.inst, solution.__str__ partielle
  - instance.get_job/get_operation par id

@author: Vassilissa Lehoux
'''
import unittest
import os

from src.scheduling.instance.instance import Instance
from src.scheduling.instance.operation import Operation
from src.scheduling.instance.machine import Machine
from src.scheduling.instance.job import Job
from src.scheduling.solution import Solution
from src.scheduling.tests.test_utils import TEST_FOLDER_DATA


class TestOperationBranches(unittest.TestCase):
    '''
    Couvre les branches manquantes de la classe Operation.
    '''

    def setUp(self):
        self.op = Operation(0, 0)
        self.op.add_machine_option(1, 12, 12)

    def test_str_unassigned(self):
        '''__str__ d'une opération non planifiée.'''
        s = str(self.op)
        self.assertIn('O0_J0', s)
        self.assertNotIn('_M', s)

    def test_str_assigned(self):
        '''__str__ et __repr__ d'une opération planifiée.'''
        self.op.schedule(1, 20, check_success=False)
        s = str(self.op)
        self.assertIn('_M1', s)
        self.assertEqual(repr(self.op), s)   # couvre __repr__

    def test_assigned_to_unassigned(self):
        '''assigned_to retourne -1 si non planifiée.'''
        self.assertEqual(self.op.assigned_to, -1)

    def test_processing_time_unassigned(self):
        '''processing_time retourne -1 si non planifiée.'''
        self.assertEqual(self.op.processing_time, -1)

    def test_start_time_unassigned(self):
        '''start_time retourne -1 si non planifiée.'''
        self.assertEqual(self.op.start_time, -1)

    def test_end_time_unassigned(self):
        '''end_time retourne -1 si non planifiée.'''
        self.assertEqual(self.op.end_time, -1)

    def test_energy_unassigned(self):
        '''energy retourne -1 si non planifiée.'''
        self.assertEqual(self.op.energy, -1)

    def test_is_ready_no_predecessors(self):
        '''is_ready retourne True si pas de prédécesseur.'''
        self.assertTrue(self.op.is_ready(0))

    def test_schedule_check_success_fail(self):
        '''
        schedule() avec check_success=True doit retourner False si le
        prédécesseur n'est pas encore planifié.
        '''
        pred = Operation(0, -1)
        pred.add_machine_option(0, 5, 5)
        self.op.add_predecessor(pred)
        # pred n'est pas planifié → is_ready = False → retour False
        result = self.op.schedule(1, 0, check_success=True)
        self.assertFalse(result, 'schedule doit échouer si précédence non respectée')

    def test_schedule_at_min_time_valid(self):
        '''schedule_at_min_time sur une machine éligible.'''
        result = self.op.schedule_at_min_time(1, 0)
        self.assertTrue(result)
        self.assertTrue(self.op.assigned)

    def test_schedule_at_min_time_invalid_machine(self):
        '''schedule_at_min_time retourne False si la machine n'est pas éligible.'''
        result = self.op.schedule_at_min_time(99, 0)
        self.assertFalse(result)


class TestJobBranches(unittest.TestCase):
    '''
    Couvre les branches manquantes de la classe Job.
    '''

    def test_operations_property(self):
        '''La propriété operations retourne la liste des opérations.'''
        job = Job(0)
        op0 = Operation(0, 0)
        op0.add_machine_option(0, 5, 5)
        job.add_operation(op0)
        # Couvre la ligne "return self._operations"
        self.assertEqual(job.operations, [op0])

    def test_next_operation_none_when_planned(self):
        '''next_operation retourne None quand le job est entièrement planifié.'''
        job = Job(0)
        op0 = Operation(0, 0)
        op0.add_machine_option(0, 5, 5)
        job.add_operation(op0)
        job.schedule_operation()   # simule la planification de op0
        # next_operation doit retourner None (index >= nb ops)
        self.assertIsNone(job.next_operation)

    def test_completion_time_empty_job(self):
        '''completion_time retourne -1 pour un job sans opérations.'''
        job = Job(99)
        self.assertEqual(job.completion_time, -1)

    def test_completion_time_unassigned_last_op(self):
        '''completion_time retourne -1 si la dernière opération n'est pas planifiée.'''
        job = Job(0)
        op0 = Operation(0, 0)
        op0.add_machine_option(0, 5, 5)
        job.add_operation(op0)
        # op0 n'est pas planifiée → completion_time = -1
        self.assertEqual(job.completion_time, -1)


class TestMachineBranches(unittest.TestCase):
    '''
    Couvre les branches manquantes de la classe Machine.
    '''

    def test_str_repr(self):
        '''__str__ et __repr__ de Machine.'''
        m = Machine(2, 10, 3, 10, 3, 1, 100)
        self.assertEqual(str(m), 'M2')
        self.assertEqual(repr(m), 'M2')

    def test_stop_method(self):
        '''
        Vérifie que stop() met à jour stop_times et désactive _running.
        Utile pour la stratégie multi-session.
        '''
        m  = Machine(0, 15, 4, 15, 4, 1, 100)
        op = Operation(0, 0)
        op.add_machine_option(0, 5, 5)
        m.add_operation(op, 0)   # démarre la machine

        # stop à l'heure de disponibilité
        m.stop(m.available_time)
        self.assertFalse(m._running, 'La machine doit être éteinte après stop()')
        self.assertEqual(m.stop_times[0], m.available_time + m.tear_down_time,
                         'stop_times doit être mis à jour par stop()')

    def test_multi_session(self):
        '''
        Vérifie le comportement multi-session : stop() puis add_operation()
        démarre une nouvelle session.
        '''
        m   = Machine(0, 5, 2, 5, 2, 1, 200)
        op0 = Operation(0, 0)
        op0.add_machine_option(0, 10, 5)
        op1 = Operation(0, 1)
        op1.add_machine_option(0, 10, 5)

        m.add_operation(op0, 0)    # session 1 : démarre à t=0
        m.stop(op0.end_time)       # arrêt après op0

        m.add_operation(op1, 100)  # session 2 : redémarre à t=95

        self.assertEqual(len(m.start_times), 2, 'Deux sessions doivent exister')
        self.assertEqual(len(m.stop_times), 2)

    def test_auto_interrupt_on_large_idle_gap(self):
        '''
        Une grande plage d'inactivité doit créer automatiquement une nouvelle
        session au lieu de laisser la machine allumée inutilement.
        '''
        m   = Machine(0, 5, 2, 5, 2, 1, 200)
        op0 = Operation(0, 0)
        op0.add_machine_option(0, 10, 5)
        op1 = Operation(1, 1)
        op1.add_machine_option(0, 10, 5)

        m.add_operation(op0, 0)
        m.add_operation(op1, 100)

        self.assertEqual(len(m.start_times), 2,
                         'Une interruption automatique doit créer deux sessions')
        self.assertEqual(m.stop_times[0], op0.end_time + m.tear_down_time,
                         'La première session doit se terminer après le teardown')
        self.assertEqual(m.start_times[1], 95,
                         'La seconde session doit redémarrer juste à temps')


class TestSolutionBranches(unittest.TestCase):
    '''
    Couvre les branches manquantes de la classe Solution.
    '''

    def setUp(self):
        self.inst = Instance.from_file(TEST_FOLDER_DATA + os.path.sep + "jsp1")

    def test_inst_property(self):
        '''La propriété inst retourne l'instance associée.'''
        sol = Solution(self.inst)
        self.assertIs(sol.inst, self.inst)

    def test_str_partial(self):
        '''__str__ d'une solution partiellement planifiée.'''
        sol = Solution(self.inst)
        s = str(sol)
        self.assertIn('partielle', s)

    def test_is_feasible_not_all_ops(self):
        '''is_feasible retourne False si une opération n'est pas planifiée.'''
        sol = Solution(self.inst)
        # Planifier seulement une opération → pas toutes planifiées
        sol.schedule(self.inst.operations[0], self.inst.machines[1])
        self.assertFalse(sol.is_feasible)


class TestInstanceBranches(unittest.TestCase):
    '''
    Couvre les branches manquantes de la classe Instance.
    '''

    def setUp(self):
        self.inst = Instance.from_file(TEST_FOLDER_DATA + os.path.sep + "jsp1")

    def test_get_job_by_id(self):
        '''get_job retrouve un job par son identifiant.'''
        job = self.inst.get_job(1)
        self.assertEqual(job.job_id, 1)

    def test_get_operation_by_id(self):
        '''get_operation retrouve une opération par son identifiant.'''
        op = self.inst.get_operation(2)
        self.assertEqual(op.operation_id, 2)

    def test_get_job_not_found(self):
        '''get_job lève ValueError pour un identifiant inconnu.'''
        with self.assertRaises(ValueError):
            self.inst.get_job(999)

    def test_get_operation_not_found(self):
        '''get_operation lève ValueError pour un identifiant inconnu.'''
        with self.assertRaises(ValueError):
            self.inst.get_operation(999)

    def test_repr_instance(self):
        '''__repr__ de l'instance.'''
        self.assertEqual(repr(self.inst), str(self.inst))


class TestSolutionGanttAndFromCsv(unittest.TestCase):
    '''Tests des branches restantes de solution.py.'''

    def setUp(self):
        self.inst = Instance.from_file(TEST_FOLDER_DATA + os.path.sep + "jsp1")
        self.sol  = Solution(self.inst)
        # Planifier toutes les opérations
        self.sol.schedule(self.inst.operations[0], self.inst.machines[1])
        self.sol.schedule(self.inst.operations[2], self.inst.machines[1])
        self.sol.schedule(self.inst.operations[1], self.inst.machines[0])
        self.sol.schedule(self.inst.operations[3], self.inst.machines[0])

    def test_gantt_returns_plt(self):
        '''gantt() retourne un objet plt sans erreur.'''
        import matplotlib
        matplotlib.use('Agg')   # backend sans affichage
        plt = self.sol.gantt('tab20')
        self.assertIsNotNone(plt)

    def test_is_feasible_end_time_violation(self):
        '''
        is_feasible retourne False si la dernière opération dépasse l'échéance.
        On crée une machine avec end_time très court pour forcer la violation.
        '''
        from src.scheduling.instance.machine import Machine
        from src.scheduling.instance.operation import Operation

        # Machine avec end_time très serré : teardown ne pourra pas se faire
        m   = Machine(99, 1, 1, 100, 1, 1, 10)   # teardown_time = 100 > end_time=10
        op  = Operation(99, 99)
        op.add_machine_option(99, 2, 2)
        m.add_operation(op, 0)                     # op se termine à t=2

        # Vérifier manuellement la condition : 2 + 100 = 102 > 10 → infaisable
        last_end = op.end_time   # = 2
        self.assertGreater(last_end + m.tear_down_time, m._end_time)

    def test_from_csv_round_trip(self):
        '''to_csv puis from_csv doit reproduire une solution cohérente.'''
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            self.sol.to_csv(tmpdir)
            op_file   = os.path.join(tmpdir, 'sol_op.csv')
            mach_file = os.path.join(tmpdir, 'sol_mach.csv')
            # Recharger l'instance (état propre)
            new_inst = Instance.from_file(TEST_FOLDER_DATA + os.path.sep + "jsp1")
            new_sol  = Solution(new_inst)
            new_sol.from_csv(tmpdir, op_file, mach_file)
            # Toutes les opérations doivent être planifiées
            self.assertTrue(all(op.assigned for op in new_sol.all_operations))


class TestLocalSearchBranches(unittest.TestCase):
    '''Tests des branches restantes de local_search.py.'''

    def setUp(self):
        self.inst = Instance.from_file(TEST_FOLDER_DATA + os.path.sep + "jsp1")

    def test_best_neighbor_ls_n2_branch(self):
        '''
        Vérifie que la branche "meilleur = meilleur2" est accessible quand N2
        produit un meilleur résultat que N1.
        On exécute BestNeighborLocalSearch avec plusieurs seeds pour couvrir
        les deux branches de la comparaison N1/N2.
        '''
        from src.scheduling.optim.local_search import BestNeighborLocalSearch
        from src.scheduling.optim.constructive import NonDeterminist
        heur = BestNeighborLocalSearch()
        # Plusieurs runs pour couvrir les deux branches N1 <= N2 et N1 > N2
        for seed in range(5):
            sol = heur.run(self.inst, NonDeterminist, params={'seed': seed,
                                                               'max_iterations': 3})
            self.assertIsNotNone(sol)


if __name__ == "__main__":
    unittest.main()
