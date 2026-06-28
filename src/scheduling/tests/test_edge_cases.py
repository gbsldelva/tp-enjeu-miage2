'''
Tests des cas limites (edge cases) pour le TP d'ordonnancement à contraintes
énergétiques.

Ces tests complètent les tests principaux (test_machine, test_job,
test_solution, test_optim, test_coverage) en ciblant explicitement les
situations limites du modèle :

  - instance pour laquelle AUCUNE solution réalisable n'existe
    (cf. TP, question 4) ;
  - indépendance des solutions construites successivement sur la même
    instance (mécanisme freeze/snapshot, évite le bug d'aliasing) ;
  - assertions et no-op de Machine.stop / Machine.close ;
  - contraintes de précédence : prédécesseurs multiples, opération non prête,
    bornes exactes ;
  - cohérence entre estimate_start_time (estimation) et add_operation (effet) ;
  - décalage d'une opération par le temps de démarrage (setup) ;
  - évaluation des solutions vides / non réalisables (pénalité) ;
  - respect des précédences par apply_sequence même avec une séquence
    volontairement désordonnée ;
  - round-trip to_csv / from_csv conservant l'objectif et les métriques ;
  - voisinages sur une instance mono-job (aucun échange inter-jobs possible) ;
  - convergence de la recherche locale vers un optimum local (point fixe).

@author: tests complémentaires (cas limites)
'''
import os
import tempfile
import unittest

from src.scheduling.instance.instance import Instance
from src.scheduling.instance.machine import Machine
from src.scheduling.instance.operation import Operation
from src.scheduling.solution import Solution
from src.scheduling.optim.constructive import Greedy, NonDeterminist
from src.scheduling.optim.neighborhoods import MyNeighborhood1, MyNeighborhood2
from src.scheduling.optim.local_search import (
    FirstNeighborLocalSearch, BestNeighborLocalSearch
)
from src.scheduling.tests.test_utils import TEST_FOLDER_DATA


# ===========================================================================
# Opération : précédences, planification, reset
# ===========================================================================

class TestOperationEdgeCases(unittest.TestCase):
    '''Cas limites de la classe Operation.'''

    def test_min_start_time_no_predecessor(self):
        '''Sans prédécesseur, l'heure de début minimale est 0.'''
        op = Operation(0, 0)
        op.add_machine_option(0, 5, 5)
        self.assertEqual(op.min_start_time, 0)

    def test_min_start_time_multiple_predecessors(self):
        '''
        Avec plusieurs prédécesseurs, min_start_time est le maximum de leurs
        dates de fin (le plus tardif contraint le démarrage).
        '''
        p1 = Operation(0, 0); p1.add_machine_option(0, 5, 5)
        p2 = Operation(0, 1); p2.add_machine_option(0, 5, 5)
        child = Operation(0, 2); child.add_machine_option(0, 5, 5)
        p1.schedule(0, 10, check_success=False)   # fin = 15
        p2.schedule(0, 20, check_success=False)   # fin = 25
        child.add_predecessor(p1)
        child.add_predecessor(p2)
        self.assertEqual(child.min_start_time, 25)

    def test_is_ready_boundary_and_unassigned(self):
        '''
        is_ready est faux tant que le prédécesseur n'est pas planifié, faux
        avant sa fin, et vrai dès l'instant exact de sa fin (borne incluse).
        '''
        pred = Operation(0, 0); pred.add_machine_option(0, 5, 5)
        op   = Operation(0, 1); op.add_machine_option(0, 5, 5)
        op.add_predecessor(pred)
        self.assertFalse(op.is_ready(100),
                         'prédécesseur non planifié → jamais prêt')
        pred.schedule(0, 10, check_success=False)   # fin = 15
        self.assertFalse(op.is_ready(14), 'pas prêt avant la fin du prédécesseur')
        self.assertTrue(op.is_ready(15), 'prêt exactement à la fin du prédécesseur')
        self.assertTrue(op.is_ready(20))

    def test_schedule_success_when_ready(self):
        '''
        schedule(check_success=True) réussit (retourne True) lorsque les
        précédences sont satisfaites — complète le test d'échec existant.
        '''
        op = Operation(0, 0)
        op.add_machine_option(1, 12, 12)
        self.assertTrue(op.schedule(1, 0, check_success=True))
        self.assertTrue(op.assigned)
        self.assertEqual(op.assigned_to, 1)
        self.assertEqual(op.end_time, 12)

    def test_schedule_ineligible_machine_raises(self):
        '''
        Planifier sur une machine non éligible lève KeyError (le couple
        op/machine n'a pas de durée définie). Documente le comportement.
        '''
        op = Operation(0, 0)
        op.add_machine_option(0, 5, 5)
        with self.assertRaises(KeyError):
            op.schedule(99, 0, check_success=False)

    def test_reset_clears_all_schedule_info(self):
        '''Après reset, toutes les informations de planification valent -1.'''
        op = Operation(0, 0)
        op.add_machine_option(0, 5, 5)
        op.schedule(0, 10, check_success=False)
        op.reset()
        self.assertFalse(op.assigned)
        self.assertEqual(op.assigned_to, -1)
        self.assertEqual(op.start_time, -1)
        self.assertEqual(op.end_time, -1)
        self.assertEqual(op.processing_time, -1)
        self.assertEqual(op.energy, -1)


