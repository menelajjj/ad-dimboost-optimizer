import { labels } from './constants.js';

export function parseTimeToSeconds(timeStr) {
  if (!timeStr || timeStr === '?') return Infinity;
  
  try {
    const [minutes, secondsWithMs] = timeStr.split(':');
    const [seconds, milliseconds] = secondsWithMs.split('.');
    
    return parseInt(minutes) * 60 + parseInt(seconds) + parseInt(milliseconds) / 1000;
  } catch (e) {
    return Infinity;
  }
}

export function getCurrentFilePath(platform, galaxy, dimboost, sacrifice, strategy) {
  const sacStr = (dimboost >= 5 && sacrifice === 'true') ? '_sac' : '';
  const strategyFolder = strategy.replace(/[<>:"/\\|?*]/g, '_'); // Sanitize strategy name for folder
  return `Saved_Runs/${strategyFolder}/${platform}/galaxy${galaxy}/${platform}_galaxy${galaxy}_dimboost${dimboost}${sacStr}.txt`;
}

export function getStrategySummaryPath(strategy) {
  const strategyFolder = strategy.replace(/[<>:"/\\|?*]/g, '_'); // Sanitize strategy name for folder
  return `Saved_Runs/${strategyFolder}/summary.txt`;
}

export function saveDropdownValues(platformSelect, galaxySelect, dimboostSelect, sacrificeSelect, strategySelect) {
  localStorage.setItem('ad-platform', platformSelect.value);
  localStorage.setItem('ad-galaxy', galaxySelect.value);
  localStorage.setItem('ad-dimboost', dimboostSelect.value);
  localStorage.setItem('ad-sacrifice', sacrificeSelect.value);
  localStorage.setItem('ad-strategy', strategySelect.value);
}