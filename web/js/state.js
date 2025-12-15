/**
 * State Management Module
 * Global state and DOM element references
 */

// ============================================
// Global State
// ============================================
const state = {
  websocket: null,
  isConnected: false,
  mcpConnected: false,
  mcpServers: [],
  requestId: 1,
  pendingRequests: new Map(),
  tools: [],
  selectedToolIndex: 0,
  // Custom endpoint URL (null = use auto-generated)
  customEndpointUrl: null,
  // Chat state
  chatHistory: [],
  isGenerating: false,
  // Chat settings
  chatSettings: {
    baseUrl: '',
    token: '',
    model: '',
    systemPrompt: '',
    maxHistory: 20,
    toolMode: 'selected', // 'selected' or 'custom'
    customTools: [], // array of tool names when toolMode is 'custom'
    availableModels: []
  }
};

// ============================================
// DOM Elements
// ============================================
const elements = {
  connectionToggleBtn: document.getElementById('connection-toggle-btn'),
  copyEndpointBtn: document.getElementById('copy-endpoint-btn'),
  customEndpointBtn: document.getElementById('custom-endpoint-btn'),
  connectionStatus: document.getElementById('connection-status'),
  responsePanel: document.querySelector('.response-panel'),
  responseContent: document.getElementById('response-content'),
  requestContent: document.getElementById('request-content'),
  logContent: document.getElementById('log-content'),
  toolNav: document.querySelector('.tool-nav'),
  toolPanel: document.querySelector('.tool-panel'),
  // Tab elements
  tabBtns: document.querySelectorAll('.tab-btn'),
  tabContents: document.querySelectorAll('.tab-content'),
  // Chat elements
  chatBody: document.getElementById('chat-body'),
  chatInput: document.getElementById('chat-input'),
  chatSendBtn: document.getElementById('chat-send-btn'),
  chatSettingsBtn: document.getElementById('chat-settings-btn'),
  // Settings modal elements (will be populated after DOM loads)
  settingsModal: null,
  settingsForm: null,
  // Custom endpoint modal elements
  customEndpointModal: document.getElementById('custom-endpoint-modal'),
  customEndpointUrl: document.getElementById('custom-endpoint-url'),
  customEndpointModalClose: document.getElementById('custom-endpoint-modal-close'),
  customEndpointCancel: document.getElementById('custom-endpoint-cancel'),
  customEndpointConnect: document.getElementById('custom-endpoint-connect')
};

// ============================================
// LocalStorage Persistence
// ============================================
function loadChatSettings() {
  try {
    const saved = localStorage.getItem('chatSettings');
    if (saved) {
      const parsed = JSON.parse(saved);
      state.chatSettings = { ...state.chatSettings, ...parsed };
    }
  } catch (e) {
    console.warn('Failed to load chat settings:', e);
  }
}

function saveChatSettings() {
  try {
    localStorage.setItem('chatSettings', JSON.stringify(state.chatSettings));
  } catch (e) {
    console.warn('Failed to save chat settings:', e);
  }
}

// Load settings on script load
loadChatSettings();
