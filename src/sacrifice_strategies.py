from typing import Union, TYPE_CHECKING
import numpy as np

from utils import Constants, Helper

if TYPE_CHECKING:
    from ad_dimboost_optimizer import Runner


class SacrificeStrategy:
    def __init__(self):
        self.is_real_sacrifice_strategy = None
        self.is_constant_sacrifice_strategy = None
        self.sacrifices_length = None
    
    def next_sacrifices(self, runner: 'Runner', line: int) -> np.ndarray:
        if self.is_constant_sacrifice_strategy and hasattr(self, 'stored_array'):
            return self.stored_array
        simple_list = self.next_sacrifices_short_list(runner, line)
        simple_list.extend([Constants.no_action_const] * (self.sacrifices_length - len(simple_list)))
        result = np.array(simple_list, dtype=runner.allowed_sacrifices.dtype)
        if self.is_constant_sacrifice_strategy:
            self.stored_array = result
        return result
    
    def next_sacrifices_short_list(self, runner: 'Runner', line: int) -> list:
        raise NotImplementedError("SacrificeStrategy must implement next_sacrifices_short_list")

class NeverSacrificeStrategy(SacrificeStrategy):
    def __init__(self):
        self.is_real_sacrifice_strategy = False
        self.is_constant_sacrifice_strategy = True
        self.sacrifices_length = 1
    
    def next_sacrifices_short_list(self, runner: 'Runner', line: int) -> list:
        return [Constants.sacrifice_infinity]

class IncrementalSacrificeStrategy(SacrificeStrategy):
    def __init__(self, sacrifice_step):
        self.is_real_sacrifice_strategy = True
        self.is_constant_sacrifice_strategy = True
        self.sacrifice_step = sacrifice_step
        count = int((Constants.sacrifice_max - 1) / sacrifice_step)
        self.sacrifices_length = count + 2
    
    def next_sacrifices_short_list(self, runner: 'Runner', line: int) -> list:
        next_sacrifices_list = list(np.arange(1 + self.sacrifice_step, Constants.sacrifice_max, self.sacrifice_step))
        next_sacrifices_list.append(Constants.sacrifice_infinity)
        return next_sacrifices_list

class SacrificeStrategyWithList(NeverSacrificeStrategy):
    def __init__(self, sacrifice_list: Union[list, None]=None):
        self.is_real_sacrifice_strategy = True
        self.is_constant_sacrifice_strategy = False
        self.sacrifices_length = 1
        
        if sacrifice_list is None:
            sacrifice_list = []
        self.sacrifice_list = sacrifice_list
    
    def next_sacrifices_short_list(self, runner: 'Runner', line: int) -> list:
        actions_num = runner.actions_item_lists[line][0]
        sacrifices_num = 0
        real_total_sacrifice_boost = 1
        for action_pos in range(1, actions_num + 1):
            if runner.actions_item_lists[line][action_pos] != Constants.sacrifice_action_const:
                continue
            sacrifices_num += 1
            real_total_sacrifice_boost *= runner.actions_info_lists[line][action_pos]
        
        if sacrifices_num >= len(self.sacrifice_list):
            return [Constants.sacrifice_infinity]
        
        predicted_total_sacrifice_boost = 1
        for sacrifice_boost in self.sacrifice_list[:sacrifices_num]:
            predicted_total_sacrifice_boost *= sacrifice_boost
        
        predicted_next_sacrifice_boost = self.sacrifice_list[sacrifices_num]
        calibrated_next_sacrifice_boost = predicted_next_sacrifice_boost * predicted_total_sacrifice_boost / real_total_sacrifice_boost
        
        return [calibrated_next_sacrifice_boost]

class SacrificeStrategyFromActionList(SacrificeStrategyWithList):
    def __init__(self, actions_readable_list: str):
        super().__init__(Helper.parse_action_list_for_sacrifices(actions_readable_list))

class SacrificeStrategyFromFile(SacrificeStrategyFromActionList):
    def __init__(self, filename: str):
        super().__init__(Helper.parse_file_for_action_list(filename))
