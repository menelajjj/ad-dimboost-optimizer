from typing import TYPE_CHECKING
import copy

from utils import Helper
from runner import Runner
from purchase_strategies import OptimizedPurchaseStrategy, PurchaseStrategyFromActionList
from sacrifice_strategies import NeverSacrificeStrategy, IncrementalSacrificeStrategy, SacrificeStrategyFromActionList
from live import live_display

if TYPE_CHECKING:
    from purchase_strategies import PurchaseStrategy


class Iterator():
    def __init__(self, purchase_strategy: 'PurchaseStrategy', platform: str, galaxies_bought: int, dimboosts_bought: int) -> None:
        self.purchase_strategy = purchase_strategy
        self.platform = platform
        self.galaxies_bought = galaxies_bought
        self.dimboosts_bought = dimboosts_bought
        
        self.iterative_optimization_info = {
            'total_strategy_search_time': '00:00.000',
            'CPU': Helper.cpu_info(),
            'max_used_memory_mb': 0,
            'total_states_analyzed': 0,
            'number_of_iterations': 0
            }
        self.iterative_optimization_info['iterations'] = []
    
    def add_iteration(self, iteration_info: dict) -> None:
        self.iterative_optimization_info['total_strategy_search_time'] = Helper.sum_times_str(self.iterative_optimization_info['total_strategy_search_time'], iteration_info['strategy_search_info']['strategy_search_time'])
        used_memory_mb = iteration_info['strategy_search_info']['used_memory_mb']
        self.iterative_optimization_info['max_used_memory_mb'] = max(self.iterative_optimization_info['max_used_memory_mb'], used_memory_mb)
        self.iterative_optimization_info['total_states_analyzed'] += iteration_info['strategy_search_info']['states_analyzed']
        self.iterative_optimization_info['number_of_iterations'] += 1
        self.iterative_optimization_info['iterations'].append(iteration_info)

    def save_iterative_optimization_info(self) -> None:
        if len(self.iterative_optimization_info['iterations']) == 1:
            winner_dict = self.iterative_optimization_info['iterations'][0]
            iterative_optimization_info_short = None
        else:
            if len(self.iterative_optimization_info['iterations']) == 2:
                winner_dict = self.iterative_optimization_info['iterations'][-1]
            else:
                winner_dict = self.iterative_optimization_info['iterations'][-3]
        
            iterative_optimization_info_short = copy.deepcopy(self.iterative_optimization_info)
            for iteration in iterative_optimization_info_short['iterations']:
                del iteration['actions_readable_list']
        
        filename = Helper.get_filename(self.purchase_strategy,
                                       winner_dict['game_info']['platform'],
                                       winner_dict['game_info']['galaxies_bought'],
                                       winner_dict['game_info']['dimboosts_bought'],
                                       winner_dict['game_info']['has_sacrifice'])
        Helper.save_winner_dict(winner_dict, iterative_optimization_info_short, filename)
    
    def get_last_actions_readable_list(self) -> str:
        return self.iterative_optimization_info['iterations'][-1]['actions_readable_list']
    
    def get_iteration_number(self) -> int:
        return len(self.iterative_optimization_info['iterations'])+1
    
    def search_and_save(self) -> None:
        runner = Runner(platform=self.platform,
            galaxies_bought=self.galaxies_bought,
            dimboosts_bought=self.dimboosts_bought,
            purchase_strategy=self.purchase_strategy,
            sacrifice_strategy=NeverSacrificeStrategy()
            )
        live_display.update_iteration(current=self.get_iteration_number(),
                                      description="Initial run without sacrifice")
        self.add_iteration(runner.run())
        self.save_iterative_optimization_info()
        if self.dimboosts_bought < 5:
            return
        
        sacrifice_step = 0.001
        last_actions_readable_list = self.get_last_actions_readable_list()
        runner = Runner(platform=self.platform,
            galaxies_bought=self.galaxies_bought,
            dimboosts_bought=self.dimboosts_bought,
            purchase_strategy=PurchaseStrategyFromActionList(last_actions_readable_list),
            sacrifice_strategy=IncrementalSacrificeStrategy(sacrifice_step)
            )
        live_display.update_iteration(current=self.get_iteration_number(),
                                      description="Initial run with incremental sacrifice")
        self.add_iteration(runner.run())
        
        if not self.purchase_strategy.is_fixed_purchase_strategy:
            while True:
                last_actions_readable_list = self.get_last_actions_readable_list()
                runner = Runner(platform=self.platform,
                    galaxies_bought=self.galaxies_bought,
                    dimboosts_bought=self.dimboosts_bought,
                    purchase_strategy=self.purchase_strategy,
                    sacrifice_strategy=SacrificeStrategyFromActionList(last_actions_readable_list)
                    )
                live_display.update_iteration(current=self.get_iteration_number(),
                                              description="Attempt to improve - fixed sacrifices")
                self.add_iteration(runner.run())
                
                last_actions_readable_list = self.get_last_actions_readable_list()
                runner = Runner(platform=self.platform,
                    galaxies_bought=self.galaxies_bought,
                    dimboosts_bought=self.dimboosts_bought,
                    purchase_strategy=PurchaseStrategyFromActionList(last_actions_readable_list),
                    sacrifice_strategy=IncrementalSacrificeStrategy(sacrifice_step)
                    )
                live_display.update_iteration(current=self.get_iteration_number(),
                                              description="Attempt to improve - fixed purchases")
                self.add_iteration(runner.run())
                
                if self.iterative_optimization_info['iterations'][-1]['game_info']['ticks_passed'] >= self.iterative_optimization_info['iterations'][-3]['game_info']['ticks_passed']:
                    break
        
        self.save_iterative_optimization_info()
