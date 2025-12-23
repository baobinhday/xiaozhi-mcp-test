/**
 * Tab Management Module
 * Handles tab switching between Tools and Chat views
 */
import { elements } from './state.js';

// ============================================
// Tab Initialization
// ============================================
export function initTabHandler() {
  elements.tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const tabName = btn.dataset.tab;
      switchTab(tabName);
    });
  });
}

// ============================================
// Tab Switching
// ============================================
export function switchTab(tabName) {
  elements.tabBtns.forEach(btn => {
    btn.classList.toggle('active', btn.dataset.tab === tabName);
  });

  elements.tabContents.forEach(content => {
    const contentTabName = content.id.replace('-tab', '');
    const isActive = contentTabName === tabName;

    content.classList.toggle('active', isActive);

    if (isActive) {
      content.classList.remove('hidden');
      content.classList.add('flex');
    } else {
      content.classList.add('hidden');
      content.classList.remove('flex');
    }
  });
}
