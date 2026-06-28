'''
Tests pour la classe Job.

@author: Vassilissa Lehoux
'''
import unittest

from src.scheduling.instance.job import Job
from src.scheduling.instance.operation import Operation
from src.scheduling.instance.machine import Machine


class TestJob(unittest.TestCase):
    '''
    Tests unitaires pour la classe Job.
    On utilise les données de l'instance jsp1 :
      Job 0 : op0 (sur M1, pt=12, start=20, end=32),
              op1 (sur M0, pt=5,  start=32, end=37)
    '''

    def setUp(self):
        # Construire le job 0 à la main (sans Instance)
        self.job0 = Job(0)

        self.op0 = Operation(0, 0)
        self.op0.add_machine_option(1, 12, 12)

        self.op1 = Operation(0, 1)
        self.op1.add_machine_option(0, 5, 6)

        # Ajout dans l'ordre → add_operation pose les précédences
        self.job0.add_operation(self.op0)
        self.job0.add_operation(self.op1)

        # Machine utilisées pour forcer le schedule
        self.m1 = Machine(1, 20, 5, 15, 4, 2, 120)
        self.m0 = Machine(0, 15, 4, 15, 4, 1, 100)

    def tearDown(self):
        pass

    def testCompletionTime(self):
        '''
        Vérifie la date de fin du job (dernière opération planifiée).
        op0 sur M1 → start=20, end=32.
        op1 sur M0 → start=32, end=37.
        completion_time = 37.
        '''
        self.m1.add_operation(self.op0, 0)
        # op1 peut démarrer après op0 (min_start = op0.end_time = 32)
        self.m0.add_operation(self.op1, self.op0.end_time)
        self.assertEqual(self.job0.completion_time, 37,
                         'completion_time incorrect pour job 0')

    def testNextOperation(self):
        '''
        Vérifie que next_operation retourne la bonne opération au fur et à mesure.
        '''
        self.assertEqual(self.job0.next_operation, self.op0,
                         'next_operation doit être op0 au départ')
        self.job0.schedule_operation()
        self.assertEqual(self.job0.next_operation, self.op1,
                         'next_operation doit passer à op1 après schedule_operation')

    def testPlanned(self):
        '''
        Vérifie que planned devient True quand toutes les opérations sont planifiées.
        '''
        self.assertFalse(self.job0.planned,
                         'job non terminé ne doit pas être planned')
        self.job0.schedule_operation()
        self.assertFalse(self.job0.planned,
                         'job partiellement planifié ne doit pas être planned')
        self.job0.schedule_operation()
        self.assertTrue(self.job0.planned,
                        'job entièrement planifié doit être planned')

    def testOperationNb(self):
        '''
        Vérifie le nombre d'opérations du job.
        '''
        self.assertEqual(self.job0.operation_nb, 2,
                         'job 0 doit avoir 2 opérations')

    def testPrecedences(self):
        '''
        Vérifie que add_operation a bien posé les liens prédécesseur/successeur.
        '''
        self.assertIn(self.op0, self.op1.predecessors,
                      'op0 doit être prédécesseur de op1')
        self.assertIn(self.op1, self.op0.successors,
                      'op1 doit être successeur de op0')

    def testReset(self):
        '''
        Vérifie que reset() remet next_index à 0.
        '''
        self.job0.schedule_operation()
        self.job0.reset()
        self.assertEqual(self.job0.next_operation, self.op0,
                         'après reset, next_operation doit revenir à op0')
        self.assertFalse(self.job0.planned,
                         'après reset, le job ne doit pas être planned')


if __name__ == "__main__":
    unittest.main()
