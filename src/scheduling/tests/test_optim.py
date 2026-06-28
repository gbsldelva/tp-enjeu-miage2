'''
Tests pour les modules d'optimisation :
  - optim/constructive.py  (Greedy, NonDeterminist)
  - optim/neighborhoods.py (MyNeighborhood1, MyNeighborhood2)
  - optim/local_search.py  (FirstNeighborLocalSearch, BestNeighborLocalSearch)

@author: Vassilissa Lehoux
'''
import unittest
import os

from src.scheduling.instance.instance import Instance
from src.scheduling.solution import Solution
from src.scheduling.optim.constructive import Greedy, NonDeterminist
from src.scheduling.optim.neighborhoods import MyNeighborhood1, MyNeighborhood2
from src.scheduling.optim.local_search import (
    FirstNeighborLocalSearch, BestNeighborLocalSearch
)
from src.scheduling.tests.test_utils import TEST_FOLDER_DATA


class TestGreedy(unittest.TestCase):
    '''Tests pour l'heuristique gloutonne déterministe.'''

    def setUp(self):
        self.inst = Instance.from_file(TEST_FOLDER_DATA + os.path.sep + "jsp1")

    def test_greedy_returns_solution(self):
        '''Greedy doit retourner une Solution valide.'''
        sol = Greedy().run(self.inst)
        self.assertIsInstance(sol, Solution, 'Greedy doit retourner une Solution')

    def test_greedy_all_ops_assigned(self):
        '''Greedy doit planifier toutes les opérations.'''
        sol = Greedy().run(self.inst)
        self.assertTrue(all(op.assigned for op in sol.all_operations),
                        'Toutes les opérations doivent être planifiées')

    def test_greedy_feasible(self):
        '''Greedy doit produire une solution réalisable sur jsp1.'''
        sol = Greedy().run(self.inst)
        self.assertTrue(sol.is_feasible,
                        'Greedy doit produire une solution réalisable sur jsp1')

    def test_greedy_deterministic(self):
        '''Greedy doit produire le même résultat à chaque exécution.'''
        sol1 = Greedy().run(self.inst)
        sol2 = Greedy().run(self.inst)
        self.assertEqual(sol1.objective, sol2.objective,
                         'Greedy est déterministe : même objectif à chaque run')

    def test_greedy_positive_objective(self):
        '''La valeur objective doit être positive.'''
        sol = Greedy().run(self.inst)
        self.assertGreater(sol.objective, 0, 'Objectif doit être positif')


class TestNonDeterminist(unittest.TestCase):
    '''Tests pour l'heuristique non déterministe.'''

    def setUp(self):
        self.inst = Instance.from_file(TEST_FOLDER_DATA + os.path.sep + "jsp1")

    def test_nondeterminist_returns_solution(self):
        '''NonDeterminist doit retourner une Solution valide.'''
        sol = NonDeterminist().run(self.inst)
        self.assertIsInstance(sol, Solution)

    def test_nondeterminist_all_ops_assigned(self):
        '''NonDeterminist doit planifier toutes les opérations.'''
        sol = NonDeterminist().run(self.inst)
        self.assertTrue(all(op.assigned for op in sol.all_operations))

    def test_nondeterminist_same_seed_same_result(self):
        '''Même seed → même résultat.'''
        sol1 = NonDeterminist().run(self.inst, params={'seed': 42})
        sol2 = NonDeterminist().run(self.inst, params={'seed': 42})
        self.assertEqual(sol1.objective, sol2.objective,
                         'Même seed doit produire le même objectif')

    def test_nondeterminist_different_seeds(self):
        '''
        Des seeds différents peuvent produire des solutions différentes.
        (Pas garanti mais très probable sur une instance avec plusieurs
        machines éligibles.)
        '''
        objectives = set()
        for seed in range(10):
            sol = NonDeterminist().run(self.inst, params={'seed': seed})
            objectives.add(sol.objective)
        # Au moins 2 valeurs différentes parmi 10 runs
        self.assertGreater(len(objectives), 1,
                           'Des seeds différents doivent parfois donner des '
                           'solutions différentes')

    def test_nondeterminist_k_parameter(self):
        '''Paramètre k=1 doit se comporter comme un glouton aléatoire.'''
        sol = NonDeterminist().run(self.inst, params={'k': 1, 'seed': 0})
        self.assertTrue(all(op.assigned for op in sol.all_operations))


