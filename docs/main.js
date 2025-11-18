import { platforms, galaxies, strategies } from './constants.js';
import * as dom from './dom-elements.js';
import { initializeColumnToggles, updateColumnVisibility } from './column-management.js';
import { saveDropdownValues, getCurrentFilePath, getStrategySummaryPath, parseTimeToSeconds } from './utils.js';
import { toggleTrackingMode } from './tracking-mode.js';
import { renderTimeBreakdown, renderInfoCards, renderIteration } from './rendering.js';

let currentIterationsData = [];
let allStrategySummaries = {};
let isStrategyInfoVisible = false;

async function loadAllStrategySummaries() {
  const promises = Object.keys(strategies).map(async (strategy) => {
    const filePath = getStrategySummaryPath(strategy);
    
    try {
      const response = await fetch(filePath);
      if (!response.ok) throw new Error('Strategy summary not found');
      const text = await response.text();
      allStrategySummaries[strategy] = JSON.parse(text);
    } catch (err) {
      allStrategySummaries[strategy] = null;
    }
  });
  
  await Promise.all(promises);
}

async function loadDropdownValues() {
  const savedPlatform = localStorage.getItem('ad-platform');
  const savedGalaxy = localStorage.getItem('ad-galaxy');
  const savedDimboost = localStorage.getItem('ad-dimboost');
  const savedSacrifice = localStorage.getItem('ad-sacrifice');
  const savedStrategy = localStorage.getItem('ad-strategy');

  await loadAllStrategySummaries();
  
  const strategiesWithTimes = Object.keys(strategies).map(strategy => {
    const summary = allStrategySummaries[strategy];
    let pcTime = '?';
    let mobileTime = '?';
    
    if (summary && summary.times && summary.times.pc && summary.times.pc.total) {
      pcTime = summary.times.pc.total;
    }
    if (summary && summary.times && summary.times.mobile && summary.times.mobile.total) {
      mobileTime = summary.times.mobile.total;
    }
    
    return {
      key: strategy,
      display: `${strategy} (${pcTime} / ${mobileTime})`,
      pcTime: pcTime
    };
  });
  
  strategiesWithTimes.sort((a, b) => {
    const timeA = a.pcTime === '?' ? Infinity : parseTimeToSeconds(a.pcTime);
    const timeB = b.pcTime === '?' ? Infinity : parseTimeToSeconds(b.pcTime);
    return timeA - timeB;
  });
  
  dom.strategySelect.innerHTML = '';
  
  strategiesWithTimes.forEach(item => {
    const o = document.createElement("option");
    o.value = item.key;
    o.textContent = item.display;
    dom.strategySelect.appendChild(o);
  });
  
  const validStrategies = Object.keys(strategies);
  dom.strategySelect.value = savedStrategy && validStrategies.includes(savedStrategy) 
    ? savedStrategy 
    : "Optimized";
  
  platforms.forEach(p => {
    const o = document.createElement("option");
    o.value = p;
    o.textContent = p.toUpperCase();
    dom.platformSelect.appendChild(o);
  });
  
  galaxies.forEach(g => {
    const o = document.createElement("option");
    o.value = g;
    o.textContent = g;
    dom.galaxySelect.appendChild(o);
  });
  
  dom.platformSelect.value = savedPlatform || "pc";
  dom.galaxySelect.value = savedGalaxy || "0";
  dom.sacrificeSelect.value = savedSacrifice || "true";
  
  refreshDimboosts(savedDimboost);
  saveDropdownValues(dom.platformSelect, dom.galaxySelect, dom.dimboostSelect, dom.sacrificeSelect, dom.strategySelect);
  updateStrategyInfo();
}

