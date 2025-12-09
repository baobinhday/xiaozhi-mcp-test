/**
 * MCP Tools Tester - Main Application Entry Point
 * This file initializes all modules and sets up the application
 */

// ============================================
// Application Initialization
// ============================================
document.addEventListener('DOMContentLoaded', () => {
  initConnectionHandler();
  initTabHandler();
  initChatHandler();
  showNoToolsMessage();
  log('info', 'Application initialized');
});

// ============================================
// Keyboard Shortcuts
// ============================================
document.addEventListener('keydown', (e) => {
  // Enter to submit in input fields
  if (e.key === 'Enter' && e.target.classList.contains('input') && !e.target.classList.contains('input-textarea')) {
    const form = e.target.closest('.tool-form');
    if (form) {
      const btn = form.querySelector('.btn-execute');
      if (btn) btn.click();
    }
  }
});
