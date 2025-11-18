from typing import Union, TYPE_CHECKING
import re
import json
from pathlib import Path
import cpuinfo
import numpy as np

if TYPE_CHECKING:
    from purchase_strategies import PurchaseStrategy


class ArraysTypes:
    actions_item_lists = np.int32
    actions_amount_lists = np.int32
    actions_info_lists = np.float64
    actions_tick_lists = np.int32
    sacrifice_boosts = np.float64
    allowed_purchases = np.int32
    allowed_sacrifices = np.float32
    amounts = np.float64
    bought_amounts = np.int32
    costs = np.float64
    multipliers = np.float64
    sorted_indices = np.int32


class Constants:
    start_antimatter = 10
    tickspeed_base_cost = 1e3
    tickspeed_base_cost_multiplier = 10
    tickspeed_base_multiplier = 1.0
    tickspeed_multiplier_multipliers = {0: 1.1245, 1: 1.1445, 2: 1.1645}

    dims_base_costs = {1: 10.00, 2: 100.00, 3: 1.00e4, 4: 1.00e6, 5: 1.00e9, 6: 1.00e13, 7: 1.00e18, 8: 1.00e24}
    dims_base_cost_multipliers = {1: 1.00e3, 2: 1.00e4, 3: 1.00e5, 4: 1.00e6, 5: 1.00e8, 6: 1.00e10, 7: 1.00e12, 8: 1.00e15}
    dims_base_multipliers = {1: 1, 2: 0.1, 3: 0.1, 4: 0.1, 5: 0.1, 6: 0.1, 7: 0.1, 8: 0.1}
    mobile_dim_multiplier = 2
    buy_ten_multiplier = 2
    
    ach_multiplier = 1.03
    ach_row_multiplier = 1.25
    start_ach_amount = 3
    ach23_multiplier = 1.1
    ach28_multiplier = 1.1
    ach31_multiplier = 1.05
    
    dimboost_multiplier = 2

    tick_duration = {'pc': 0.033, 'mobile': 0.025}

    addition_cycles_without_clear_limit = 300
    state_growth_without_clear_limit = 1.5
    numpy_reserve_step = int(1e5)
    numpy_actions_reserve_step = 30

    no_action_const = -1
    sacrifice_action_const = 9
    
    purchase_strategy_accuracy_multiplier = 1.01
    purchase_strategy_last_tier_low_multiplier = 0.2
    purchase_strategy_last_tier_high_multiplier = 20
    purchase_strategy_always_buy_multiplier = 1000

    sacrifice_infinity = 1e10
    sacrifice_max = 50
    
    platform_list = ['pc', 'mobile']
    galaxies_bought_list = [0, 1, 2]


