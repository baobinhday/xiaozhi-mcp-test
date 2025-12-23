import { state, elements } from './js/state.js';
import { initConnectionHandler } from './js/websocket.js';
import { initTabHandler } from './js/tabs.js';
import { initChatHandler } from './js/chat-api.js';
import { showNoToolsMessage, executeSelectedTool } from './js/tools.js';
import { fetchVoices, setTtsVoice, setTtsProvider } from './js/tts.js';
import { log, clearResponse, clearRequest, clearLogs } from './js/ui-utils.js';

import { closeSettingsModal, fetchModels, saveSettings, toggleCustomToolsPanel } from './js/settings.js';
import { clearChat } from './js/chat-api.js';

/**
 * MCP Tools Tester - Main Application Entry Point
 * This file initializes all modules and sets up the application
 */

// ============================================
// Authentication State
// ============================================
let isAuthenticated = false;

// ============================================
// Expose functions to window (for HTML onclick/onchange)
// ============================================
window.clearResponse = clearResponse;
window.clearRequest = clearRequest;
window.clearChat = clearChat;
window.clearLogs = clearLogs;
window.closeSettingsModal = closeSettingsModal;
window.fetchModels = fetchModels;
window.saveSettings = saveSettings;
window.toggleCustomToolsPanel = toggleCustomToolsPanel;
window.executeSelectedTool = executeSelectedTool;
window.setTtsVoice = setTtsVoice;
window.setTtsProvider = setTtsProvider;

// ============================================
// Authentication Functions
// ============================================
function showLoginView() {
  elements.loginView.classList.remove('hidden');
  elements.loginView.style.display = 'flex';
  elements.dashboardView.classList.add('hidden');
  elements.dashboardView.style.display = 'none';
}

function showDashboardView() {
  elements.loginView.classList.add('hidden');
  elements.loginView.style.display = 'none';
  elements.dashboardView.classList.remove('hidden');
  elements.dashboardView.style.display = 'block';
}

async function checkAuth() {
  try {
    const response = await fetch('/api/auth/check');
    const data = await response.json();
    return data.authenticated;
  } catch (error) {
    console.error('Auth check failed:', error);
    return false;
  }
}

async function login(username, password) {
  try {
    const response = await fetch('/api/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });
    return response.ok;
  } catch (error) {
    console.error('Login failed:', error);
    return false;
  }
}

async function logout() {
  try {
    await fetch('/api/logout', { method: 'POST' });
  } catch (error) {
    console.error('Logout failed:', error);
  }
}

// ============================================
// Application Initialization
// ============================================
window.initApp = function () {
  initConnectionHandler();
  initTabHandler();
  initChatHandler();
  showNoToolsMessage();
  fetchVoices(); // Load TTS voices from both providers
  log('info', 'Application initialized');
};

// ============================================
// Auth Event Listeners
// ============================================
elements.loginForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const username = elements.loginUsername.value;
  const password = elements.loginPassword.value;

  elements.loginError.textContent = '';
  elements.loginError.classList.add('hidden');

  if (await login(username, password)) {
    isAuthenticated = true;
    showDashboardView();
    // Initialize the app after login
    window.initApp();
  } else {
    elements.loginError.textContent = 'Invalid username or password';
    elements.loginError.classList.remove('hidden');
  }
});

elements.logoutBtn.addEventListener('click', async () => {
  await logout();
  isAuthenticated = false;
  showLoginView();
});

// ============================================
// Initialize auth state
// ============================================
async function initAuth() {
  isAuthenticated = await checkAuth();
  if (isAuthenticated) {
    showDashboardView();
    window.initApp();
  } else {
    showLoginView();
  }
}

// Run auth check on page load
initAuth();

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