# ===========================================================================
# Machine : sessions, arrêt, énergie, estimation
# ===========================================================================

class TestMachineEdgeCases(unittest.TestCase):
    '''Cas limites de la classe Machine.'''

    def test_stop_non_running_raises(self):
        '''Arrêter une machine éteinte lève une AssertionError.'''
        m = Machine(0, 5, 2, 5, 2, 1, 100)
        with self.assertRaises(AssertionError):
            m.stop(0)

    def test_stop_before_available_time_raises(self):
        '''
        Arrêter une machine avant la fin de sa dernière opération lève une
        AssertionError (on ne peut pas éteindre pendant une opération).
        '''
        m  = Machine(0, 5, 2, 5, 2, 1, 100)
        op = Operation(0, 0); op.add_machine_option(0, 10, 5)
        m.add_operation(op, 0)               # fin = 15, available_time = 15
        with self.assertRaises(AssertionError):
            m.stop(0)

    def test_close_non_running_is_noop(self):
        '''Fermer une machine jamais démarrée ne fait rien (pas d'exception).'''
        m = Machine(0, 5, 2, 5, 2, 1, 100)
        m.close()
        self.assertEqual(m.start_times, [])
        self.assertEqual(m.stop_times, [])
        self.assertFalse(m.running)

    def test_close_reduces_energy_and_sets_teardown(self):
        '''
        close() éteint la machine juste après la dernière opération : l'énergie
        d'inactivité de fin de session disparaît et stop_time = fin + teardown.
        '''
        m  = Machine(0, 5, 2, 5, 2, 3, 500)
        op = Operation(0, 0); op.add_machine_option(0, 10, 5)
        m.add_operation(op, 0)               # start=5, end=15, available=15
        energy_open = m.total_energy_consumption
        m.close()
        energy_closed = m.total_energy_consumption
        self.assertLess(energy_closed, energy_open,
                        'close() doit réduire l énergie d inactivité')
        # setup(2) + teardown(2) + 0 idle + op(5) = 9
        self.assertEqual(energy_closed, 9)
        self.assertEqual(m.stop_times[0], m.available_time + m.tear_down_time)

    def test_unused_machine_zero_energy(self):
        '''Une machine jamais utilisée ne consomme aucune énergie.'''
        m = Machine(0, 5, 2, 5, 2, 1, 100)
        self.assertEqual(m.total_energy_consumption, 0.0)
        self.assertEqual(m.working_time, 0)

    def test_operation_delayed_by_setup(self):
        '''
        Si l'heure de début demandée est inférieure au temps de démarrage,
        la machine démarre à t=0 et l'opération attend la fin du setup.
        '''
        m  = Machine(0, 15, 4, 15, 4, 1, 100)
        op = Operation(0, 0); op.add_machine_option(0, 5, 6)
        start = m.add_operation(op, 3)       # min_start=3 < setup=15
        self.assertEqual(start, 15, 'l opération doit attendre la fin du setup')
        self.assertEqual(op.start_time, 15)
        self.assertEqual(m.start_times[0], 0, 'la machine démarre à t=0')

    def test_estimate_start_time_matches_add_operation_fresh(self):
        '''
        estimate_start_time prédit exactement l'heure de début effective
        d'add_operation pour une machine éteinte (cohérence indispensable
        au filtrage de faisabilité du glouton).
        '''
        m  = Machine(0, 15, 4, 15, 4, 1, 100)
        op = Operation(0, 0); op.add_machine_option(0, 5, 6)
        estimated = m.estimate_start_time(0)
        actual    = m.add_operation(op, 0)
        self.assertEqual(estimated, actual)

    def test_estimate_start_time_matches_add_operation_running(self):
        '''Même cohérence lorsque la machine est déjà allumée (petit trou).'''
        m   = Machine(0, 5, 2, 5, 2, 1, 200)
        op0 = Operation(0, 0); op0.add_machine_option(0, 10, 5)
        op1 = Operation(1, 1); op1.add_machine_option(0, 10, 5)
        m.add_operation(op0, 0)              # running, available = 15
        estimated = m.estimate_start_time(8)
        actual    = m.add_operation(op1, 8)
        self.assertEqual(estimated, actual)

    def test_estimate_start_time_matches_add_operation_interrupt(self):
        '''
        Cohérence dans le cas d'une interruption automatique : un grand trou
        (≥ teardown + setup) tout en restant allumée déclenche une extinction
        puis un redémarrage. estimate_start_time doit prédire la même heure
        que celle effectivement appliquée par add_operation.
        '''
        m   = Machine(0, 5, 2, 5, 2, 1, 200)
        op0 = Operation(0, 0); op0.add_machine_option(0, 10, 5)
        op1 = Operation(1, 1); op1.add_machine_option(0, 10, 5)
        m.add_operation(op0, 0)             # fin = 15, machine allumée
        estimated = m.estimate_start_time(100)   # grand trou → interruption
        actual    = m.add_operation(op1, 100)
        self.assertEqual(estimated, actual)
        self.assertEqual(len(m.start_times), 2,
                         'l interruption doit créer une seconde session')

    def test_small_gap_keeps_single_session(self):
        '''
        Un petit trou (< teardown + setup) ne provoque pas d'interruption :
        la machine reste allumée (une seule session).
        '''
        m   = Machine(0, 5, 2, 5, 2, 1, 200)
        op0 = Operation(0, 0); op0.add_machine_option(0, 10, 5)
        op1 = Operation(1, 1); op1.add_machine_option(0, 10, 5)
        m.add_operation(op0, 0)             # fin = 15
        m.add_operation(op1, 18)           # trou = 3 < 10
        self.assertEqual(len(m.start_times), 1,
                         'un petit trou ne doit pas créer de nouvelle session')