function refreshDimboosts(savedDimboostValue = null) {
  dom.dimboostSelect.innerHTML = "";
  const galaxy = parseInt(dom.galaxySelect.value, 10);
  const maxByGalaxy = {0: 8, 1: 12, 2: 16};
  const maxDimboost = maxByGalaxy[galaxy] ?? 8;
  
  for (let i = 0; i <= maxDimboost; i++) {
    const opt = document.createElement("option");
    opt.value = i;
    opt.textContent = i;
    dom.dimboostSelect.appendChild(opt);
  }
  
  let dimboostToSet;
  
  if (savedDimboostValue !== null && parseInt(savedDimboostValue) <= maxDimboost) {
    dimboostToSet = savedDimboostValue;
  } else {
    const currentSaved = localStorage.getItem('ad-dimboost');
    if (!currentSaved) {
      dimboostToSet = 0;
    } else {
      if (parseInt(currentSaved) <= maxDimboost) {
        dimboostToSet = currentSaved;
      } else {
        dimboostToSet = maxDimboost;
      }
    }
  }
  
  dom.dimboostSelect.value = dimboostToSet;
  
  saveDropdownValues(dom.platformSelect, dom.galaxySelect, dom.dimboostSelect, dom.sacrificeSelect, dom.strategySelect);
  loadFile();
}

function updateStrategyInfo() {
  const currentStrategy = dom.strategySelect.value;
  const summary = allStrategySummaries[currentStrategy];
  
  if (!summary) {
    dom.strategyDescription.innerHTML = '<p class="text-gray-400">No description available</p>';
    dom.strategyTimesPC.innerHTML = '<p class="text-gray-400">No data</p>';
    dom.strategyTimesMobile.innerHTML = '<p class="text-gray-400">No data</p>';
    return;
  }

  if (summary.description) {
    dom.strategyDescription.innerHTML = summary.description
      .map(line => line ? `<p class="mb-1">${line}</p>` : '<br>')
      .join('');
  } else {
    dom.strategyDescription.innerHTML = '<p class="text-gray-400">No description available</p>';
  }

  if (summary.times && summary.times.pc) {
    const pcData = summary.times.pc;
    let pcHTML = '';
    
    Object.entries(pcData).forEach(([galaxy, time]) => {
      if (galaxy !== 'total') {
        pcHTML += `<div class="flex justify-between">
          <span>Galaxy ${galaxy}:</span>
          <span class="font-mono">${time}</span>
        </div>`;
      }
    });
    
    if (pcData.total) {
      pcHTML += `
        <div class="flex justify-between font-semibold border-t border-gray-600 mt-2 pt-2">
          <span>Total:</span>
          <span class="font-mono">${pcData.total}</span>
        </div>
      `;
    }
    
    dom.strategyTimesPC.innerHTML = pcHTML || '<p class="text-gray-400">No data</p>';
  } else {
    dom.strategyTimesPC.innerHTML = '<p class="text-gray-400">No data</p>';
  }

  if (summary.times && summary.times.mobile) {
    const mobileData = summary.times.mobile;
    let mobileHTML = '';
    
    Object.entries(mobileData).forEach(([galaxy, time]) => {
      if (galaxy !== 'total') {
        mobileHTML += `<div class="flex justify-between">
          <span>Galaxy ${galaxy}:</span>
          <span class="font-mono">${time}</span>
        </div>`;
      }
    });
    
    if (mobileData.total) {
      mobileHTML += `
        <div class="flex justify-between font-semibold border-t border-gray-600 mt-2 pt-2">
          <span>Total:</span>
          <span class="font-mono">${mobileData.total}</span>
        </div>
      `;
    }
    
    dom.strategyTimesMobile.innerHTML = mobileHTML || '<p class="text-gray-400">No data</p>';
  } else {
    dom.strategyTimesMobile.innerHTML = '<p class="text-gray-400">No data</p>';
  }
}

function toggleStrategyInfo() {
  isStrategyInfoVisible = !isStrategyInfoVisible;
  
  if (isStrategyInfoVisible) {
    dom.strategyInfoContainer.classList.remove('hidden');
    dom.toggleStrategyInfoBtn.textContent = 'Hide Info';
    dom.toggleStrategyInfoBtn.classList.remove('bg-blue-600', 'hover:bg-blue-700');
    dom.toggleStrategyInfoBtn.classList.add('bg-purple-600', 'hover:bg-purple-700');
  } else {
    dom.strategyInfoContainer.classList.add('hidden');
    dom.toggleStrategyInfoBtn.textContent = 'Show Info';
    dom.toggleStrategyInfoBtn.classList.remove('bg-purple-600', 'hover:bg-purple-700');
    dom.toggleStrategyInfoBtn.classList.add('bg-blue-600', 'hover:bg-blue-700');
  }
}

