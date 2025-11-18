from typing import Union, TYPE_CHECKING
import numpy as np

from utils import Constants, Helper

if TYPE_CHECKING:
    from ad_dimboost_optimizer import Runner


class PurchaseStrategy:
    """
    Base class for all purchase strategies.
    """
    def __init__(self) -> None:
        self.is_fixed_purchase_strategy = False
    
    def get_description_lines(self) -> list:
        raw_description = self.__class__.__doc__ or ""
        description_lines = [line.strip() for line in raw_description.splitlines()]
        if description_lines and (not description_lines[0]):
            del description_lines[0]
        if description_lines and (not description_lines[-1]):
            del description_lines[-1]
        if not description_lines:
            description_lines = [self.__class__.__name__]
        return description_lines
    
    def get_short_name(self):
        description_lines = self.get_description_lines()
        if len(description_lines) >= 3:
            return description_lines[0]
        return self.__class__.__name__
    
    def next_purchases(self, runner: 'Runner', line: int) -> np.ndarray:
        simple_list = self.next_purchases_short_list(runner, line)
        simple_list.extend([Constants.no_action_const] * (1 + runner.max_dims - len(simple_list)))
        return np.array(simple_list, dtype=runner.allowed_purchases.dtype)
    
    def next_purchases_short_list(self, runner: 'Runner', line: int) -> list:
        raise NotImplementedError("PurchaseStrategy must implement next_purchases_short_list")

class FullPurchaseStrategy(PurchaseStrategy):
    """
    Exhaustive search strategy. Returns the complete sorted list of tickspeed and all dimensions.
    """
    def next_purchases_short_list(self, runner: 'Runner', line: int) -> list:
        max_dims = runner.max_dims
        result = [{'item_int': item_int, 'cost': runner.costs[line][item_int]} for item_int in range(max_dims + 1)]
        result.sort(key = lambda x: x['cost'])
        return [x['item_int'] for x in result]

class PartiallyOptimizedPurchaseStrategy(FullPurchaseStrategy):
    """
    Partially optimized strategy. For testing purposes mostly.
    """
    def next_purchases_short_list(self, runner: 'Runner', line: int) -> list:
        for item_int in range(1, runner.max_dims + 1):
            if (runner.amounts[line][item_int] > 100) and (runner.bought_amounts[line][item_int] % 10 != 0):
                return [item_int]
        return super().next_purchases_short_list(runner, line)

class OptimizedPurchaseStrategy(PurchaseStrategy):
    """
    Optimized
    
    Optimized purchase strategy that uses intuitive logical rules to reduce search space and find purchase sequence for any dimboost. Matches exhaustive search on the first three dimboosts (cannot verify beyond that). 
    
    1. If the first dimension is not purchased, buy it.
    2. If any purchase is cheaper than 1/1000 of current antimatter, buy it.
    3. If any dimension has more than 10 total purchases and the current count is not a multiple of 10, buy it (as a result, each dimension can be purchased not in stack of 10 only during the first 10 purchases).
    4. Dimensions and tickspeed are purchased in groups with the same stack cost (e.g., first all purchases with cost for stack 1e50, then 1e51, 1e52, etc.). The exception is the last available dimension for purchase - if it costs X for stack, it can be purchased not only in the X for stack group but also in the 0.1*X for stack group.
    """
    def next_purchases_short_list(self, runner: 'Runner', line: int) -> list:
        item_int = 1
        if runner.bought_amounts[line][item_int] == 0:
            return [item_int]
        max_dims = runner.max_dims
        
        for item_int in range(0, max_dims + 1):
            if runner.costs[line][item_int] * Constants.purchase_strategy_always_buy_multiplier <= runner.amounts[line][0]:
                return [item_int]

        for item_int in range(1, max_dims + 1):
            if (runner.bought_amounts[line][item_int] > 10) and (runner.bought_amounts[line][item_int] % 10 != 0):
                return [item_int]

        last_tier = max(i for i in range(1, max_dims + 1) if runner.bought_amounts[line][i] > 0)
        if (runner.bought_amounts[line][last_tier] >= 10) and (last_tier < max_dims):
            last_tier += 1

        item_int = 0
        all_next_purchases = [{'item_int': item_int,
                               'cost': runner.costs[line][item_int],
                               'cost_stack': runner.costs[line][item_int]}]
        for item_int in range(1, last_tier):
            all_next_purchases.append({'item_int': item_int,
                                       'cost': runner.costs[line][item_int],
                                       'cost_stack': runner.costs[line][item_int] * 10})
        min_cost_stack = min(x['cost_stack'] for x in all_next_purchases)
        all_next_purchases = [x for x in all_next_purchases if x['cost_stack'] <= min_cost_stack * Constants.purchase_strategy_accuracy_multiplier]
        last_cost_stack = runner.costs[line][last_tier] * 10
        
        if last_cost_stack < min_cost_stack * Constants.purchase_strategy_last_tier_low_multiplier: # for low_multiplier=0.2: if last_cost_stack is 0.1 * min_cost_stack
            return [last_tier]
        if last_cost_stack < min_cost_stack * Constants.purchase_strategy_last_tier_high_multiplier: # for high_multiplier=20: if last_cost_stack is min_cost_stack or 10*min_cost_stack
            all_next_purchases.append({'item_int': last_tier,
                                       'cost': runner.costs[line][last_tier],
                                       'cost_stack': runner.costs[line][last_tier]})
        
        all_next_purchases.sort(key = lambda x: x['cost'])
        return [x['item_int'] for x in all_next_purchases]

