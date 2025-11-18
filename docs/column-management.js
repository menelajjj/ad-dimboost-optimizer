import { columns } from './constants.js';
import { setVisibleColumnsCount } from './state.js';

export function initializeColumnToggles(columnToggles, toggleAllColumns) {
  columnToggles.innerHTML = '';
  
  columns.forEach(column => {
    const toggleId = `toggle-${column.id}`;
    const isChecked = localStorage.getItem(toggleId) !== 'false';
    
    const toggleElement = document.createElement('label');
    toggleElement.className = 'inline-flex items-center column-toggle cursor-pointer';
    toggleElement.innerHTML = `
      <input type="checkbox" id="${toggleId}" data-column="${column.id}" 
             ${isChecked ? 'checked' : ''} class="form-checkbox h-4 w-4 text-green-500 rounded">
      <span class="ml-1 text-sm text-gray-300">${column.name}</span>
    `;
    
    columnToggles.appendChild(toggleElement);
    
    document.getElementById(toggleId).addEventListener('change', function() {
      localStorage.setItem(toggleId, this.checked);
      updateColumnVisibility();
    });
  });
  
  updateColumnVisibility();
  
  toggleAllColumns.addEventListener('click', function() {
    const checkboxes = document.querySelectorAll('#columnToggles input[type="checkbox"]');
    const allChecked = Array.from(checkboxes).every(cb => cb.checked);
    
    checkboxes.forEach(cb => {
      cb.checked = !allChecked;
      localStorage.setItem(cb.id, !allChecked);
    });
    
    updateColumnVisibility();
  });
}

export function updateColumnVisibility() {
  let visibleCount = 0;
  columns.forEach(column => {
    const toggleId = `toggle-${column.id}`;
    const toggleElement = document.getElementById(toggleId);
    const isVisible = toggleElement && toggleElement.checked;
    
    // Update table headers
    const headerElements = document.querySelectorAll(`.column-${column.id}`);
    headerElements.forEach(el => {
      el.style.display = isVisible ? '' : 'none';
    });
    
    // Update table cells
    const cellSelector = column.id === 'index' ? 'td:first-child' : 
                       column.id === 'action' ? 'td:nth-child(2)' :
                       `td:nth-child(${columns.findIndex(c => c.id === column.id) + 1})`;
    const cellElements = document.querySelectorAll(`#actionsBody tr ${cellSelector}`);
    cellElements.forEach(el => {
      el.style.display = isVisible ? '' : 'none';
    });

    if (isVisible) {
      visibleCount++;
    }
  });
  setVisibleColumnsCount(visibleCount);
}