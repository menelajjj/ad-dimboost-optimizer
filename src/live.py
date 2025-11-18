import math

from rich.live import Live
from rich.console import Console, Group
from rich.text import Text
from rich.panel import Panel
from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn


class LiveDisplayManager:
    def __init__(self):
        self.live = None
        self._live_running = False
        
        self.console = Console()
        # === flickering fix (partially working) ===
        # taken from https://github.com/Textualize/rich/pull/3038#issuecomment-1786654627
        # try and force VT support, this is HUGELY useful because in cmd.exe and
        # powershell, there is huge flicker and missing bold/underline otherwise
        if self.console.legacy_windows:
            import ctypes

            from rich import console as conlib
            from rich._win32_console import (
                ENABLE_VIRTUAL_TERMINAL_PROCESSING,
                GetConsoleMode,
                GetStdHandle,
            )
            windll = ctypes.LibraryLoader(ctypes.WinDLL)

            handle = GetStdHandle()
            mode = GetConsoleMode(handle)

            mode |= ENABLE_VIRTUAL_TERMINAL_PROCESSING

            SetConsoleMode = windll.kernel32.SetConsoleMode
            SetConsoleMode.argtypes = [
                ctypes.wintypes.HANDLE,
                ctypes.wintypes.DWORD,
            ]
            SetConsoleMode.restype = ctypes.wintypes.BOOL
            SetConsoleMode(handle, mode)

            # re-init by invalidating the console feature check from before
            conlib._windows_console_features = None
            self.console = Console()
        # === flickering fix end ===
        
        
        self.config_data = {}
        self.iteration_data = {}
        self.runner_data = {}
        
        self.progress = Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("*"),
            TextColumn("[progress.completed]e{task.completed}/e{task.total}"),
            TextColumn("*"),
            TimeElapsedColumn(),
            expand=False
        )
        self.progress_task_am_log = None
    
    def start(self):
        self._live_running = True
        self.live = Live(self._generate_display(), refresh_per_second=4)
        self.live.__enter__()
    
    def stop(self):
        if self._live_running and self.live:
            self.live.__exit__(None, None, None)
            self._live_running = False
    
    def update_config(self, platform=None, galaxies_bought=None, dimboosts_bought=None,
                      purchase_strategy_name=None, sacrifice_strategy_name=None):
        if platform is not None:
            self.config_data['platform'] = platform
        if galaxies_bought is not None:
            self.config_data['galaxies_bought'] = galaxies_bought
        if dimboosts_bought is not None:
            self.config_data['dimboosts_bought'] = dimboosts_bought
        if purchase_strategy_name is not None:
            self.config_data['purchase_strategy_name'] = purchase_strategy_name
        if sacrifice_strategy_name is not None:
            self.config_data['sacrifice_strategy_name'] = sacrifice_strategy_name
        
        self._refresh()
    
    def update_iteration(self, current=None, description=None):
        if current is not None:
            self.iteration_data['current'] = current
        else:
            del self.iteration_data['current']
        if description is not None:
            self.iteration_data['description'] = description
        else:
            del self.iteration_data['description']
        
        self._refresh()
    
    def update_runner(self, lines=None):
        if lines is not None:
            self.runner_data['lines'] = lines
        
        self._refresh()
    
    def init_progress_bar(self, current_am: float, total_am: float):
        if current_am == float('inf'):
            current_am = 1.78e308
        current_am_log = int(math.log10(current_am))
        total_am_log = int(math.log10(total_am))
        if self.progress_task_am_log is None:
            self.progress_task_am_log = self.progress.add_task(
                "AM",
                total=total_am_log,
                completed=current_am_log
            )
        else:
            self.progress.reset(self.progress_task_am_log)
            self.progress.update(self.progress_task_am_log, total=total_am_log, completed=current_am_log)
    
    def update_progress_bar(self, current_am: float):
        if current_am == float('inf'):
            current_am = 1.78e308
        current_am_log = int(math.log10(current_am))
        if self.progress_task_am_log is not None:
            self.progress.update(self.progress_task_am_log, completed=current_am_log)
        self._refresh()
    
    def complete_progress_bar(self):
        if self.progress_task_am_log is not None:
            current = self.progress.tasks[self.progress_task_am_log].completed
            total = self.progress.tasks[self.progress_task_am_log].total
            if current < total:
                self.progress.update(self.progress_task_am_log, completed=total)
            self._refresh()
    
    def _generate_display(self):
        config_text = Text(overflow="ellipsis", no_wrap=True)
        config_text.append(f"Platform: {self.config_data.get('platform', 'N/A')}\n")
        config_text.append(f"Galaxies: {self.config_data.get('galaxies_bought', 'N/A')}\n")
        config_text.append(f"Dimboosts: {self.config_data.get('dimboosts_bought', 'N/A')}\n")
        config_text.append(f"Purchase Strategy: {self.config_data.get('purchase_strategy_name', 'N/A')}\n")
        config_text.append(f"Sacrifice Strategy: {self.config_data.get('sacrifice_strategy_name', 'N/A')}")
        config_panel = Panel(config_text, title="Current configuration", border_style="blue", height=7)
        
        iteration_text = Text(overflow="ellipsis", no_wrap=True)
        iteration_text.append(f"Iteration: {self.iteration_data.get('current', 'N/A')}\n")
        iteration_text.append(f"Description: {self.iteration_data.get('description', 'N/A')}")
        iteration_panel = Panel(iteration_text, title="Iteration Info", border_style="green", height=4)
        
        runner_lines = self.runner_data.get('lines', [])
        runner_text = Text("\n".join(runner_lines), overflow="ellipsis", no_wrap=True)
        
        if self.progress_task_am_log is not None:
            runner_content = Group(
                self.progress,
                runner_text
            )
        else:
            runner_content = Group(runner_text)
        runner_panel = Panel(runner_content, title="Runner Progress", border_style="yellow")
        
        return Group(
            config_panel,
            iteration_panel,
            runner_panel
            )
    
    def _refresh(self):
        if self._live_running and self.live:
            self.live.update(self._generate_display())

live_display = LiveDisplayManager()