# ===========================================================================
# Instance sans solution réalisable (TP — question 4)
# ===========================================================================

class TestInfeasibleInstance(unittest.TestCase):
    '''
    Instance jsp_infeasible : une seule opération de durée 10 sur une machine
    dont l'échéance (15) est trop courte pour setup(10) + traitement(10) +
    teardown(10). Aucune solution réalisable n'existe (réponse à la question 4
    du TP). Les heuristiques doivent néanmoins planifier l'opération et
    signaler la non-réalisabilité.
    '''

    def setUp(self):
        self.inst = Instance.from_file(
            TEST_FOLDER_DATA + os.path.sep + "jsp_infeasible")

    def test_instance_loads_correctly(self):
        '''L'instance se charge avec les bons effectifs.'''
        self.assertEqual(self.inst.nb_jobs, 1)
        self.assertEqual(self.inst.nb_machines, 1)
        self.assertEqual(self.inst.nb_operations, 1)
        self.assertEqual(self.inst.name, "jsp_infeasible")

    def test_greedy_assigns_all_but_infeasible(self):
        '''
        Le glouton planifie toutes les opérations (couverture maximale) mais
        la solution reste non réalisable.
        '''
        sol = Greedy().run(self.inst)
        self.assertTrue(all(op.assigned for op in sol.all_operations),
                        'même infaisable, toutes les opérations sont planifiées')
        self.assertFalse(sol.is_feasible,
                         'aucune solution réalisable n existe pour cette instance')

    def test_infeasible_objective_carries_penalty(self):
        '''La solution non réalisable est fortement pénalisée (≥ LAMBDA).'''
        sol = Greedy().run(self.inst)
        self.assertGreaterEqual(sol.objective, Solution.LAMBDA,
                                'une solution non réalisable doit être pénalisée')

    def test_nondeterminist_also_infeasible(self):
        '''L'heuristique non déterministe aboutit aussi à l'infaisabilité.'''
        sol = NonDeterminist().run(self.inst, params={'seed': 0})
        self.assertFalse(sol.is_feasible)


# ===========================================================================
# Solution : snapshot, évaluation, précédences, round-trip CSV
# ===========================================================================

