export let isTrackingMode = false;
export let currentTrackedRow = 0;
export let actionRows = [];
export let visibleColumnsCount = 0;

export function setTrackingMode(value) {
  isTrackingMode = value;
}

export function setCurrentTrackedRow(value) {
  currentTrackedRow = value;
}

export function setActionRows(value) {
  actionRows = value;
}

export function setVisibleColumnsCount(value) {
  visibleColumnsCount = value;
}