class PurchaseStrategyWithList(OptimizedPurchaseStrategy):
    """
    Strategy that follows a predefined purchase list before switching to optimization.
    """
    def __init__(self, purchase_list: Union[list, None]=None):
        if purchase_list is None:
            purchase_list = []
        self.purchase_list = purchase_list
    
    def next_purchases_short_list(self, runner: 'Runner', line: int) -> list:
        valid_purchases_num = runner.bought_amounts[line].sum()
        if valid_purchases_num < len(self.purchase_list):
            return [self.purchase_list[valid_purchases_num]]
        return super().next_purchases_short_list(runner, line)

class PurchaseStrategyFromActionList(PurchaseStrategyWithList):
    """
    Strategy that follows a predefined purchase list from a readable action list string.
    """
    def __init__(self, actions_readable_list: str):
        super().__init__(Helper.parse_action_list_for_purchases(actions_readable_list))

class PurchaseStrategyFromFile(PurchaseStrategyFromActionList):
    """
    Strategy that follows a predefined purchase list from a file with results of some previously calculated run.
    """
    def __init__(self, filename: str):
        super().__init__(Helper.parse_file_for_action_list(filename))


class FixedPurchaseStrategy(PurchaseStrategy):
    """
    Base class for strategies with fixed purchase order.
    
    1. If the first dimension is not purchased, buy it.
    2. If any dimension is not a multiple of 10, buy it (as a result, each dimension can only be purchased in stack of 10).
    3. Consider only purchases with minimum stack cost (for dimensions: cost of 10 purchases).
    4. If there is an unpurchased dimension among remaining options, buy it.
    5. If purchasing the highest dimension would complete a dimboost, buy it.
    """
    def __init__(self) -> None:
        self.is_fixed_purchase_strategy = True
    
    @classmethod
    def filter_items_for_fixed_strategies(cls, runner: 'Runner', line: int) -> list:
        item_int = 1
        if runner.bought_amounts[line][item_int] == 0:
            return [item_int]
        max_dims = runner.max_dims

        for item_int in range(1, max_dims + 1):
            if (runner.bought_amounts[line][item_int] % 10 != 0):
                return [item_int]

        last_tier = max(i for i in range(1, max_dims + 1) if runner.bought_amounts[line][i] > 0)
        if (runner.bought_amounts[line][last_tier] >= 10) and (last_tier < max_dims):
            last_tier += 1

        item_int = 0
        all_next_purchases = [{'item_int': item_int,
                               'cost': runner.costs[line][item_int],
                               'cost_stack': runner.costs[line][item_int]}]
        for item_int in range(1, last_tier + 1):
            all_next_purchases.append({'item_int': item_int,
                                       'cost': runner.costs[line][item_int],
                                       'cost_stack': runner.costs[line][item_int] * 10})
        min_cost_stack = min(x['cost_stack'] for x in all_next_purchases)
        all_next_purchases = [x for x in all_next_purchases if x['cost_stack'] <= min_cost_stack * Constants.purchase_strategy_accuracy_multiplier]
        last_considered = all_next_purchases[-1]['item_int']
        if runner.bought_amounts[line][last_considered] == 0:
            return [last_considered]
        
        winner_last_dim_bought = Helper.winner_last_dim_bought(runner.galaxies_bought, runner.dimboosts_bought)
        if (last_considered == max_dims) and (runner.bought_amounts[line][last_considered] + 10 >= winner_last_dim_bought):
            return [last_considered]
        
        return [x['item_int'] for x in all_next_purchases]


