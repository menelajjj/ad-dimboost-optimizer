import { 
  isTrackingMode, 
  setTrackingMode, 
  currentTrackedRow, 
  setCurrentTrackedRow, 
  actionRows, 
  setActionRows 
} from './state.js';
import { trackingBtn, trackingInfo, tableContainer } from './dom-elements.js';

export function toggleTrackingMode() {
  setTrackingMode(!isTrackingMode);
  
  if (isTrackingMode) {
    trackingBtn.textContent = 'Stop Tracking';
    trackingBtn.classList.remove('bg-blue-600', 'hover:bg-blue-700');
    trackingBtn.classList.add('bg-purple-600', 'hover:bg-purple-700');
    document.body.classList.add('tracking-mode-active');
    trackingInfo.classList.remove('hidden');
    
    const rows = Array.from(document.querySelectorAll('#actionsBody tr'));
    setActionRows(rows);
    document.getElementById('totalActions').textContent = rows.length;
    
    setCurrentTrackedRow(0);
    highlightCurrentRow();
    
    document.addEventListener('keydown', handleKeyPress);
    tableContainer.addEventListener('click', handleTableClick);
  } else {
    trackingBtn.textContent = 'Start Tracking';
    trackingBtn.classList.remove('bg-purple-600', 'hover:bg-purple-700');
    trackingBtn.classList.add('bg-blue-600', 'hover:bg-blue-700');
    document.body.classList.remove('tracking-mode-active');
    trackingInfo.classList.add('hidden');
    
    actionRows.forEach(row => row.classList.remove('tracking-highlight'));
    
    document.removeEventListener('keydown', handleKeyPress);
    tableContainer.removeEventListener('click', handleTableClick);
  }
}

function handleKeyPress(event) {
  if (event.code === 'Space' || event.key === ' ' || event.keyCode === 32) {
    event.preventDefault();
    advanceTracking();
  } else if (event.key === 'Escape') {
    toggleTrackingMode();
  }
}

function handleTableClick(event) {
  if (!event.target.matches('button, select, input, a')) {
    advanceTracking();
  }
}

function advanceTracking() {
  if (!isTrackingMode || actionRows.length === 0) return;
  
  if (currentTrackedRow < actionRows.length - 1) {
    setCurrentTrackedRow(currentTrackedRow + 1);
    highlightCurrentRow();
  }
}

function highlightCurrentRow() {
  actionRows.forEach(row => row.classList.remove('tracking-highlight'));
  
  if (actionRows[currentTrackedRow]) {
    actionRows[currentTrackedRow].classList.add('tracking-highlight');
    actionRows[currentTrackedRow].scrollIntoView({ 
      behavior: 'smooth', 
      block: 'center' 
    });
  }
  
  document.getElementById('currentActionIndex').textContent = currentTrackedRow + 1;
}