async function loadFile() {
  const filePath = getCurrentFilePath(
    dom.platformSelect.value, 
    dom.galaxySelect.value, 
    dom.dimboostSelect.value, 
    dom.sacrificeSelect.value,
    dom.strategySelect.value
  );

  try {
    const response = await fetch(filePath);
    if (!response.ok) throw new Error('File not found');
    const text = await response.text();
    parseFile(text);
  } catch (err) {
    resetAllFields();
    if (isTrackingMode) {
      toggleTrackingMode();
    }
  }
}

function resetAllFields() {
  document.getElementById('gameInfo-time').textContent = '-';
  document.getElementById('gameInfo-ticks').textContent = '-';
  document.getElementById('gameInfo-tick-duration').textContent = '-';
  
  dom.actionsBody.innerHTML = ``;
  
  dom.strategySearchContainer.classList.add('hidden');
  dom.timeBreakdownContainer.classList.add('hidden');
  dom.optimizationContainer.classList.add('hidden');
}

function downloadCurrentFile() {
  const filePath = getCurrentFilePath(
    dom.platformSelect.value, 
    dom.galaxySelect.value, 
    dom.dimboostSelect.value, 
    dom.sacrificeSelect.value,
    dom.strategySelect.value
  );
  const fileName = filePath.split('/').pop();
  
  const a = document.createElement('a');
  a.href = filePath;
  a.download = fileName;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
}

function toggleIteration(iterationId) {
  const element = document.getElementById(iterationId);
  const icon = document.getElementById(iterationId + '-icon');
  if (element.classList.contains('hidden')) {
    element.classList.remove('hidden');
    icon.style.transform = 'rotate(180deg)';
    
    const timeBreakdownContainer = document.getElementById(iterationId + '-time-breakdown');
    if (timeBreakdownContainer) {
      const iterationIndex = parseInt(iterationId.split('-')[1]);
      const iteration = currentIterationsData[iterationIndex];
      if (iteration && iteration.strategy_search_info?.time_breakdown) {
        renderTimeBreakdown(iteration.strategy_search_info.time_breakdown, iterationId + '-time-breakdown');
      }
    }
  } else {
    element.classList.add('hidden');
    icon.style.transform = 'rotate(0deg)';
  }
}