class TestSolutionEdgeCases(unittest.TestCase):
    '''Cas limites de la classe Solution.'''

    def setUp(self):
        self.path = TEST_FOLDER_DATA + os.path.sep + "jsp1"
        self.inst = Instance.from_file(self.path)

    def test_snapshot_independence(self):
        '''
        Une solution figée ne doit pas être altérée par la construction
        d'autres solutions sur la MÊME instance (évite le bug d'aliasing :
        l'état d'ordonnancement est partagé, seul le snapshot protège).
        '''
        solA   = Greedy().run(self.inst)
        before = (solA.objective, solA.cmax, solA.sum_ci,
                  solA.total_energy_consumption)
        NonDeterminist().run(self.inst, params={'seed': 1})
        NonDeterminist().run(self.inst, params={'seed': 2})
        after  = (solA.objective, solA.cmax, solA.sum_ci,
                  solA.total_energy_consumption)
        self.assertEqual(before, after,
                         'la solution figée doit rester indépendante')

    def test_empty_solution_is_penalized(self):
        '''
        Une solution vide (aucune opération planifiée) est non réalisable et
        fortement pénalisée (réponse au TP Q3 : évaluer une solution non
        réalisable).
        '''
        sol = Solution(self.inst)
        self.assertFalse(sol.is_feasible)
        self.assertGreaterEqual(sol.objective, Solution.LAMBDA)

    def test_feasible_objective_has_no_penalty(self):
        '''
        Pour une solution réalisable, l'objectif vaut exactement la somme
        énergie + Cmax + ΣCi (aucune pénalité).
        '''
        sol = Greedy().run(self.inst)
        self.assertTrue(sol.is_feasible)
        expected = sol.total_energy_consumption + sol.cmax + sol.sum_ci
        self.assertAlmostEqual(sol.objective, expected, places=5)

    def test_apply_sequence_respects_precedence(self):
        '''
        apply_sequence respecte les précédences même si la séquence place les
        successeurs avant leurs prédécesseurs : une opération n'est planifiée
        que lorsque ses prédécesseurs le sont.
        '''
        sol = Solution(self.inst)
        # Séquence volontairement désordonnée (op1 avant op0, op3 avant op2)
        sol.apply_sequence([(1, 0), (0, 0), (3, 0), (2, 0)])
        o0, o1 = self.inst.get_operation(0), self.inst.get_operation(1)
        o2, o3 = self.inst.get_operation(2), self.inst.get_operation(3)
        self.assertLessEqual(o0.end_time, o1.start_time,
                             'job 0 : op0 doit finir avant le début de op1')
        self.assertLessEqual(o2.end_time, o3.start_time,
                             'job 1 : op2 doit finir avant le début de op3')
        self.assertTrue(all(op.assigned for op in sol.all_operations))

    def test_restore_reapplies_snapshot(self):
        '''
        restore() réapplique le snapshot sur l'instance même après qu'une
        autre solution a modifié l'état partagé.
        '''
        solA = Greedy().run(self.inst)
        seqA = solA.schedule_sequence
        # Une autre solution écrase l'état de l'instance
        NonDeterminist().run(self.inst, params={'seed': 7})
        solA.restore()
        for op_id, machine_id in seqA:
            self.assertEqual(self.inst.get_operation(op_id).assigned_to,
                             machine_id,
                             'après restore, l instance doit refléter solA')

    def test_from_csv_preserves_metrics(self):
        '''
        Le round-trip to_csv → from_csv reproduit exactement l'objectif et
        toutes les métriques (sérialisation fidèle de la solution).
        '''
        sol = Greedy().run(self.inst)
        ref = (sol.objective, sol.cmax, sol.sum_ci,
               sol.total_energy_consumption)
        with tempfile.TemporaryDirectory() as tmpdir:
            sol.to_csv(tmpdir)
            new_inst = Instance.from_file(self.path)
            new_sol  = Solution(new_inst)
            new_sol.from_csv(tmpdir,
                             os.path.join(tmpdir, 'sol_op.csv'),
                             os.path.join(tmpdir, 'sol_mach.csv'))
            self.assertEqual(
                (new_sol.objective, new_sol.cmax, new_sol.sum_ci,
                 new_sol.total_energy_consumption), ref,
                'from_csv doit reproduire les métriques de la solution')

    def test_schedule_sequence_live_when_not_frozen(self):
        '''
        schedule_sequence reconstruit la séquence depuis l'état courant quand
        la solution n'est pas figée (branche sans snapshot).
        '''
        sol = Solution(self.inst)
        sol.schedule(self.inst.operations[0], self.inst.machines[1])
        sol.schedule(self.inst.operations[2], self.inst.machines[1])
        self.assertEqual(sol.schedule_sequence, [(0, 1), (2, 1)])


# ===========================================================================
# Voisinages : instance mono-job (aucun échange inter-jobs)
# ===========================================================================

