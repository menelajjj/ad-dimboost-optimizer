from utils import Helper
from runner import Runner
from purchase_strategies import OptimizedPurchaseStrategy, PurchaseStrategyFromFile
from purchase_strategies import FixedT12345678PurchaseStrategy, Fixed12T345678PurchaseStrategy, FixedT87654321PurchaseStrategy
from sacrifice_strategies import NeverSacrificeStrategy, IncrementalSacrificeStrategy
from live import live_display


def test_1():
    platform = 'pc'
    galaxies_bought = 0
    dimboosts_bought = 0
    filename='../test_1.txt'
    runner = Runner(platform=platform,
                    galaxies_bought=galaxies_bought,
                    dimboosts_bought=dimboosts_bought,
                    purchase_strategy=OptimizedPurchaseStrategy(),
                    sacrifice_strategy=NeverSacrificeStrategy()
                    )
    runner.run_and_save(filename=filename)


def test_2():
    platform = 'mobile'
    galaxies_bought = 0
    dimboosts_bought = 5
    sacrifice_step = 0.1
    no_sac_filename = Helper.get_filename(OptimizedPurchaseStrategy(), platform, galaxies_bought, dimboosts_bought,
                                          has_sacrifice=False)
    filename='../test_2.txt'
    runner = Runner(platform=platform,
                    galaxies_bought=galaxies_bought,
                    dimboosts_bought=dimboosts_bought,
                    purchase_strategy=PurchaseStrategyFromFile(no_sac_filename),
                    sacrifice_strategy=IncrementalSacrificeStrategy(sacrifice_step)
                    )
    runner.run_and_save(filename=filename)


def test_3():
    platform = 'pc'
    galaxies_bought = 0
    dimboosts_bought = 8
    filename='../test_3.txt'
    runner = Runner(platform=platform,
                    galaxies_bought=galaxies_bought,
                    dimboosts_bought=dimboosts_bought,
                    purchase_strategy=FixedT12345678PurchaseStrategy(),
                    sacrifice_strategy=NeverSacrificeStrategy()
                    )
    runner.run_and_save(filename=filename)


def test_4():
    platform = 'pc'
    galaxies_bought = 0
    dimboosts_bought = 8
    filename='../test_4.txt'
    runner = Runner(platform=platform,
                    galaxies_bought=galaxies_bought,
                    dimboosts_bought=dimboosts_bought,
                    purchase_strategy=Fixed12T345678PurchaseStrategy(),
                    sacrifice_strategy=NeverSacrificeStrategy()
                    )
    runner.run_and_save(filename=filename)


def test_5():
    platform = 'pc'
    galaxies_bought = 0
    dimboosts_bought = 8
    sacrifice_step = 0.001
    filename='../test_5.txt'
    runner = Runner(platform=platform,
                    galaxies_bought=galaxies_bought,
                    dimboosts_bought=dimboosts_bought,
                    purchase_strategy=FixedT87654321PurchaseStrategy(),
                    sacrifice_strategy=IncrementalSacrificeStrategy(sacrifice_step)
                    )
    runner.run_and_save(filename=filename)


if __name__ == '__main__':
    live_display.start()
    
    test_1()
#    test_2()
#    test_3()
#    test_4()
#    test_5()
    
    live_display.stop()
