/**
 * Settings Modal Module
 * Chat settings configuration and model selection
 */

// ============================================
// Modal Initialization
// ============================================
function initSettingsModal() {
  elements.settingsModal = document.getElementById('settings-modal');

  // Close on backdrop click
  elements.settingsModal?.addEventListener('click', (e) => {
    if (e.target === elements.settingsModal) {
      closeSettingsModal();
    }
  });

  // Close on Escape key
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && elements.settingsModal && !elements.settingsModal.classList.contains('hidden')) {
      closeSettingsModal();
    }
  });
}

// ============================================
// Modal Open/Close
// ============================================
function openSettingsModal() {
  if (!elements.settingsModal) return;

  // Populate form with current settings
  const baseUrlInput = document.getElementById('settings-base-url');
  const tokenInput = document.getElementById('settings-token');
  const modelSelect = document.getElementById('settings-model');
  const systemPromptInput = document.getElementById('settings-system-prompt');
  const maxHistoryInput = document.getElementById('settings-max-history');

  if (baseUrlInput) baseUrlInput.value = state.chatSettings.baseUrl;
  if (tokenInput) tokenInput.value = state.chatSettings.token;
  if (systemPromptInput) systemPromptInput.value = state.chatSettings.systemPrompt;
  if (maxHistoryInput) maxHistoryInput.value = state.chatSettings.maxHistory || 20;

  // Populate models if available
  if (modelSelect && state.chatSettings.availableModels.length > 0) {
    populateModelSelect(state.chatSettings.availableModels, state.chatSettings.model);
  }

  // Set tool mode radio
  const toolMode = state.chatSettings.toolMode || 'selected';
  document.getElementById('tool-mode-selected').checked = toolMode === 'selected';
  document.getElementById('tool-mode-custom').checked = toolMode === 'custom';

  // Populate and show/hide custom tools panel
  populateCustomToolsList();
  toggleCustomToolsPanel();

  elements.settingsModal.classList.remove('hidden');
  elements.settingsModal.classList.add('flex');

  log('info', 'Settings modal opened');
}

function closeSettingsModal() {
  if (!elements.settingsModal) return;

  elements.settingsModal.classList.add('hidden');
  elements.settingsModal.classList.remove('flex');
}

// ============================================
// Settings Save
// ============================================
function saveSettings() {
  const baseUrlInput = document.getElementById('settings-base-url');
  const tokenInput = document.getElementById('settings-token');
  const modelSelect = document.getElementById('settings-model');
  const systemPromptInput = document.getElementById('settings-system-prompt');
  const maxHistoryInput = document.getElementById('settings-max-history');

  state.chatSettings.baseUrl = baseUrlInput?.value.trim() || '';
  state.chatSettings.token = tokenInput?.value.trim() || '';
  state.chatSettings.model = modelSelect?.value || '';
  state.chatSettings.systemPrompt = systemPromptInput?.value || '';
  state.chatSettings.maxHistory = parseInt(maxHistoryInput?.value) || 20;

  // Save tool mode and custom tools
  state.chatSettings.toolMode = document.getElementById('tool-mode-custom').checked ? 'custom' : 'selected';
  state.chatSettings.customTools = getSelectedCustomTools();

  saveChatSettings();
  closeSettingsModal();

  log('success', 'Settings saved');
}

// ============================================
// Tool Mode
// ============================================
function toggleCustomToolsPanel() {
  const panel = document.getElementById('custom-tools-panel');
  const isCustomMode = document.getElementById('tool-mode-custom').checked;

  if (panel) {
    if (isCustomMode) {
      panel.classList.remove('hidden');
    } else {
      panel.classList.add('hidden');
    }
  }
}

