from typing import Union, TYPE_CHECKING
import re
import json

from utils import Constants, Helper
from iterator import Iterator
from live import live_display
from purchase_strategies import OptimizedPurchaseStrategy
from purchase_strategies import FixedT12345678PurchaseStrategy, FixedT87654321PurchaseStrategy
from purchase_strategies import Fixed12T345678PurchaseStrategy, Fixed87654321TPurchaseStrategy, Fixed12345678TPurchaseStrategy

if TYPE_CHECKING:
    from purchase_strategies import PurchaseStrategy


def search_and_save_several(purchase_strategy: 'PurchaseStrategy', platform_list: Union[list, None]=None, galaxies_bought_list: Union[list, None]=None, dimboosts_bought_list: Union[list, None]=None):
    if not platform_list:
        platform_list = Constants.platform_list
    if not galaxies_bought_list:
        galaxies_bought_list = Constants.galaxies_bought_list
    for platform in platform_list:
        for galaxies_bought in galaxies_bought_list:
            if not dimboosts_bought_list:
                dimboosts_bought_list_accurate = range(Helper.last_dimboost(galaxies_bought) + 1)
            else:
                dimboosts_bought_list_accurate = [x for x in dimboosts_bought_list if x <= Helper.last_dimboost(galaxies_bought)]
            for dimboosts_bought in dimboosts_bought_list_accurate:
                iterator = Iterator(purchase_strategy, platform, galaxies_bought, dimboosts_bought)
                iterator.search_and_save()

def create_strategy_summary(purchase_strategy: 'PurchaseStrategy') -> None:
    platform_list = Constants.platform_list
    galaxies_bought_list = Constants.galaxies_bought_list
    
    summary = {
        "description": purchase_strategy.get_description_lines(),
        "times": {}
    }
    total_float_times = {}
    
    for platform in platform_list:
        summary["times"][platform] = {}
        total_float_times[platform] = 0.0
        for galaxies_bought in galaxies_bought_list:
            galaxy_time = 0
            dimboosts_bought_list = range(Helper.last_dimboost(galaxies_bought) + 1)
            for dimboosts_bought in dimboosts_bought_list:
                has_sacrifice = True if (dimboosts_bought >= 5) else False
                filename = Helper.get_filename(purchase_strategy, platform, galaxies_bought, dimboosts_bought, has_sacrifice)
                
                with open(filename, 'r', encoding='utf-8') as f:
                    content = f.read()
                game_info_match = re.search(r'=== GAME INFO ===\s*({.*?})\s*=== END GAME INFO ===', content, re.DOTALL)
                game_info = json.loads(game_info_match.group(1))
                time_str = game_info['game_time']
                galaxy_time += Helper.time_str_to_float(time_str)
            
            summary["times"][platform][galaxies_bought] = Helper.time_float_to_str(galaxy_time)
            total_float_times[platform] += galaxy_time
        summary["times"][platform]["total"] = Helper.time_float_to_str(total_float_times[platform])
    
    summary_str = json.dumps(summary, indent=4)
    strategy_path = Helper.get_strategy_path(purchase_strategy)
    summary_path = strategy_path / "summary.txt"
    summary_path.write_text(summary_str, encoding='utf-8')


if __name__ == '__main__':
    live_display.start()
    
    purchase_strategy_list = [
        FixedT12345678PurchaseStrategy(),
        FixedT87654321PurchaseStrategy(),
        Fixed12T345678PurchaseStrategy(),
        Fixed87654321TPurchaseStrategy(),
        Fixed12345678TPurchaseStrategy(),
        OptimizedPurchaseStrategy()
    ]
    for purchase_strategy in purchase_strategy_list:
        search_and_save_several(purchase_strategy=purchase_strategy)
        create_strategy_summary(purchase_strategy)
    
    live_display.stop()
