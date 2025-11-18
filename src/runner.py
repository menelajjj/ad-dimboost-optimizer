from typing import Union, TYPE_CHECKING
import ctypes
import time
import os
import psutil
import numpy as np

from utils import ArraysTypes, Constants, Helper
from live import live_display

if TYPE_CHECKING:
    from purchase_strategies import PurchaseStrategy
    from sacrifice_strategies import SacrificeStrategy


cpp_lib = ctypes.CDLL('./cpp_lib.dll')
cpp_lib.find_dominated.argtypes = [
    np.ctypeslib.ndpointer(dtype=ArraysTypes.amounts, flags='C_CONTIGUOUS'), # amounts
    np.ctypeslib.ndpointer(dtype=ArraysTypes.bought_amounts, flags='C_CONTIGUOUS'), # bought_amounts
    np.ctypeslib.ndpointer(dtype=ArraysTypes.sorted_indices, flags='C_CONTIGUOUS'), # sorted_indices
    ctypes.c_int, # num_objects
    ctypes.c_int, # max_dims
    np.ctypeslib.ndpointer(dtype=bool, flags='C_CONTIGUOUS') # dominated_bools
]

cpp_lib.can_buy_all.argtypes = [
    np.ctypeslib.ndpointer(dtype=ArraysTypes.amounts, flags='C_CONTIGUOUS'), # amounts
    np.ctypeslib.ndpointer(dtype=ArraysTypes.costs, flags='C_CONTIGUOUS'), # costs
    np.ctypeslib.ndpointer(dtype=ArraysTypes.allowed_purchases, flags='C_CONTIGUOUS'), # allowed_purchases
    ctypes.c_int, # num_objects
    ctypes.c_int, # max_dims
    np.ctypeslib.ndpointer(dtype=bool, flags='C_CONTIGUOUS') # can_buy_bools
]
cpp_lib.can_buy_all.restype = ctypes.c_bool

cpp_lib.can_sacrifice_all.argtypes = [
    np.ctypeslib.ndpointer(dtype=ArraysTypes.amounts, flags='C_CONTIGUOUS'), # amounts
    np.ctypeslib.ndpointer(dtype=ArraysTypes.allowed_sacrifices, flags='C_CONTIGUOUS'), # allowed_sacrifices
    ctypes.c_int, # num_objects
    ctypes.c_int, # max_dims
    ctypes.c_int, # sacrifices_length
    np.ctypeslib.ndpointer(dtype=ArraysTypes.sacrifice_boosts, flags='C_CONTIGUOUS') # sacrifice_boosts
]
cpp_lib.can_buy_all.restype = ctypes.c_bool


