'''
Tests pour la classe Machine.

@author: Vassilissa Lehoux
'''
import unittest

from src.scheduling.instance.machine import Machine
from src.scheduling.instance.operation import Operation


class TestMachine(unittest.TestCase):
    '''
    Tests unitaires pour la classe Machine.
    On utilise les données de l'instance jsp1 :
      Machine 1 : setup_time=20, setup_energy=5, teardown_time=15,
                  teardown_energy=4, min_consumption=2, end_time=120
      Machine 0 : setup_time=15, setup_energy=4, teardown_time=15,
                  teardown_energy=4, min_consumption=1, end_time=100
    '''

    def setUp(self):
        # Machine 1 de jsp1
        self.m1 = Machine(1, 20, 5, 15, 4, 2, 120)
        # Machine 0 de jsp1
        self.m0 = Machine(0, 15, 4, 15, 4, 1, 100)

        # Opérations de substitution (sans Instance complète)
        # op0 : job=0, op=0, machine=1 → pt=12, energy=12
        self.op0 = Operation(0, 0)
        self.op0.add_machine_option(1, 12, 12)

        # op2 : job=1, op=2, machine=1 → pt=9, energy=10
        self.op2 = Operation(1, 2)
        self.op2.add_machine_option(1, 9, 10)

        # op1 : job=0, op=1, machine=0 → pt=5, energy=6
        self.op1 = Operation(0, 1)
        self.op1.add_machine_option(0, 5, 6)
        # op1 attend que op0 soit terminé (précédence)
        self.op1.add_predecessor(self.op0)
        self.op0.add_successor(self.op1)

        # op3 : job=1, op=3, machine=0 → pt=10, energy=9
        self.op3 = Operation(1, 3)
        self.op3.add_machine_option(0, 10, 9)
        self.op3.add_predecessor(self.op2)
        self.op2.add_successor(self.op3)

    def tearDown(self):
        pass

    def testWorkingTime(self):
        '''
        Vérifie le temps de fonctionnement total d'une machine.
        Machine 1 : démarre à t=0 (max(0, 0-20)=0), setup → op0 à t=20.
        stop_time = end_time = 120. working_time = 120 - 0 = 120.
        Après ajout de op2 (pas de nouveau démarrage), working_time reste 120.
        '''
        self.m1.add_operation(self.op0, 0)
        self.assertEqual(self.m1.working_time, 120,
                         'working_time incorrect après la première opération')

        self.m1.add_operation(self.op2, 0)
        self.assertEqual(self.m1.working_time, 120,
                         'working_time ne doit pas changer pour la même session')

        # Machine 0 : op1 min_start=32 (op0 termine à 32)
        # machine_start = max(0, 32-15) = 17, stop = end_time = 100
        # working_time = 100 - 17 = 83
        self.op0.schedule(1, 20, check_success=False)   # force le schedule pour que op0 soit "terminé"
        self.m0.add_operation(self.op1, self.op0.end_time)
        self.assertEqual(self.m0.working_time, 83,
                         'working_time incorrect pour machine 0 (démarrage tardif)')

    def testTotalEnergyConsumption(self):
        '''
        Vérifie la consommation totale d'énergie d'une machine (en kWh).
        Machine 1 avec op0 (pt=12, e=12) et op2 (pt=9, e=10) :
          - setup_energy    = 5
          - teardown_energy = 4
          - Σ op.energy     = 12 + 10 = 22
          - idle_time       = working_time - setup_time - teardown_time - Σ pt
                            = 120 - 20 - 15 - 21 = 64
          - énergie idle    = min_consumption × idle / 60 = 2 × 64 / 60 ≈ 2.13
          - TOTAL           = 5 + 4 + 22 + 2.13 ≈ 33.13
        '''
        self.m1.add_operation(self.op0, 0)
        self.m1.add_operation(self.op2, 0)
        self.assertAlmostEqual(self.m1.total_energy_consumption,
                               5 + 4 + 22 + 2 * 64 / 60, places=5,
                               msg='consommation énergétique incorrecte pour machine 1')

    def testAvailableTime(self):
        '''
        Vérifie que available_time est mis à jour après chaque opération.
        '''
        self.assertEqual(self.m1.available_time, 0,
                         'machine vide → available_time doit être 0')
        self.m1.add_operation(self.op0, 0)
        # op0 start=20, pt=12 → fin=32
        self.assertEqual(self.m1.available_time, 32,
                         'available_time incorrect après op0')
        self.m1.add_operation(self.op2, 0)
        # op2 start=32, pt=9 → fin=41
        self.assertEqual(self.m1.available_time, 41,
                         'available_time incorrect après op2')

    def testStartStopTimes(self):
        '''
        Vérifie que start_times et stop_times sont bien enregistrés.
        Machine 1 : start_times[0]=0, stop_times[0]=120.
        Machine 0 : start_times[0]=17, stop_times[0]=100.
        '''
        self.m1.add_operation(self.op0, 0)
        self.assertEqual(self.m1.start_times[0], 0, 'start_time incorrect pour m1')
        self.assertEqual(self.m1.stop_times[0], 120, 'stop_time incorrect pour m1')

        self.op0.schedule(1, 20, check_success=False)
        self.m0.add_operation(self.op1, self.op0.end_time)
        self.assertEqual(self.m0.start_times[0], 17, 'start_time incorrect pour m0')
        self.assertEqual(self.m0.stop_times[0], 100, 'stop_time incorrect pour m0')

    def testReset(self):
        '''
        Vérifie que reset() efface bien toutes les informations planifiées.
        '''
        self.m1.add_operation(self.op0, 0)
        self.m1.reset()
        self.assertEqual(self.m1.scheduled_operations, [],
                         'reset doit vider les opérations planifiées')
        self.assertEqual(self.m1.start_times, [],
                         'reset doit vider start_times')
        self.assertEqual(self.m1.stop_times, [],
                         'reset doit vider stop_times')
        self.assertEqual(self.m1.available_time, 0,
                         'reset doit remettre available_time à 0')

    def testAutomaticInterruption(self):
        '''
        Vérifie qu'une nouvelle session est créée automatiquement lorsqu'il
        existe un grand trou entre deux opérations.
        '''
        self.m1.add_operation(self.op0, 0)
        self.m1.add_operation(self.op2, 100)

        self.assertEqual(len(self.m1.start_times), 2,
                         'un grand trou doit provoquer une interruption automatique')
        self.assertEqual(self.m1.stop_times[0], self.op0.end_time + self.m1.tear_down_time,
                         'la première session doit inclure son teardown')
        self.assertEqual(self.m1.start_times[1], 80,
                         'la seconde session doit démarrer juste avant l opération')


if __name__ == "__main__":
    unittest.main()
