import { parseTimeToSeconds } from './utils.js';
import { labels } from './constants.js';

export function renderTimeBreakdown(timeData, containerId) {
  const container = document.getElementById(containerId);
  
  if (!timeData || Object.keys(timeData).length === 0) {
    container.innerHTML = '<div class="text-gray-500 text-center py-2">No time breakdown data available</div>';
    return;
  }

  let totalSeconds = 0;
  const breakdownData = [];
  
  Object.entries(timeData).forEach(([key, value]) => {
    const timePart = value.split(' (')[0].trim();
    const seconds = parseTimeToSeconds(timePart);
    totalSeconds += seconds;
    
    const percentMatch = value.match(/\((\d+)%\)/);
    const percent = percentMatch ? parseInt(percentMatch[1]) : null;
    
    breakdownData.push({
      category: key,
      time: timePart,
      seconds: seconds,
      percent: percent
    });
  });

  if (breakdownData.some(item => item.percent === null)) {
    breakdownData.forEach(item => {
      item.percent = totalSeconds > 0 ? Math.round((item.seconds / totalSeconds) * 100) : 0;
    });
  }

  breakdownData.sort((a, b) => b.seconds - a.seconds);

  container.innerHTML = breakdownData.map(item => `
    <div class="mb-3">
      <div class="flex justify-between text-sm mb-1">
        <span class="text-green-400 font-medium">${item.category}</span>
        <span class="text-gray-300">${item.time} (${item.percent}%)</span>
      </div>
      <div class="w-full bg-gray-700 rounded-full h-3">
        <div 
          class="bg-gradient-to-r from-blue-500 to-purple-500 h-3 rounded-full transition-all duration-500 ease-out" 
          style="width: ${item.percent}%"
        ></div>
      </div>
    </div>
  `).join('');
}

export function renderInfoCards(containerId, data) {
  const container = document.getElementById(containerId);
  container.innerHTML = "";
  Object.entries(data).forEach(([key, val]) => {
    const label = labels[key] ?? key;
    container.insertAdjacentHTML("beforeend", `
      <div class="bg-[#1c1c1c] border border-gray-700 rounded px-3 py-2">
        <div class="text-green-400 font-semibold">${label}</div>
        <div>${val}</div>
      </div>
    `);
  });
}

export function renderIteration(iteration, index, totalIterations) {
  const iterationId = `iteration-${index}`;
  const gameTime = iteration.game_info?.game_time || '00:00.000';
  const isBestIteration = ((totalIterations === 2) ? (index === totalIterations - 1) : (index === totalIterations - 3));
  const bestIterationText = isBestIteration ? ' <span class="text-amber-400 font-bold">(best iteration)</span>' : '';
  
  return `
    <div class="bg-[#1a1a1a] border border-gray-700 rounded-lg overflow-hidden ${isBestIteration ? 'best-iteration' : ''}">
      <button class="w-full flex justify-between items-center p-4 text-left bg-[#222] hover:bg-[#2a2a2a] transition-colors" onclick="toggleIteration('${iterationId}')">
        <span class="font-semibold text-purple-300">Iteration ${index + 1} - ${gameTime}${bestIterationText}</span>
        <svg class="w-5 h-5 text-gray-400 transition-transform" id="${iterationId}-icon" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clip-rule="evenodd" />
        </svg>
      </button>
      <div class="hidden p-4 border-t border-gray-700" id="${iterationId}">
        <h4 class="text-lg font-semibold mb-2 text-purple-300">Game info</h4>
        <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3 mb-4">
          ${iteration.game_info ? `
            <div class="bg-[#1c1c1c] border border-gray-700 rounded px-3 py-2">
              <div class="text-green-400 font-semibold">Game time</div>
              <div>${iteration.game_info.game_time || '-'}</div>
            </div>
            <div class="bg-[#1c1c1c] border border-gray-700 rounded px-3 py-2">
              <div class="text-green-400 font-semibold">Ticks passed</div>
              <div>${iteration.game_info.ticks_passed || '-'}</div>
            </div>
            <div class="bg-[#1c1c1c] border border-gray-700 rounded px-3 py-2">
              <div class="text-green-400 font-semibold">Tick duration</div>
              <div>${iteration.game_info.tick_duration || '-'}</div>
            </div>
          ` : ''}
        </div>
        <h4 class="text-lg font-semibold mb-2 text-purple-300">Strategy Search Info</h4>
        <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3 mb-4">
          ${Object.entries(iteration.strategy_search_info || {}).map(([key, val]) => {
            if (key === 'time_breakdown') return '';
            return `
              <div class="bg-[#1c1c1c] border border-gray-700 rounded px-3 py-2">
                <div class="text-green-400 font-semibold">${labels[key] || key}</div>
                <div>${val}</div>
              </div>
            `;
          }).join('')}
        </div>
        ${iteration.strategy_search_info?.time_breakdown ? `
          <h4 class="text-lg font-semibold mb-2 text-purple-300">Time Breakdown</h4>
          <div class="bg-[#1c1c1c] border border-gray-700 rounded p-4 mb-4" id="${iterationId}-time-breakdown"></div>
        ` : ''}
      </div>
    </div>
  `;
}