class Runner():
    def __init__(self, platform: str, galaxies_bought: int, dimboosts_bought: int,
                 purchase_strategy: 'PurchaseStrategy',
                 sacrifice_strategy: 'SacrificeStrategy'):
        self.ticks_passed = 0
        self.addition_cycles_without_clear = 0
        self.states_num_after_clear = 0

        self.platform = platform
        self.galaxies_bought = galaxies_bought
        self.dimboosts_bought = dimboosts_bought
        self.purchase_strategy = purchase_strategy
        self.sacrifice_strategy = sacrifice_strategy
        
        self.tick_duration = Constants.tick_duration[platform]
        self.sacrifices_length = sacrifice_strategy.sacrifices_length

        self.max_dims = Helper.max_dims(self.dimboosts_bought)
        self.num_states_reserved = 0
        self.num_states_alltime = 0
        self.num_states_current = 0

        self.actions_item_lists = np.empty((Constants.numpy_reserve_step, Constants.numpy_actions_reserve_step), dtype=ArraysTypes.actions_item_lists)
        self.actions_amount_lists = np.empty((Constants.numpy_reserve_step, Constants.numpy_actions_reserve_step), dtype=ArraysTypes.actions_amount_lists)
        self.actions_info_lists = np.empty((Constants.numpy_reserve_step, Constants.numpy_actions_reserve_step), dtype=ArraysTypes.actions_info_lists)
        self.actions_tick_lists = np.empty((Constants.numpy_reserve_step, Constants.numpy_actions_reserve_step), dtype=ArraysTypes.actions_tick_lists)
        self.allowed_purchases = np.empty((Constants.numpy_reserve_step, 1 + self.max_dims), dtype=ArraysTypes.allowed_purchases)
        self.allowed_sacrifices = np.empty((Constants.numpy_reserve_step, self.sacrifices_length), dtype=ArraysTypes.allowed_sacrifices)
        self.amounts = np.empty((Constants.numpy_reserve_step, 2 + self.max_dims), dtype=ArraysTypes.amounts)
            # amounts[0] is antimatter
            # amounts[1, ..., max_dims] are dims amounts
            # amounts[max_dims+1] is amount of dim 1 sacrificed
        self.bought_amounts = np.empty((Constants.numpy_reserve_step, 1 + self.max_dims), dtype=ArraysTypes.bought_amounts)
            # bought_amounts[0] is bought tickspeed
            # bought_amounts[1-8] are bought dims
        self.costs = np.empty((Constants.numpy_reserve_step, 1 + self.max_dims), dtype=ArraysTypes.costs)
            # costs[0] is tickspeed cost
            # costs[1-8] are dims costs
        self.multipliers = np.empty((Constants.numpy_reserve_step, 1 + self.max_dims), dtype=ArraysTypes.multipliers)
            # multipliers[0] is tickspeed multiplier
            # multipliers[1-8] are dims multipliers
        self.num_states_reserved = Constants.numpy_reserve_step

        self.add_start_state()
        line = 0
        self.max_am = self.amounts[line][0]
        self.buy(line=line, item_int=1)

        self.spent_for_tick = 0
        self.spent_for_tick_at_last_refresh = 0
        self.spent_for_buy = 0
        self.spent_for_buy_at_last_refresh = 0
        self.spent_for_sacrifice = 0
        self.spent_for_sacrifice_at_last_refresh = 0
        self.spent_for_clear = 0
        self.spent_for_clear_at_last_refresh = 0
        self.spent_for_cpp_dominated = 0
        self.spent_for_cpp_dominated_at_last_refresh = 0
        self.spent_for_deleting = 0
        self.spent_for_deleting_at_last_refresh = 0
        self.added_after_refresh = 0
        self.deleted_after_refresh = 0
        self.time_of_last_refresh = None
        self.ticks_of_last_refresh = 0
        
        self.used_memory_mb = 0
        
        live_display.update_config(
            platform=self.platform,
            galaxies_bought=self.galaxies_bought,
            dimboosts_bought=self.dimboosts_bought,
            purchase_strategy_name=type(self.purchase_strategy).__name__,
            sacrifice_strategy_name=type(self.sacrifice_strategy).__name__
        )
        live_display.init_progress_bar(
            current_am=self.max_am,
            total_am=Helper.winner_antimatter(self.galaxies_bought, self.dimboosts_bought))

    def add_start_state(self) -> None:
        line = 0
        self.amounts[line] = np.zeros(self.amounts.shape[1])
        self.amounts[line][0] = Constants.start_antimatter
        self.amounts[line][self.max_dims + 1] = 0
        self.bought_amounts[line] = np.zeros(self.bought_amounts.shape[1])
        self.costs[line][0] = Constants.tickspeed_base_cost
        for tier in range(1, self.max_dims + 1):
            self.costs[line][tier] = Constants.dims_base_costs[tier]
        self.multipliers[line][0] = Constants.tickspeed_base_multiplier
        for tier in range(1, self.max_dims + 1):
            self.multipliers[line][tier] = Constants.dims_base_multipliers[tier]
            if self.platform == 'mobile':
                self.multipliers[line][tier] *= Constants.mobile_dim_multiplier

        self.add_ach_bonuses(line)
        self.add_dimboost_multiplier(line)
        
        self.actions_item_lists[line][0] = 0
        self.actions_amount_lists[line][0] = 0
        self.actions_info_lists[line][0] = 0
        self.actions_tick_lists[line][0] = 0
        self.allowed_purchases[line] = self.purchase_strategy.next_purchases(self, line)
        self.allowed_sacrifices[line] = self.sacrifice_strategy.next_sacrifices(self, line)
        
        self.num_states_alltime += 1
        self.num_states_current += 1

    def add_achs(self, line: int, amount: int) -> None:
        new_ach_multiplier = pow(Constants.ach_multiplier, amount)
        for tier in range(1, self.max_dims + 1):
            self.multipliers[line][tier] *= new_ach_multiplier

    def add_row_ach_mult(self, line: int) -> None:
        for tier in range(1, self.max_dims + 1):
            self.multipliers[line][tier] *= Constants.ach_row_multiplier

    def add_dimboost_multiplier(self, line: int) -> None:
        for tier in range(1, self.max_dims + 1):
            dimboost_count_for_tier = max(0, self.dimboosts_bought - tier + 1)
            if dimboost_count_for_tier > 0:
                self.multipliers[line][tier] *= pow(Constants.dimboost_multiplier, dimboost_count_for_tier)

    def add_ach_bonuses(self, line: int) -> None:
        self.add_achs(line, Helper.start_ach_amount(self.galaxies_bought, self.dimboosts_bought))
        if ((self.galaxies_bought == 0) and (self.dimboosts_bought >= 5)) or (self.galaxies_bought >= 1):
            self.add_row_ach_mult(line) # row 1
        if ((self.galaxies_bought == 1) and (self.dimboosts_bought >= 10)) or (self.galaxies_bought >= 2):
            tier = 8
            if self.max_dims >= tier:
                self.multipliers[line][tier] *= Constants.ach23_multiplier # r23
        if ((self.galaxies_bought == 1) and (self.dimboosts_bought >= 12)) or (self.galaxies_bought >= 2):
            tier = 1
            self.multipliers[line][tier] *= Constants.ach28_multiplier # r28
        if (self.galaxies_bought == 2) and (self.dimboosts_bought >= 15):
            tier = 1
            self.multipliers[line][tier] *= Constants.ach31_multiplier # r31

    def add_ach_for_new_dim(self, line: int, tier: int) -> None:
        if self.galaxies_bought == 0:
            if self.dimboosts_bought == 0:
                self.add_achs(line, 1)
            elif (self.dimboosts_bought == 1) and (tier == 5):
                self.add_achs(line, 1)
            elif (self.dimboosts_bought == 2) and (tier == 6):
                self.add_achs(line, 1)
            elif (self.dimboosts_bought == 3) and (tier == 7):
                self.add_achs(line, 1)
            elif (self.dimboosts_bought == 4) and (tier == 8):
                self.add_achs(line, 1)
                self.add_row_ach_mult(line)

    def extend_actions_lists(self) -> None:
        actions_lists_length = self.actions_item_lists.shape[1]
        new_actions_lists_shape = (self.num_states_reserved, actions_lists_length + Constants.numpy_actions_reserve_step)
        
        new_array = np.empty(new_actions_lists_shape, dtype=self.actions_item_lists.dtype)
        new_array[:, :actions_lists_length] = self.actions_item_lists
        self.actions_item_lists = new_array

        new_array = np.empty(new_actions_lists_shape, dtype=self.actions_amount_lists.dtype)
        new_array[:, :actions_lists_length] = self.actions_amount_lists
        self.actions_amount_lists = new_array
        
        new_array = np.empty(new_actions_lists_shape, dtype=self.actions_info_lists.dtype)
        new_array[:, :actions_lists_length] = self.actions_info_lists
        self.actions_info_lists = new_array
        
        new_array = np.empty(new_actions_lists_shape, dtype=self.actions_tick_lists.dtype)
        new_array[:, :actions_lists_length] = self.actions_tick_lists
        self.actions_tick_lists = new_array

    def add_action(self, line: int, item_int: int, cost: float) -> None:
        prev_action_pos = self.actions_item_lists[line][0]
        if ((self.actions_item_lists[line][prev_action_pos] == item_int) and
            (item_int != Constants.sacrifice_action_const) and
            (self.actions_info_lists[line][prev_action_pos] == cost)):
            self.actions_amount_lists[line][prev_action_pos] += 1
            self.actions_tick_lists[line][prev_action_pos] = self.ticks_passed
            return
        action_pos = self.actions_item_lists[line][0] + 1
        if action_pos == len(self.actions_item_lists[line]):
            self.extend_actions_lists()
        self.actions_item_lists[line][0] = action_pos
        self.actions_item_lists[line][action_pos] = item_int
        self.actions_amount_lists[line][0] = action_pos
        self.actions_amount_lists[line][action_pos] = 1
        self.actions_info_lists[line][0] = action_pos
        self.actions_info_lists[line][action_pos] = cost
        self.actions_tick_lists[line][0] = action_pos
        self.actions_tick_lists[line][action_pos] = self.ticks_passed

    def buy(self, line: int, item_int: int) -> None:
        cost = self.costs[line][item_int]
        self.amounts[line][0] -= cost
        if self.amounts[line][0] < 0:
            raise Exception("Negative antimatter")
        self.bought_amounts[line][item_int] += 1
        if item_int == 0:
            self.costs[line][item_int] *= Constants.tickspeed_base_cost_multiplier
            self.multipliers[line][item_int] *= Constants.tickspeed_multiplier_multipliers[self.galaxies_bought]
        else:
            self.amounts[line][item_int] += 1
            if self.bought_amounts[line][item_int] % 10 == 0:
                self.costs[line][item_int] *= Constants.dims_base_cost_multipliers[item_int]
                self.multipliers[line][item_int] *= Constants.buy_ten_multiplier
            elif self.bought_amounts[line][item_int] == 1:
                self.add_ach_for_new_dim(line, item_int)

        self.add_action(line, item_int, cost)
        
        self.allowed_purchases[line] = self.purchase_strategy.next_purchases(self, line)

    def sacrifice(self, line: int, sacrifice_boost: float) -> None:
        self.amounts[line][self.max_dims + 1] += self.amounts[line][1]
        self.multipliers[line][8] *= sacrifice_boost
        for tier in range(1, self.max_dims):
            self.amounts[line][tier] = 0

        self.add_action(line, Constants.sacrifice_action_const, sacrifice_boost)
        self.allowed_sacrifices[line] = self.sacrifice_strategy.next_sacrifices(self, line)
    
    def extend_arrays(self) -> None:
        new_actions_lists_shape = (self.num_states_reserved + Constants.numpy_reserve_step, self.actions_item_lists.shape[1])
        
        new_array = np.empty(new_actions_lists_shape, dtype=self.actions_item_lists.dtype)
        new_array[:self.num_states_reserved] = self.actions_item_lists
        self.actions_item_lists = new_array

        new_array = np.empty(new_actions_lists_shape, dtype=self.actions_amount_lists.dtype)
        new_array[:self.num_states_reserved] = self.actions_amount_lists
        self.actions_amount_lists = new_array
        
        new_array = np.empty(new_actions_lists_shape, dtype=self.actions_info_lists.dtype)
        new_array[:self.num_states_reserved] = self.actions_info_lists
        self.actions_info_lists = new_array
        
        new_array = np.empty(new_actions_lists_shape, dtype=self.actions_tick_lists.dtype)
        new_array[:self.num_states_reserved] = self.actions_tick_lists
        self.actions_tick_lists = new_array
        
        new_shape = (self.num_states_reserved + Constants.numpy_reserve_step, self.allowed_purchases.shape[1])
        new_array = np.empty(new_shape, dtype=self.allowed_purchases.dtype)
        new_array[:self.num_states_reserved] = self.allowed_purchases
        self.allowed_purchases = new_array
        
        new_shape = (self.num_states_reserved + Constants.numpy_reserve_step, self.allowed_sacrifices.shape[1])
        new_array = np.empty(new_shape, dtype=self.allowed_sacrifices.dtype)
        new_array[:self.num_states_reserved] = self.allowed_sacrifices
        self.allowed_sacrifices = new_array

        new_shape = (self.num_states_reserved + Constants.numpy_reserve_step, self.amounts.shape[1])
        new_array = np.empty(new_shape, dtype=self.amounts.dtype)
        new_array[:self.num_states_reserved] = self.amounts
        self.amounts = new_array

        new_shape = (self.num_states_reserved + Constants.numpy_reserve_step, self.bought_amounts.shape[1])
        new_array = np.empty(new_shape, dtype=self.bought_amounts.dtype)
        new_array[:self.num_states_reserved] = self.bought_amounts
        self.bought_amounts = new_array

        new_shape = (self.num_states_reserved + Constants.numpy_reserve_step, self.costs.shape[1])
        new_array = np.empty(new_shape, dtype=self.costs.dtype)
        new_array[:self.num_states_reserved] = self.costs
        self.costs = new_array

        new_shape = (self.num_states_reserved + Constants.numpy_reserve_step, self.multipliers.shape[1])
        new_array = np.empty(new_shape, dtype=self.multipliers.dtype)
        new_array[:self.num_states_reserved] = self.multipliers
        self.multipliers = new_array
        
        self.num_states_reserved += Constants.numpy_reserve_step
    
    def add_state_copy(self, orig_line: int) -> int:
        if self.num_states_current == self.num_states_reserved:
            self.extend_arrays()
        new_line = self.num_states_current
        self.actions_item_lists[new_line] = self.actions_item_lists[orig_line]
        self.actions_amount_lists[new_line] = self.actions_amount_lists[orig_line]
        self.actions_info_lists[new_line] = self.actions_info_lists[orig_line]
        self.actions_tick_lists[new_line] = self.actions_tick_lists[orig_line]
        self.allowed_purchases[new_line] = self.allowed_purchases[orig_line]
        self.allowed_sacrifices[new_line] = self.allowed_sacrifices[orig_line]
        self.amounts[new_line] = self.amounts[orig_line]
        self.bought_amounts[new_line] = self.bought_amounts[orig_line]
        self.costs[new_line] = self.costs[orig_line]
        self.multipliers[new_line] = self.multipliers[orig_line]
        
        self.num_states_alltime += 1
        self.num_states_current += 1
        return new_line

    def can_buy(self, line: int) -> bool:
        item_int = self.allowed_purchases[line][0]
        cost = self.costs[line][item_int]
        result = (cost <= self.amounts[line][0])
        return result

    def tick_all(self) -> None:
        start_time = time.perf_counter()
        for tier in range(self.max_dims, 0, -1):
            self.amounts[:self.num_states_current, tier - 1] += self.amounts[:self.num_states_current, tier] * self.multipliers[:self.num_states_current, tier] * self.multipliers[:self.num_states_current, 0] * self.tick_duration
        self.ticks_passed += 1
        end_time = time.perf_counter()
        self.spent_for_tick += end_time - start_time

    def sorted_indices(self, item_int: int) -> np.ndarray:
        return np.argsort(self.amounts[:self.num_states_current, item_int])[::-1].astype(ArraysTypes.sorted_indices)
    
    def sort_states(self, item_int: int) -> None:
        sorted_indices = self.sorted_indices(item_int)
        self.actions_item_lists[:self.num_states_current] = self.actions_item_lists[sorted_indices]
        self.actions_amount_lists[:self.num_states_current] = self.actions_amount_lists[sorted_indices]
        self.actions_info_lists[:self.num_states_current] = self.actions_info_lists[sorted_indices]
        self.actions_tick_lists[:self.num_states_current] = self.actions_tick_lists[sorted_indices]
        self.allowed_purchases[:self.num_states_current] = self.allowed_purchases[sorted_indices]
        self.allowed_sacrifices[:self.num_states_current] = self.allowed_sacrifices[sorted_indices]
        self.amounts[:self.num_states_current] = self.amounts[sorted_indices]
        self.bought_amounts[:self.num_states_current] = self.bought_amounts[sorted_indices]
        self.costs[:self.num_states_current] = self.costs[sorted_indices]
        self.multipliers[:self.num_states_current] = self.multipliers[sorted_indices]
    
    def move_second_state_to_first(self, i: int, j: int) -> None:
        self.actions_item_lists[i] = self.actions_item_lists[j]
        self.actions_amount_lists[i] = self.actions_amount_lists[j]
        self.actions_info_lists[i] = self.actions_info_lists[j]
        self.actions_tick_lists[i] = self.actions_tick_lists[j]
        self.allowed_purchases[i] = self.allowed_purchases[j]
        self.allowed_sacrifices[i] = self.allowed_sacrifices[j]
        self.amounts[i] = self.amounts[j]
        self.bought_amounts[i] = self.bought_amounts[j]
        self.costs[i] = self.costs[j]
        self.multipliers[i] = self.multipliers[j]
    
    def clear_all(self) -> None:
        old_num_states = self.num_states_current
        start_time = time.perf_counter()

        sorted_indices = self.sorted_indices(1)
        
        num_objects = self.num_states_current
        dominated_bools = np.zeros(num_objects, dtype=bool)
        cpp_lib.find_dominated(self.amounts, self.bought_amounts, sorted_indices,
                               num_objects, self.max_dims, dominated_bools)

        i = 0
        j = num_objects - 1
        while True:
            while (i < j) and (not dominated_bools[i]):
                i += 1
            while (i < j) and (dominated_bools[j]):
                j -= 1
            if i >= j:
                if not dominated_bools[i]:
                    self.num_states_current = i + 1
                else:
                    self.num_states_current = i
                break
            self.move_second_state_to_first(i, j)
            dominated_bools[i] = False
            dominated_bools[j] = True
            i += 1
            j -= 1
        
        end_time = time.perf_counter()
        self.spent_for_clear += end_time - start_time
        new_num_states = self.num_states_current
        
        self.deleted_after_refresh += old_num_states - new_num_states
    
    def buy_all(self, can_buy_bools: np.ndarray) -> None:
        old_num_states = self.num_states_current
        lines_to_check = self.num_states_current
        line = 0
        while line < lines_to_check:
            if line < old_num_states:
                can_buy = can_buy_bools[line]
            else:
                can_buy = self.can_buy(line)
            if can_buy:
                allowed_purchases = self.allowed_purchases[line]
                if (allowed_purchases[1] != Constants.no_action_const):
                    new_line = self.add_state_copy(line)
                    self.allowed_purchases[new_line][:-1] = self.allowed_purchases[new_line][1:]
                    self.allowed_purchases[new_line][-1] = Constants.no_action_const
                    lines_to_check += 1
                self.buy(line, allowed_purchases[0])
                if line < old_num_states:
                    can_buy_bools[line] = self.can_buy(line)
            else:
                line += 1
        new_num_states = self.num_states_current
        self.added_after_refresh += new_num_states - old_num_states

    def sacrifice_all(self, sacrifice_boosts: np.ndarray) -> None:
        old_num_states = self.num_states_current
        for line in range(self.num_states_current):
            if sacrifice_boosts[line] > 0:
                sacrifice_boost = sacrifice_boosts[line]
                
                shift = 0
                while (
                    (shift < len(self.allowed_sacrifices[line])) and
                    (self.allowed_sacrifices[line][shift] != Constants.no_action_const) and
                    (sacrifice_boost >= self.allowed_sacrifices[line][shift])):
                    shift += 1
                
                if (shift < len(self.allowed_sacrifices[line])) and (self.allowed_sacrifices[line][shift] != Constants.no_action_const):
                    new_line = self.add_state_copy(line)
                    self.allowed_sacrifices[new_line][:-shift] = self.allowed_sacrifices[new_line][shift:]
                    self.allowed_sacrifices[new_line][-shift:] = Constants.no_action_const
                
                self.sacrifice(line, sacrifice_boost)
        new_num_states = self.num_states_current
        self.added_after_refresh += new_num_states - old_num_states
    
    def get_winner_line(self) -> Union[int, None]:
        winner_last_dim_bought = Helper.winner_last_dim_bought(self.galaxies_bought, self.dimboosts_bought)
        for line in range(self.num_states_current):
            if self.bought_amounts[line][-1] >= winner_last_dim_bought:
                return line
        return None

    def number_of_winners(self) -> int:
        result = 0
        winner_last_dim_bought = Helper.winner_last_dim_bought(self.galaxies_bought, self.dimboosts_bought)
        for line in range(self.num_states_current):
            if self.bought_amounts[line][-1] >= winner_last_dim_bought:
                result += 1
        return result
    
    def overflow_winners(self) -> list:
        start_time = time.perf_counter()
        self.ticks_passed += 1
        results = []
        for line in range(self.num_states_current):
            for tier in range(self.max_dims, 0, -1):
                self.amounts[line][tier - 1] += self.amounts[line][tier] * self.multipliers[line][tier] * self.multipliers[line][0] * self.tick_duration
        self.sort_states(1)
        for line in range(self.num_states_current):
            if self.amounts[line][0] == np.inf:
                results.append(line)
        end_time = time.perf_counter()
        self.spent_for_tick += end_time - start_time
        return results

    def check_progress_update(self):
        current_max_am = np.max(self.amounts[:self.num_states_current, 0])
        if current_max_am > self.max_am:
            self.max_am = current_max_am
            live_display.update_progress_bar(self.max_am)

    def refresh_status(self) -> None:
        real_time = time.perf_counter()
        
        output_lines = [
            f"for tick:      {Helper.time_float_to_str(self.spent_for_tick - self.spent_for_tick_at_last_refresh)}",
            f"for buy:       {Helper.time_float_to_str(self.spent_for_buy - self.spent_for_buy_at_last_refresh)}",
            f"for sacrifice: {Helper.time_float_to_str(self.spent_for_sacrifice - self.spent_for_sacrifice_at_last_refresh)}",
            f"for clear:     {Helper.time_float_to_str(self.spent_for_clear - self.spent_for_clear_at_last_refresh)}",
            f'game time: {Helper.time_float_to_str(self.tick_duration * self.ticks_passed)}, ticks: {self.ticks_passed}',
            f'speed: {(self.ticks_passed - self.ticks_of_last_refresh) * self.tick_duration / (real_time - self.time_of_last_refresh):.3f} game seconds in one real second',
            f'states: +{self.added_after_refresh} ({self.num_states_current + self.deleted_after_refresh - self.added_after_refresh}->{self.num_states_current + self.deleted_after_refresh}), -{self.deleted_after_refresh} ({self.num_states_current + self.deleted_after_refresh}->{self.num_states_current})'
        ]
        
        live_display.update_runner(lines=output_lines)
        self.check_progress_update()
        
        self.spent_for_tick_at_last_refresh = self.spent_for_tick
        self.spent_for_buy_at_last_refresh = self.spent_for_buy
        self.spent_for_sacrifice_at_last_refresh = self.spent_for_sacrifice
        self.spent_for_clear_at_last_refresh = self.spent_for_clear
        self.added_after_refresh = 0
        self.deleted_after_refresh = 0
        self.time_of_last_refresh = real_time
        self.ticks_of_last_refresh = self.ticks_passed

    def cycle(self) -> None:
        self.used_memory_mb = max(psutil.Process(os.getpid()).memory_info().rss / 1024 ** 2, self.used_memory_mb)
        
        try:
            with np.errstate(over='raise'):
                self.tick_all()
        except FloatingPointError as e:
            raise ValueError from e
        state_num_before_buy_and_sacrifice = self.num_states_current
        start_time = time.perf_counter()
        can_buy_bools = np.zeros(self.num_states_current, dtype=bool)
        if cpp_lib.can_buy_all(self.amounts, self.costs, self.allowed_purchases,
                               self.num_states_current, self.max_dims, can_buy_bools):
            self.buy_all(can_buy_bools)
        end_time = time.perf_counter()
        self.spent_for_buy += end_time - start_time

        if (self.dimboosts_bought >= 5) and self.sacrifice_strategy.is_real_sacrifice_strategy:
            start_time = time.perf_counter()
            sacrifice_boosts = np.zeros(self.num_states_current, dtype=ArraysTypes.sacrifice_boosts)
            if cpp_lib.can_sacrifice_all(self.amounts, self.allowed_sacrifices,
                                         self.num_states_current, self.max_dims,
                                         self.sacrifices_length, sacrifice_boosts):
                self.sacrifice_all(sacrifice_boosts)
            end_time = time.perf_counter()
            self.spent_for_sacrifice += end_time - start_time
            
        if self.num_states_current > state_num_before_buy_and_sacrifice:
            if (self.addition_cycles_without_clear >= Constants.addition_cycles_without_clear_limit) or (
                    self.num_states_current > self.states_num_after_clear * Constants.state_growth_without_clear_limit):
                self.clear_all()
                self.states_num_after_clear = self.num_states_current
                self.addition_cycles_without_clear = 0
                cleared = True
            else:
                self.addition_cycles_without_clear += 1
                cleared = False
            
            if cleared:
                self.refresh_status()
    
    def generate_winner_dict(self, winner_line: int, number_of_winners: int, elapsed_seconds: float) -> dict:
        game_info = {
            "platform": self.platform,
            "galaxies_bought": self.galaxies_bought,
            "dimboosts_bought": self.dimboosts_bought,
            "has_sacrifice": self.sacrifice_strategy.is_real_sacrifice_strategy,
            "game_time": Helper.time_float_to_str(self.tick_duration * self.ticks_passed),
            "ticks_passed": self.ticks_passed,
            "tick_duration": self.tick_duration
        }
        spent_other = elapsed_seconds
        spent_other -= self.spent_for_tick + self.spent_for_buy
        spent_other -= self.spent_for_sacrifice + self.spent_for_clear
        strategy_search_info = {
            "purchase_strategy": type(self.purchase_strategy).__name__,
            "sacrifice_strategy": type(self.sacrifice_strategy).__name__,
            "sacrifice_step": getattr(self.sacrifice_strategy, 'sacrifice_step', 0),
            "strategy_search_time": Helper.time_float_to_str(elapsed_seconds),
            "CPU": Helper.cpu_info(),
            "used_memory_mb": round(self.used_memory_mb, 3),
            "states_analyzed": self.num_states_alltime,
            "number_of_winners": number_of_winners,
            "time_breakdown": {
                "tick": Helper.time_str_percent(self.spent_for_tick, elapsed_seconds),
                "buy": Helper.time_str_percent(self.spent_for_buy, elapsed_seconds),
                "sacrifice": Helper.time_str_percent(self.spent_for_sacrifice, elapsed_seconds),
                "clear": Helper.time_str_percent(self.spent_for_clear, elapsed_seconds),
                "other": Helper.time_str_percent(spent_other, elapsed_seconds)
            }
        }
        actions_num = self.actions_item_lists[winner_line][0]
        actions_readable_list = Helper.get_actions_readable_list(
            self.actions_item_lists[winner_line][1 : actions_num + 1],
            self.actions_amount_lists[winner_line][1 : actions_num + 1],
            self.actions_info_lists[winner_line][1 : actions_num + 1],
            self.actions_tick_lists[winner_line][1 : actions_num + 1],
            self.tick_duration
        )
        return {
            'game_info': game_info,
            'actions_readable_list': actions_readable_list,
            'strategy_search_info': strategy_search_info
            }
    
    def run(self) -> dict:
        start_time = time.perf_counter()
        self.time_of_last_refresh = start_time
        
        while True:
            try:
                self.cycle()
                winner_line = self.get_winner_line()
                if winner_line is not None:
                    number_of_winners = self.number_of_winners()
                    self.sort_states(1)
                    winner_line = self.get_winner_line()
            except ValueError:
                winners = self.overflow_winners()
                number_of_winners = len(winners)
                winner_line = winners[0]
            if winner_line is not None:
                end_time = time.perf_counter()
                elapsed_seconds = end_time - start_time
                break
        
        self.refresh_status()
        live_display.complete_progress_bar()
        return self.generate_winner_dict(winner_line, number_of_winners, elapsed_seconds)
    
    def run_and_save(self, filename: str='') -> None:
        winner_dict = self.run()
        Helper.save_winner_dict(winner_dict, filename=filename)