function populateCustomToolsList() {
  const listEl = document.getElementById('custom-tools-list');
  if (!listEl) return;

  if (state.tools.length === 0) {
    listEl.innerHTML = '<p class="text-xs text-zinc-500 italic">Connect to MCP to see available tools</p>';
    return;
  }

  const savedCustomTools = state.chatSettings.customTools || [];

  listEl.innerHTML = state.tools.map(tool => `
    <label class="flex items-center gap-2 p-1 rounded hover:bg-white/5 cursor-pointer">
      <input type="checkbox" value="${tool.name}" 
        ${savedCustomTools.includes(tool.name) ? 'checked' : ''}
        class="custom-tool-checkbox w-4 h-4 accent-indigo-500">
      <span class="text-sm text-zinc-300">${formatToolName(tool.name)}</span>
      <span class="text-xs text-zinc-500">(${tool.name})</span>
    </label>
  `).join('');

  // Setup select all functionality
  const selectAllCheckbox = document.getElementById('select-all-tools');
  if (selectAllCheckbox) {
    // Update "Select All" state based on current selections
    updateSelectAllState();

    // Handle "Select All" click
    selectAllCheckbox.addEventListener('change', (e) => {
      const checkboxes = document.querySelectorAll('.custom-tool-checkbox');
      checkboxes.forEach(cb => cb.checked = e.target.checked);
    });

    // Update "Select All" when individual checkboxes change
    listEl.addEventListener('change', (e) => {
      if (e.target.classList.contains('custom-tool-checkbox')) {
        updateSelectAllState();
      }
    });
  }
}

function updateSelectAllState() {
  const selectAllCheckbox = document.getElementById('select-all-tools');
  const checkboxes = document.querySelectorAll('.custom-tool-checkbox');
  if (!selectAllCheckbox || checkboxes.length === 0) return;

  const checkedCount = document.querySelectorAll('.custom-tool-checkbox:checked').length;
  selectAllCheckbox.checked = checkedCount === checkboxes.length;
  selectAllCheckbox.indeterminate = checkedCount > 0 && checkedCount < checkboxes.length;
}

function getSelectedCustomTools() {
  const checkboxes = document.querySelectorAll('.custom-tool-checkbox:checked');
  return Array.from(checkboxes).map(cb => cb.value);
}

// ============================================
// Model Fetching
// ============================================
async function fetchModels() {
  const baseUrlInput = document.getElementById('settings-base-url');
  const tokenInput = document.getElementById('settings-token');
  const modelSelect = document.getElementById('settings-model');
  const fetchBtn = document.getElementById('settings-fetch-models-btn');

  const baseUrl = baseUrlInput?.value.trim();
  const token = tokenInput?.value.trim();

  if (!baseUrl) {
    log('error', 'Please enter a Base URL first');
    return;
  }

  // Show loading state
  if (fetchBtn) {
    fetchBtn.disabled = true;
    fetchBtn.innerHTML = `
      <svg class="animate-spin h-4 w-4" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none"></circle>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
      </svg>
    `;
  }

  try {
    const headers = {
      'Content-Type': 'application/json'
    };

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`${baseUrl}/models`, {
      method: 'GET',
      headers: headers
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();

    // Handle OpenAI-style response
    const models = data.data || data.models || data || [];
    const modelIds = Array.isArray(models)
      ? models.map(m => typeof m === 'string' ? m : m.id || m.name)
      : [];

    if (modelIds.length === 0) {
      log('warning', 'No models found');
      return;
    }

    state.chatSettings.availableModels = modelIds;
    populateModelSelect(modelIds, state.chatSettings.model);

    log('success', `Found ${modelIds.length} model(s)`);

  } catch (error) {
    log('error', `Failed to fetch models: ${error.message}`);
  } finally {
    if (fetchBtn) {
      fetchBtn.disabled = false;
      fetchBtn.textContent = 'Get Models';
    }
  }
}

function populateModelSelect(models, selectedModel) {
  const modelSelect = document.getElementById('settings-model');
  if (!modelSelect) return;

  modelSelect.innerHTML = `
    <option value="">Select a model...</option>
    ${models.map(model => `
      <option value="${model}" ${model === selectedModel ? 'selected' : ''}>${model}</option>
    `).join('')}
  `;
}
