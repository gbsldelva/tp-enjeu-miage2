'''
Test of the Solution class.

@author: Vassilissa Lehoux
'''
import unittest
import os

from src.scheduling.instance.instance import Instance
from src.scheduling.solution import Solution
from src.scheduling.tests.test_utils import TEST_FOLDER_DATA, TEST_FOLDER


class TestSolution(unittest.TestCase):

    def setUp(self):
        self.inst1 = Instance.from_file(TEST_FOLDER_DATA + os.path.sep + "jsp1")

    def tearDown(self):
        pass

    def test_init_sol(self):
        sol = Solution(self.inst1)
        self.assertEqual(len(sol.all_operations), len(self.inst1.operations),
                         'Nb of operations should be the same between instance and solution')
        self.assertEqual(len(sol.available_operations), len(self.inst1.jobs),
                         'One operation per job should be available for scheduling')

    def test_schedule_op(self):
        sol = Solution(self.inst1)
        operation = self.inst1.operations[0]
        machine = self.inst1.machines[1]
        sol.schedule(operation, machine)
        self.assertEqual(operation.assigned, True, 'operation should be assigned')
        self.assertEqual(operation.assigned_to, 1, 'wrong machine machine')
        self.assertEqual(operation.processing_time, 12, 'wrong operation duration')
        self.assertEqual(operation.energy, 12, 'wrong operation energy cost')
        self.assertEqual(operation.start_time, 20, 'wrong set up time for machine')
        self.assertEqual(operation.end_time, 32, 'wrong operation end time')
        self.assertEqual(machine.available_time, 32, 'wrong available time')
        self.assertEqual(machine.working_time, 120, 'wrong working time for machine')
        operation = self.inst1.operations[2]
        sol.schedule(operation, machine)
        self.assertEqual(operation.assigned, True, 'operation should be assigned')
        self.assertEqual(operation.assigned_to, 1, 'wrong machine machine')
        self.assertEqual(operation.processing_time, 9, 'wrong operation duration')
        self.assertEqual(operation.energy, 10, 'wrong operation energy cost')
        self.assertEqual(operation.start_time, 32, 'wrong start time for operation')
        self.assertEqual(operation.end_time, 41, 'wrong operation end time')
        self.assertEqual(machine.available_time, 41, 'wrong available time')
        self.assertEqual(machine.working_time, 120, 'wrong working time for machine')
        operation = self.inst1.operations[1]
        machine = self.inst1.machines[0]
        sol.schedule(operation, machine)
        self.assertEqual(operation.assigned, True, 'operation should be assigned')
        self.assertEqual(operation.assigned_to, 0, 'wrong machine machine')
        self.assertEqual(operation.processing_time, 5, 'wrong operation duration')
        self.assertEqual(operation.energy, 6, 'wrong operation energy cost')
        self.assertEqual(operation.start_time, 32, 'wrong start time for operation')
        self.assertEqual(operation.end_time, 37, 'wrong operation end time')
        self.assertEqual(machine.available_time, 37, 'wrong available time')
        self.assertEqual(machine.working_time, 83, 'wrong working time for machine')
        self.assertEqual(machine.start_times[0], 17)
        self.assertEqual(machine.stop_times[0], 100)
        operation = self.inst1.operations[3]
        sol.schedule(operation, machine)
        self.assertEqual(operation.assigned, True, 'operation should be assigned')
        self.assertEqual(operation.assigned_to, 0, 'wrong machine machine')
        self.assertEqual(operation.processing_time, 10, 'wrong operation duration')
        self.assertEqual(operation.energy, 9, 'wrong operation energy cost')
        self.assertEqual(operation.start_time, 41, 'wrong start time for operation')
        self.assertEqual(operation.end_time, 51, 'wrong operation end time')
        self.assertEqual(machine.available_time, 51, 'wrong available time')
        self.assertEqual(machine.working_time, 83, 'wrong working time for machine')
        self.assertEqual(machine.start_times[0], 17)
        self.assertEqual(machine.stop_times[0], 100)
        self.assertTrue(sol.is_feasible, 'Solution should be feasible')
        plt = sol.gantt('tab20')
        plt.savefig(TEST_FOLDER + os.path.sep + 'temp.png')

    def test_objective(self):
        '''
        Vérifie la valeur de la fonction objectif et sa cohérence avec
        les métriques individuelles.
        '''
        sol = Solution(self.inst1)
        # Planifier toutes les opérations (même séquence que test_schedule_op)
        sol.schedule(self.inst1.operations[0], self.inst1.machines[1])
        sol.schedule(self.inst1.operations[2], self.inst1.machines[1])
        sol.schedule(self.inst1.operations[1], self.inst1.machines[0])
        sol.schedule(self.inst1.operations[3], self.inst1.machines[0])

        # Vérifier les composantes individuelles
        self.assertGreater(sol.cmax, 0, 'Cmax doit être positif')
        self.assertGreater(sol.sum_ci, 0, 'ΣCi doit être positif')
        self.assertGreater(sol.total_energy_consumption, 0,
                           'Consommation énergétique doit être positive')

        # La valeur objective = énergie + Cmax + ΣCi (poids = 1)
        expected = (sol.total_energy_consumption + sol.cmax + sol.sum_ci)
        self.assertAlmostEqual(sol.objective, expected, places=5,
                               msg='Valeur objective incorrecte')

    def test_evaluate(self):
        '''
        Vérifie que evaluate retourne la même valeur que objective.
        '''
        sol = Solution(self.inst1)
        sol.schedule(self.inst1.operations[0], self.inst1.machines[1])
        sol.schedule(self.inst1.operations[2], self.inst1.machines[1])
        sol.schedule(self.inst1.operations[1], self.inst1.machines[0])
        sol.schedule(self.inst1.operations[3], self.inst1.machines[0])

        self.assertEqual(sol.evaluate, sol.objective,
                         'evaluate et objective doivent retourner la même valeur')

    def test_reset(self):
        '''
        Vérifie que reset() remet la solution à zéro.
        '''
        sol = Solution(self.inst1)
        sol.schedule(self.inst1.operations[0], self.inst1.machines[1])
        sol.reset()
        self.assertEqual(len(sol.available_operations), len(self.inst1.jobs),
                         'Après reset, les opérations initiales doivent être disponibles')
        self.assertFalse(any(op.assigned for op in sol.all_operations),
                         'Après reset, aucune opération ne doit être planifiée')

    def test_str(self):
        '''
        Vérifie la représentation textuelle d'une solution complète.
        '''
        sol = Solution(self.inst1)
        sol.schedule(self.inst1.operations[0], self.inst1.machines[1])
        sol.schedule(self.inst1.operations[2], self.inst1.machines[1])
        sol.schedule(self.inst1.operations[1], self.inst1.machines[0])
        sol.schedule(self.inst1.operations[3], self.inst1.machines[0])
        self.assertIn('Solution', str(sol), 'La repr. textuelle doit contenir "Solution"')

    def test_to_csv(self):
        '''
        Vérifie que to_csv génère les fichiers sans erreur.
        '''
        import tempfile
        sol = Solution(self.inst1)
        sol.schedule(self.inst1.operations[0], self.inst1.machines[1])
        sol.schedule(self.inst1.operations[2], self.inst1.machines[1])
        sol.schedule(self.inst1.operations[1], self.inst1.machines[0])
        sol.schedule(self.inst1.operations[3], self.inst1.machines[0])

        with tempfile.TemporaryDirectory() as tmpdir:
            sol.to_csv(tmpdir)
            self.assertTrue(os.path.exists(os.path.join(tmpdir, 'sol_op.csv')),
                            'sol_op.csv doit être créé')
            self.assertTrue(os.path.exists(os.path.join(tmpdir, 'sol_mach.csv')),
                            'sol_mach.csv doit être créé')


if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
