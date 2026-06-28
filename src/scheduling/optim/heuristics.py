'''
Classe mère pour toutes les heuristiques du TP.

@author: Vassilissa Lehoux
'''
from typing import Dict

from src.scheduling.instance.instance import Instance
from src.scheduling.solution import Solution


class Heuristic(object):
    '''
    Classe abstraite dont héritent toutes les heuristiques.
    Définit l'interface commune : constructeur avec paramètres et
    méthode run().
    '''

    def __init__(self, params: Dict = None):
        '''
        Constructeur.
        @param params: dictionnaire de paramètres (optionnel). Les sous-classes
                       doivent définir leurs valeurs par défaut dans run().
        '''
        self._params = params if params is not None else {}

    def run(self, instance: Instance, params: Dict = None) -> Solution:
        '''
        Calcule une solution pour l'instance donnée.
        @param instance: instance du problème à résoudre
        @param params:   paramètres spécifiques à l'exécution (peuvent
                         surcharger ceux du constructeur)
        @return:         Solution calculée
        '''
        raise NotImplementedError("La méthode run() doit être implémentée.")  # pragma: no cover