function parseFile(text) {
  const gameInfoMatch = text.match(/=== GAME INFO ===([\s\S]*?)=== END GAME INFO ===/);
  const actionsMatch = text.match(/=== ACTIONS ===([\s\S]*?)=== END ACTIONS ===/);
  const strategySearchInfoMatch = text.match(/=== STRATEGY SEARCH INFO ===([\s\S]*?)=== END STRATEGY SEARCH INFO ===/);
  const iterativeOptimizationInfoMatch = text.match(/=== ITERATIVE OPTIMIZATION INFO ===([\s\S]*?)=== END ITERATIVE OPTIMIZATION INFO ===/);

  dom.optimizationContainer.classList.add('hidden');
  dom.iterationsAccordion.innerHTML = '';

  if (gameInfoMatch) {
    try {
      const info = JSON.parse(gameInfoMatch[1]);
      document.getElementById('gameInfo-time').textContent = info.game_time || '-';
      document.getElementById('gameInfo-ticks').textContent = info.ticks_passed ?? '-';
      document.getElementById('gameInfo-tick-duration').textContent = info.tick_duration ?? '-';
    } catch {
      document.getElementById('gameInfo').textContent = gameInfoMatch[1].trim();
    }
  } else {
    document.getElementById('gameInfo-time').textContent = '-';
    document.getElementById('gameInfo-ticks').textContent = '-';
    document.getElementById('gameInfo-tick-duration').textContent = '-';
  }

  const tbody = dom.actionsBody;
  tbody.innerHTML = '';
  let lastCostStack = null;
  if (actionsMatch) {
    const lines = actionsMatch[1].trim().split('\n');
    lines.forEach((line, i) => {
      if (!line) return;
      let bgClass="", extraBorder="";
      if (line.startsWith('sacrifice')) {
        bgClass="bg-amber-100 text-gray-900";
        const m = line.match(/sacrifice:\s*([\d.]+), time:\s*([\d:.]+)/);
        if (m) {
          const boost=m[1]
          const formattedBoost = parseFloat(boost).toFixed(3);
          const timeValue=m[2]
          
          tbody.insertAdjacentHTML('beforeend',
            `<tr class="${bgClass}">
              <td class="border border-gray-300 px-2 py-1 column-index">${i+1}</td>
              <td class="border border-gray-300 px-2 py-1 font-semibold column-action">Sacrifice</td>
              <td class="border border-gray-300 px-2 py-1 column-amount">-</td>
              <td class="border border-gray-300 px-2 py-1 column-total">-</td>
              <td class="border border-gray-300 px-2 py-1 column-cost-one">${formattedBoost}</td>
              <td class="border border-gray-300 px-2 py-1 column-cost-amount">${formattedBoost}</td>
              <td class="border border-gray-300 px-2 py-1 column-cost-stack">${formattedBoost}</td>
              <td class="border border-gray-300 px-2 py-1 column-time">${timeValue}</td>
            </tr>`);
          }
      } else {
        const m = line.match(/item:\s*(.+?), amount:\s*(\d+), total:\s*(\d+), cost_one:\s*([\de\+\-]+), cost_amount:\s*([\de\+\-]+), cost_stack:\s*([\de\+\-]+), time:\s*([\d:.]+)/);
        if (m) {
          const action=m[1].trim();
          const action_cap=action[0].toUpperCase() + action.slice(1);
          const amount=m[2], total=m[3];
          const costOne=m[4], costAmount=m[5], costStack=m[6];
          const timeValue = m[7];

          if (action.includes("tickspeed")) {
            bgClass="bg-sky-100 text-gray-900";
          } else {
            bgClass="bg-purple-100 text-gray-900";
          }

          if (lastCostStack!==null && lastCostStack!==costStack) {
            extraBorder="border-t-4 border-gray-500";
          }
          lastCostStack=costStack;

          tbody.insertAdjacentHTML('beforeend',
            `<tr class="${bgClass} ${extraBorder}">
              <td class="border border-gray-300 px-2 py-1 column-index">${i+1}</td>
              <td class="border border-gray-300 px-2 py-1 column-action">${action_cap}</td>
              <td class="border border-gray-300 px-2 py-1 column-amount">${amount}</td>
              <td class="border border-gray-300 px-2 py-1 column-total">${total}</td>
              <td class="border border-gray-300 px-2 py-1 column-cost-one">${costOne}</td>
              <td class="border border-gray-300 px-2 py-1 column-cost-amount">${costAmount}</td>
              <td class="border border-gray-300 px-2 py-1 column-cost-stack">${costStack}</td>
              <td class="border border-gray-300 px-2 py-1 column-time">${timeValue}</td>
            </tr>`);
        }
      }
    });
  } else {
    tbody.innerHTML = ``;
  }

  if (strategySearchInfoMatch) {
    try {
      const strategySearchInfo = JSON.parse(strategySearchInfoMatch[1]);
      renderInfoCards("strategySearchInfo", {
        purchase_strategy: strategySearchInfo.purchase_strategy,
        sacrifice_strategy: strategySearchInfo.sacrifice_strategy,
        sacrifice_step: strategySearchInfo.sacrifice_step,
        strategy_search_time: strategySearchInfo.strategy_search_time,
        CPU: strategySearchInfo.CPU,
        used_memory_mb: strategySearchInfo.used_memory_mb,
        states_analyzed: strategySearchInfo.states_analyzed,
        number_of_winners: strategySearchInfo.number_of_winners
      });

      if (strategySearchInfo.time_breakdown) {
        renderTimeBreakdown(strategySearchInfo.time_breakdown, 'timeBreakdown');
        dom.timeBreakdownContainer.classList.remove('hidden');
      } else {
        dom.timeBreakdownContainer.classList.add('hidden');
      }
      
      dom.strategySearchContainer.classList.remove('hidden');
    } catch {
      document.getElementById("strategySearchInfo").textContent = strategySearchInfoMatch[1].trim();
      dom.timeBreakdownContainer.classList.add('hidden');
      dom.strategySearchContainer.classList.remove('hidden');
    }
  } else {
    dom.strategySearchContainer.classList.add('hidden');
    dom.timeBreakdownContainer.classList.add('hidden');
  }

  if (iterativeOptimizationInfoMatch) {
    try {
      const iterativeOptimizationInfo = JSON.parse(iterativeOptimizationInfoMatch[1]);
      
      dom.optimizationContainer.classList.remove('hidden');
      
      renderInfoCards("iterativeOptimizationInfo", {
        total_strategy_search_time: iterativeOptimizationInfo.total_strategy_search_time,
        CPU: iterativeOptimizationInfo.CPU,
        max_used_memory_mb: iterativeOptimizationInfo.max_used_memory_mb,
        total_states_analyzed: iterativeOptimizationInfo.total_states_analyzed,
        number_of_iterations: iterativeOptimizationInfo.number_of_iterations
      });

      if (iterativeOptimizationInfo.iterations && iterativeOptimizationInfo.iterations.length > 0) {
        currentIterationsData = iterativeOptimizationInfo.iterations;
        dom.iterationsAccordion.innerHTML = iterativeOptimizationInfo.iterations.map((iteration, index) => 
          renderIteration(iteration, index, iterativeOptimizationInfo.iterations.length)
        ).join('');
      }
    } catch {
      console.error("Error parsing optimization info");
    }
  } else {
    dom.optimizationContainer.classList.add('hidden');
  }
  
  updateColumnVisibility();
}