class TestNeighborhoodEdgeCases(unittest.TestCase):
    '''
    Sur une instance mono-job (jsp_single), le voisinage par échange
    d'opérations (MyNeighborhood2) ne peut produire aucun voisin : toutes les
    paires consécutives appartiennent au même job. Les méthodes doivent donc
    renvoyer la solution initiale elle-même.
    '''

    def setUp(self):
        self.inst = Instance.from_file(
            TEST_FOLDER_DATA + os.path.sep + "jsp_single")
        self.sol = Greedy().run(self.inst)

    def test_n2_best_neighbor_no_interjob_swap(self):
        '''best_neighbor renvoie la solution initiale (aucun échange possible).'''
        nb = MyNeighborhood2(self.inst)
        self.assertIs(nb.best_neighbor(self.sol), self.sol)

    def test_n2_first_better_neighbor_no_interjob_swap(self):
        '''first_better_neighbor renvoie la solution initiale.'''
        nb = MyNeighborhood2(self.inst)
        self.assertIs(nb.first_better_neighbor(self.sol), self.sol)

    def test_n1_best_neighbor_not_worse(self):
        '''
        La réaffectation de machine ne dégrade jamais la solution, même sur
        une instance mono-job.
        '''
        nb = MyNeighborhood1(self.inst)
        self.assertLessEqual(nb.best_neighbor(self.sol).objective,
                             self.sol.objective)

    def test_n2_finds_improving_swap_when_one_exists(self):
        '''
        Lorsqu'un échange d'opérations consécutives de jobs différents améliore
        la solution, MyNeighborhood2 doit le trouver (et non se contenter de ne
        pas dégrader). On part d'un ordonnancement sous-optimal connu de jsp1.
        '''
        inst = Instance.from_file(TEST_FOLDER_DATA + os.path.sep + "jsp1")
        sol  = Solution(inst)
        # Ordonnancement réalisable mais sous-optimal (vérifié empiriquement) :
        # un échange adjacent inter-jobs réduit l'objectif.
        sol.apply_sequence([(0, 0), (1, 0), (2, 0), (3, 1)])
        self.assertTrue(sol.is_feasible)

        nb     = MyNeighborhood2(inst)
        better = nb.first_better_neighbor(sol)
        self.assertIsNot(better, sol, 'un voisin améliorant doit être trouvé')
        self.assertLess(better.objective, sol.objective,
                        'le voisin retourné doit améliorer l objectif')
        # best_neighbor doit aussi améliorer (au moins autant que first_better)
        self.assertLess(nb.best_neighbor(sol).objective, sol.objective)


# ===========================================================================
# Recherche locale : optimum local, bornes d'itérations
# ===========================================================================

class TestLocalSearchEdgeCases(unittest.TestCase):
    '''Cas limites des recherches locales.'''

    def setUp(self):
        self.inst = Instance.from_file(TEST_FOLDER_DATA + os.path.sep + "jsp1")

    def test_first_neighbor_ls_converges_to_local_optimum(self):
        '''
        Après convergence, la solution renvoyée est un optimum local : un
        nouvel appel à first_better_neighbor ne trouve plus d'amélioration
        (renvoie le même objet — point fixe).
        '''
        sol = FirstNeighborLocalSearch().run(
            self.inst, NonDeterminist, MyNeighborhood1,
            params={'seed': 0, 'max_iterations': 200})
        nb = MyNeighborhood1(self.inst)
        self.assertIs(nb.first_better_neighbor(sol), sol,
                      'la solution finale doit être un optimum local')

    def test_zero_iterations_returns_initial(self):
        '''
        Avec max_iterations=0, la recherche locale renvoie la solution
        initiale inchangée (boucle non exécutée).
        '''
        init = NonDeterminist().run(self.inst, params={'seed': 5})
        sol  = FirstNeighborLocalSearch().run(
            self.inst, NonDeterminist, MyNeighborhood1,
            params={'seed': 5, 'max_iterations': 0})
        self.assertEqual(sol.objective, init.objective)

    def test_best_neighbor_ls_not_worse_than_init(self):
        '''
        La recherche locale meilleur améliorant ne dégrade jamais la solution
        initiale.
        '''
        init = NonDeterminist().run(self.inst, params={'seed': 0})
        sol  = BestNeighborLocalSearch().run(
            self.inst, NonDeterminist, MyNeighborhood1,
            params={'seed': 0, 'max_iterations': 50})
        self.assertLessEqual(sol.objective, init.objective)


if __name__ == "__main__":
    unittest.main()