class FixedT12345678PurchaseStrategy(FixedPurchaseStrategy):
    """
    T12345678
    
    Strategy that follows fixed purchase priority: tickspeed -> 1 -> 2 -> ... -> 8
    
    1. If the first dimension is not purchased, buy it.
    2. If any dimension is not a multiple of 10, buy it (as a result, each dimension can only be purchased in stack of 10).
    3. Consider only purchases with minimum stack cost (for dimensions: cost of 10 purchases).
    4. If there is an unpurchased dimension among remaining options, buy it.
    5. If purchasing the highest dimension would complete a dimboost, buy it.
    6. Choose (among the remaining) a purchase based on priority: tickspeed -> 1 -> 2 -> ... -> 8
    """
    def next_purchases_short_list(self, runner: 'Runner', line: int) -> list:
        filtered_items = self.filter_items_for_fixed_strategies(runner, line)
        
        return [filtered_items[0]]

class Fixed12T345678PurchaseStrategy(FixedPurchaseStrategy):
    """
    12T345678
    
    Strategy that follows fixed purchase priority: 1 -> 2 -> tickspeed -> 3 -> ... -> 8
    
    1. If the first dimension is not purchased, buy it.
    2. If any dimension is not a multiple of 10, buy it (as a result, each dimension can only be purchased in stack of 10).
    3. Consider only purchases with minimum stack cost (for dimensions: cost of 10 purchases).
    4. If there is an unpurchased dimension among remaining options, buy it.
    5. If purchasing the highest dimension would complete a dimboost, buy it.
    6. Choose (among the remaining) a purchase based on priority: 1 -> 2 -> tickspeed -> 3 -> ... -> 8
    """
    def next_purchases_short_list(self, runner: 'Runner', line: int) -> list:
        filtered_items = self.filter_items_for_fixed_strategies(runner, line)
        
        item_int = 1
        if item_int in filtered_items:
            return [item_int]
        
        item_int = 2
        if item_int in filtered_items:
            return [item_int]
        
        return [filtered_items[0]]

class FixedT87654321PurchaseStrategy(FixedPurchaseStrategy):
    """
    T87654321
    
    Strategy that follows fixed purchase priority: tickspeed -> 8 -> 7 -> ... -> 1
    
    1. If the first dimension is not purchased, buy it.
    2. If any dimension is not a multiple of 10, buy it (as a result, each dimension can only be purchased in stack of 10).
    3. Consider only purchases with minimum stack cost (for dimensions: cost of 10 purchases).
    4. If there is an unpurchased dimension among remaining options, buy it.
    5. If purchasing the highest dimension would complete a dimboost, buy it.
    6. Choose (among the remaining) a purchase based on priority: tickspeed -> 8 -> 7 -> ... -> 1
    """
    def next_purchases_short_list(self, runner: 'Runner', line: int) -> list:
        filtered_items = self.filter_items_for_fixed_strategies(runner, line)
        
        item_int = 0
        if item_int in filtered_items:
            return [item_int]
        
        return [filtered_items[-1]]

class Fixed87654321TPurchaseStrategy(FixedPurchaseStrategy):
    """
    87654321T
    
    Strategy that follows fixed purchase priority: 8 -> 7 -> ... -> 1 -> tickspeed
    
    1. If the first dimension is not purchased, buy it.
    2. If any dimension is not a multiple of 10, buy it (as a result, each dimension can only be purchased in stack of 10).
    3. Consider only purchases with minimum stack cost (for dimensions: cost of 10 purchases).
    4. If there is an unpurchased dimension among remaining options, buy it.
    5. If purchasing the highest dimension would complete a dimboost, buy it.
    6. Choose (among the remaining) a purchase based on priority: 8 -> 7 -> ... -> 1 -> tickspeed
    """
    def next_purchases_short_list(self, runner: 'Runner', line: int) -> list:
        filtered_items = self.filter_items_for_fixed_strategies(runner, line)
        
        return [filtered_items[-1]]

class Fixed12345678TPurchaseStrategy(FixedPurchaseStrategy):
    """
    12345678T
    
    Strategy that follows fixed purchase priority: 1 -> 2 -> ... -> 8 -> tickspeed
    
    1. If the first dimension is not purchased, buy it.
    2. If any dimension is not a multiple of 10, buy it (as a result, each dimension can only be purchased in stack of 10).
    3. Consider only purchases with minimum stack cost (for dimensions: cost of 10 purchases).
    4. If there is an unpurchased dimension among remaining options, buy it.
    5. If purchasing the highest dimension would complete a dimboost, buy it.
    6. Choose (among the remaining) a purchase based on priority: 1 -> 2 -> ... -> 8 -> tickspeed
    """
    def next_purchases_short_list(self, runner: 'Runner', line: int) -> list:
        filtered_items = self.filter_items_for_fixed_strategies(runner, line)
        
        item_int = 0
        if item_int not in filtered_items:
            return [filtered_items[0]]
        if len(filtered_items) > 1:
            return [filtered_items[1]]
        return [item_int]