function initializeEventListeners() {
  dom.openHelpBtn.addEventListener('click', function() {
    dom.helpModal.classList.remove('hidden');
  });

  dom.closeHelpBtn.addEventListener('click', function() {
    dom.helpModal.classList.add('hidden');
  });

  dom.helpModal.addEventListener('click', function(e) {
    if (e.target === this) {
      this.classList.add('hidden');
    }
  });

  dom.toggleStrategyInfoBtn.addEventListener('click', toggleStrategyInfo);

  document.querySelectorAll('.tab-button').forEach(button => {
    button.addEventListener('click', function() {
      document.querySelectorAll('.tab-button').forEach(btn => {
        btn.classList.remove('active', 'text-green-400', 'border-b-2', 'border-green-400');
        btn.classList.add('text-gray-400');
      });
      document.querySelectorAll('.tab-content').forEach(content => content.classList.add('hidden'));
      
      this.classList.add('active', 'text-green-400', 'border-b-2', 'border-green-400');
      this.classList.remove('text-gray-400');
      
      const tabId = this.getAttribute('data-tab');
      document.getElementById(`tab-${tabId}`).classList.remove('hidden');
    });
  });

  dom.strategySelect.addEventListener("change", () => {
    saveDropdownValues(dom.platformSelect, dom.galaxySelect, dom.dimboostSelect, dom.sacrificeSelect, dom.strategySelect);
    updateStrategyInfo();
    loadFile();
  });

  [dom.platformSelect, dom.galaxySelect].forEach(el => {
    el.addEventListener("change", () => {
      saveDropdownValues(dom.platformSelect, dom.galaxySelect, dom.dimboostSelect, dom.sacrificeSelect, dom.strategySelect);
      refreshDimboosts();
    });
  });

  [dom.dimboostSelect, dom.sacrificeSelect].forEach(el => {
    el.addEventListener("change", () => {
      saveDropdownValues(dom.platformSelect, dom.galaxySelect, dom.dimboostSelect, dom.sacrificeSelect, dom.strategySelect);
      loadFile();
    });
  });

  dom.downloadBtn.addEventListener('click', downloadCurrentFile);
  dom.trackingBtn.addEventListener('click', () => toggleTrackingMode());
}

window.toggleIteration = toggleIteration;

function initializeApp() {
  loadDropdownValues();
  initializeColumnToggles(dom.columnToggles, dom.toggleAllColumns);
  initializeEventListeners();
}

document.addEventListener('DOMContentLoaded', initializeApp);