class Helper:
    @classmethod
    def time_float_to_str(cls, float_secs: float) -> str:
        seconds_int_full = int(float_secs)
        minutes = seconds_int_full // 60
        seconds = seconds_int_full % 60
        milseconds = int((float_secs - seconds_int_full) * 1000)
        return f'{minutes:02}:{seconds:02}.{milseconds:03}'
    
    @classmethod
    def time_str_to_float(cls, time_str: str) -> float:
        minutes_str, seconds_str = time_str.split(':')
        minutes = int(minutes_str)
        seconds = float(seconds_str)
        return minutes * 60 + seconds
    
    @classmethod
    def sum_times_str(cls, first_str: str, second_str: str) -> str:
        first_float = Helper.time_str_to_float(first_str)
        second_float = Helper.time_str_to_float(second_str)
        return Helper.time_float_to_str(first_float + second_float)
    
    @classmethod
    def time_str_percent(cls, float_secs: float, total_float_secs: float) -> str:
        percent = int(float_secs / total_float_secs * 100)
        return f'{Helper.time_float_to_str(float_secs)} ({percent}%)'
    
    @classmethod
    def cpu_info(cls) -> str:
        if not hasattr(cls, '_cpu_info'):
            cls._cpu_info = cpuinfo.get_cpu_info()['brand_raw']
        return cls._cpu_info
    
    @classmethod
    def max_dims(cls, dimboosts_bought: int) -> int:
        if dimboosts_bought == 0:
            return 4
        if dimboosts_bought == 1:
            return 5
        if dimboosts_bought == 2:
            return 6
        if dimboosts_bought == 3:
            return 7
        return 8
    
    @classmethod
    def start_achs_for_dims(cls, galaxies_bought: int, dimboosts_bought: int) -> int:
        if galaxies_bought == 0:
            if dimboosts_bought == 0:
                return 0
            if dimboosts_bought >= 5:
                return 8
            return 3 + dimboosts_bought
        return 8

    @classmethod
    def start_ach_amount(cls, galaxies_bought: int, dimboosts_bought: int) -> int:
        ach_amount = 0
        ach_amount += Constants.start_ach_amount # r22, r35, r76
        ach_amount += Helper.start_achs_for_dims(galaxies_bought, dimboosts_bought) # r11-r18
        if galaxies_bought == 0:
            if dimboosts_bought >= 6:
                ach_amount += 1 # r42
            if dimboosts_bought >= 7:
                ach_amount += 2 # r24, r44
            if dimboosts_bought >= 8:
                ach_amount += 1 # r46
        elif galaxies_bought == 1:
            ach_amount += 4 # from galaxy0: r24, r42, r44, r46
            ach_amount += 1 # r26
            if dimboosts_bought >= 10:
                ach_amount += 2 # r23, r25
            if dimboosts_bought >= 12:
                ach_amount += 1 # r28
        elif galaxies_bought == 2:
            ach_amount += 8 # from galaxy0: r24, r42, r44, r46
                            # from galaxy1: r23, r25, r26, r28
            ach_amount += 1 # r27
            if dimboosts_bought >= 15:
                ach_amount += 1 # r31
        return ach_amount
    
    @classmethod
    def winner_last_dim_bought(cls, galaxies_bought: int, dimboosts_bought: int) -> int:
        if cls.last_dimboost(galaxies_bought) == dimboosts_bought: # if this is the last dimboost for this galaxy, then ignore dimboost requirement and use galaxy requirement instead
            if galaxies_bought == 0:
                return 80
            if galaxies_bought == 1:
                return 140 # e.g. skip dimboost 12 in galaxy1
            if galaxies_bought == 2:
                return 200 # e.g. skip dimboosts 12+ in galaxy2
        if dimboosts_bought <= 4:
            return 20
        return 20 + (dimboosts_bought - 4) * 15
    
    @classmethod
    def winner_antimatter(cls, galaxies_bought: int, dimboosts_bought: int) -> float:
        max_dims = cls.max_dims(dimboosts_bought)
        winner_last_dim_bought = cls.winner_last_dim_bought(galaxies_bought, dimboosts_bought)
        if (max_dims == 8) and (winner_last_dim_bought >= 200):
            return 1.78e308
        
        if winner_last_dim_bought % 10 == 0:
            number_of_cost_raises = winner_last_dim_bought // 10 - 1
            last_bought_amount = 10
        else:
            number_of_cost_raises = winner_last_dim_bought // 10
            last_bought_amount = winner_last_dim_bought % 10
        
        result = Constants.dims_base_costs[max_dims]
        cost_multiplier = Constants.dims_base_cost_multipliers[max_dims]
        result *= pow(cost_multiplier, number_of_cost_raises)
        result *= last_bought_amount
        return result
    
    @classmethod
    def last_dimboost(cls, galaxies_bought: int) -> int:
        if galaxies_bought == 0:
            return 8
        if galaxies_bought == 1:
            return 12 # 11 or 12
        if galaxies_bought == 2:
            return 16 # 11-16
        return 8
    
    @classmethod
    def get_strategy_path(cls, purchase_strategy: 'PurchaseStrategy') -> Path:
        purchase_strategy_short_name = purchase_strategy.get_short_name()
        return Path('..') / 'docs' / 'Saved_runs' / purchase_strategy_short_name
    
    @classmethod
    def get_filename(cls, purchase_strategy: 'PurchaseStrategy', platform: str, galaxies_bought: int, dimboosts_bought: int, has_sacrifice: bool) -> str:
        if (dimboosts_bought >= 5) and has_sacrifice:
            sac_str = '_sac'
        else:
            sac_str = ''
        
        strategy_path = cls.get_strategy_path(purchase_strategy)
        directory = strategy_path / platform / f'galaxy{galaxies_bought}'
        filename = f'{platform}_galaxy{galaxies_bought}_dimboost{dimboosts_bought}{sac_str}.txt'
        return str(directory / filename)
    
    @classmethod
    def get_actions_readable_list(cls, actions_item_list: np.ndarray, actions_amount_list: np.ndarray,
                                  actions_info_list: np.ndarray, actions_tick_list: np.ndarray, tick_duration: float) -> str:
        lines = []
        for i, (item_int, amount, cost, tick) in enumerate(zip(actions_item_list, actions_amount_list, actions_info_list, actions_tick_list)):
            if item_int == Constants.sacrifice_action_const:
                lines.append(
                        f"sacrifice: {cost}, "
                        f"time: {Helper.time_float_to_str(tick * tick_duration)}"
                )
            else:
                total_amount = sum(actions_amount_list[j] for j in range(i+1) if actions_item_list[j] == item_int)
                if item_int == 0:
                    item_str = '  tickspeed'
                    cost_for_stack = cost
                else:
                    item_str = f"dimension {item_int}"
                    cost_for_stack = cost * 10
                lines.append(
                    f"item: {item_str}, amount: {amount:2d}, "
                    f"total: {total_amount:3d}, cost_one: {cost:.0e}, "
                    f"cost_amount: {amount * cost:.0e}, cost_stack: {cost_for_stack:.0e}, "
                    f"time: {Helper.time_float_to_str(tick * tick_duration)}"
                )
        return "\n".join(lines)
    
    @classmethod
    def generate_winner_str(cls, winner_dict: dict, iterative_optimization_info: Union[dict, None]=None) -> str:
        sections = [
            f"=== GAME INFO ===\n{json.dumps(winner_dict['game_info'], indent=4)}\n=== END GAME INFO ===",
            f"=== ACTIONS ===\n{winner_dict['actions_readable_list']}\n=== END ACTIONS ==="
            ]
        if iterative_optimization_info is None:
            sections.append(f"=== STRATEGY SEARCH INFO ===\n{json.dumps(winner_dict['strategy_search_info'], indent=4)}\n=== END STRATEGY SEARCH INFO ===")
        else:
            sections.append(f"=== ITERATIVE OPTIMIZATION INFO ===\n{json.dumps(iterative_optimization_info, indent=4)}\n=== END ITERATIVE OPTIMIZATION INFO ===")
        return "\n\n".join(sections) + "\n"

    @classmethod
    def save_winner_dict(cls, winner_dict: dict, iterative_optimization_info: Union[dict, None]=None, filename: str=''):
        winner_str = cls.generate_winner_str(winner_dict, iterative_optimization_info)
        if filename:
            file_path = Path(filename)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(winner_str, encoding='utf-8')
        else:
            print(winner_str)

    @classmethod
    def parse_file_for_action_list(cls, filename: str) -> str:
        with open(filename, 'r') as file:
            content = file.read()
        
        actions_match = re.search(
            r'=== ACTIONS ===\n(.*?)\n=== END ACTIONS ===', 
            content, 
            re.DOTALL
        )
        
        if actions_match:
            return actions_match.group(1).strip()
        return ""

    @classmethod
    def parse_action_list_for_purchases(cls, actions_readable_list: str) -> list:
        bought_items = []
        for line in actions_readable_list.split('\n'):
            line = line.strip()
            if line.startswith('item:'):
                if 'tickspeed' in line:
                    item_int = 0
                else:
                    dim_match = re.search(r'dimension\s+(\d+)', line)
                    if dim_match:
                        item_int = int(dim_match.group(1))
                    else:
                        continue
                    
                amount_match = re.search(r'amount:\s*(\d+)', line)
                if amount_match:
                    amount = int(amount_match.group(1))
                    bought_items.extend([item_int] * amount)
        return bought_items

    @classmethod
    def parse_action_list_for_sacrifices(cls, actions_readable_list: str) -> list:
        sacrifices = []
        for line in actions_readable_list.split('\n'):
            line = line.strip()
            sacrifice_match = re.search(r'sacrifice:\s*([\d.]+)', line)
            if sacrifice_match:
                boost_str = sacrifice_match.group(1)
                boost_value = float(boost_str)
                sacrifices.append(boost_value)
        return sacrifices
