export const platforms = ["pc", "mobile"];
export const galaxies = [0, 1, 2];

export const strategies = {
  "Optimized": "Optimized (? / ?)",
  "T12345678": "T12345678 (? / ?)", 
  "T87654321": "T87654321 (? / ?)",
  "12T345678": "12T345678 (? / ?)",
  "12345678T": "12345678T (? / ?)",
  "87654321T": "87654321T (? / ?)"
};

export const columns = [
  { id: 'index', name: '#', defaultVisible: true },
  { id: 'action', name: 'Action', defaultVisible: true },
  { id: 'amount', name: 'Amount', defaultVisible: true },
  { id: 'total', name: 'Total', defaultVisible: true },
  { id: 'cost-one', name: 'Cost One', defaultVisible: true },
  { id: 'cost-amount', name: 'Cost Amount', defaultVisible: true },
  { id: 'cost-stack', name: 'Cost Stack', defaultVisible: true },
  { id: 'time', name: 'Time', defaultVisible: true }
];

export const labels = {
  platform: "Platform",
  galaxies_bought: "Galaxies",
  dimboosts_bought: "Dimboosts",
  has_sacrifice: "Sacrifice",
  game_time: "Game time",
  ticks_passed: "Ticks passed",
  tick_duration: "Tick duration",
  purchase_strategy: "Purchase strategy",
  sacrifice_strategy: "Sacrifice strategy",
  sacrifice_step: "Sacrifice step",
  strategy_search_time: "Strategy search time",
  CPU: "CPU",
  used_memory_mb: "Used memory (MB)",
  max_used_memory_mb: "Max used memory (MB)",
  states_analyzed: "States analyzed",
  number_of_winners: "Number of winners",
  number_of_iterations: "Number of iterations",
  total_strategy_search_time: "Total strategy search time",
  total_states_analyzed: "Total states analyzed"
};