class TestMyNeighborhood1(unittest.TestCase):
    '''Tests pour le voisinage MachineReassignment.'''

    def setUp(self):
        self.inst = Instance.from_file(TEST_FOLDER_DATA + os.path.sep + "jsp1")
        self.sol  = Greedy().run(self.inst)

    def test_best_neighbor_returns_solution(self):
        '''best_neighbor doit retourner une Solution.'''
        nb  = MyNeighborhood1(self.inst)
        res = nb.best_neighbor(self.sol)
        self.assertIsInstance(res, Solution)

    def test_best_neighbor_not_worse(self):
        '''best_neighbor ne doit pas retourner une solution pire.'''
        nb  = MyNeighborhood1(self.inst)
        res = nb.best_neighbor(self.sol)
        self.assertLessEqual(res.objective, self.sol.objective,
                             'best_neighbor ne doit pas dégrader la solution')

    def test_first_better_neighbor_returns_solution(self):
        '''first_better_neighbor doit retourner une Solution.'''
        nb  = MyNeighborhood1(self.inst)
        res = nb.first_better_neighbor(self.sol)
        self.assertIsInstance(res, Solution)

    def test_first_better_neighbor_not_worse(self):
        '''first_better_neighbor ne doit pas retourner une solution pire.'''
        nb  = MyNeighborhood1(self.inst)
        res = nb.first_better_neighbor(self.sol)
        self.assertLessEqual(res.objective, self.sol.objective,
                             'first_better_neighbor ne doit pas dégrader')


class TestMyNeighborhood2(unittest.TestCase):
    '''Tests pour le voisinage OperationSwap.'''

    def setUp(self):
        self.inst = Instance.from_file(TEST_FOLDER_DATA + os.path.sep + "jsp1")
        self.sol  = Greedy().run(self.inst)

    def test_best_neighbor_returns_solution(self):
        '''best_neighbor doit retourner une Solution.'''
        nb  = MyNeighborhood2(self.inst)
        res = nb.best_neighbor(self.sol)
        self.assertIsInstance(res, Solution)

    def test_best_neighbor_not_worse(self):
        '''best_neighbor ne doit pas retourner une solution pire.'''
        nb  = MyNeighborhood2(self.inst)
        res = nb.best_neighbor(self.sol)
        self.assertLessEqual(res.objective, self.sol.objective)

    def test_first_better_neighbor_returns_solution(self):
        '''first_better_neighbor doit retourner une Solution.'''
        nb  = MyNeighborhood2(self.inst)
        res = nb.first_better_neighbor(self.sol)
        self.assertIsInstance(res, Solution)


class TestFirstNeighborLocalSearch(unittest.TestCase):
    '''Tests pour la recherche locale premier améliorant.'''

    def setUp(self):
        self.inst = Instance.from_file(TEST_FOLDER_DATA + os.path.sep + "jsp1")

    def test_run_returns_solution(self):
        '''FirstNeighborLocalSearch doit retourner une Solution.'''
        heur = FirstNeighborLocalSearch()
        sol  = heur.run(self.inst, NonDeterminist, MyNeighborhood1,
                        params={'seed': 0, 'max_iterations': 10})
        self.assertIsInstance(sol, Solution)

    def test_run_all_ops_assigned(self):
        '''La solution doit avoir toutes les opérations planifiées.'''
        heur = FirstNeighborLocalSearch()
        sol  = heur.run(self.inst, NonDeterminist, MyNeighborhood1,
                        params={'seed': 0, 'max_iterations': 10})
        self.assertTrue(all(op.assigned for op in sol.all_operations))

    def test_run_improves_or_equals_init(self):
        '''
        La recherche locale doit produire une solution au moins aussi bonne
        que la solution initiale.
        '''
        init_sol = NonDeterminist().run(self.inst, params={'seed': 0})
        heur     = FirstNeighborLocalSearch()
        sol      = heur.run(self.inst, NonDeterminist, MyNeighborhood1,
                            params={'seed': 0, 'max_iterations': 50})
        self.assertLessEqual(sol.objective, init_sol.objective,
                             'La recherche locale ne doit pas dégrader la solution')


class TestBestNeighborLocalSearch(unittest.TestCase):
    '''Tests pour la recherche locale meilleur améliorant.'''

    def setUp(self):
        self.inst = Instance.from_file(TEST_FOLDER_DATA + os.path.sep + "jsp1")

    def test_run_returns_solution(self):
        '''BestNeighborLocalSearch doit retourner une Solution.'''
        heur = BestNeighborLocalSearch()
        sol  = heur.run(self.inst, NonDeterminist, MyNeighborhood1,
                        params={'seed': 0, 'max_iterations': 5})
        self.assertIsInstance(sol, Solution)

    def test_run_all_ops_assigned(self):
        '''La solution doit avoir toutes les opérations planifiées.'''
        heur = BestNeighborLocalSearch()
        sol  = heur.run(self.inst, NonDeterminist, MyNeighborhood1,
                        params={'seed': 0, 'max_iterations': 5})
        self.assertTrue(all(op.assigned for op in sol.all_operations))


if __name__ == "__main__":
    unittest.main()
