/**
 * Chat Module
 * Chat interface, tab management, and settings modal
 */

// ============================================
// Tab Management
// ============================================
function initTabHandler() {
  elements.tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const tabName = btn.dataset.tab;
      switchTab(tabName);
    });
  });
}

function switchTab(tabName) {
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

// ============================================
// Chat Handler
// ============================================
function initChatHandler() {
  elements.chatSendBtn.addEventListener('click', sendChatMessage);

  elements.chatInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendChatMessage();
    }
  });

  elements.chatInput.addEventListener('input', () => {
    elements.chatInput.style.height = 'auto';
    elements.chatInput.style.height = Math.min(elements.chatInput.scrollHeight, 120) + 'px';
  });

  // Settings button
  elements.chatSettingsBtn.addEventListener('click', openSettingsModal);

  // Initialize settings modal elements
  initSettingsModal();
}

async function sendChatMessage() {
  const message = elements.chatInput.value.trim();
  if (!message) return;

  // Check if settings are configured
  if (!state.chatSettings.baseUrl || !state.chatSettings.model) {
    log('warning', 'Please configure chat settings first (Base URL and Model required)');
    openSettingsModal();
    return;
  }

  // Prevent multiple simultaneous requests
  if (state.isGenerating) {
    log('warning', 'Please wait for the current response to complete');
    return;
  }

  // Add user message to UI and history
  addChatMessage(message, 'user');
  state.chatHistory.push({ role: 'user', content: message });

  // Clear input
  elements.chatInput.value = '';
  elements.chatInput.style.height = 'auto';

  log('info', `Chat message sent: ${message.substring(0, 50)}${message.length > 50 ? '...' : ''}`);

  // Call LLM API
  await callChatAPI();
}

async function callChatAPI() {
  const { baseUrl, token, model, systemPrompt, maxHistory } = state.chatSettings;

  // Build messages array
  const messages = [];

  // Add system prompt
  if (systemPrompt) {
    messages.push({ role: 'system', content: systemPrompt });
  }

  // Add chat history (trimmed to maxHistory)
  const recentHistory = getRecentHistory(maxHistory || 20);
  messages.push(...recentHistory);

  // Build tools array (only selected tool)
  const tools = buildToolsForAPI();

  state.isGenerating = true;
  elements.chatSendBtn.disabled = true;

  // Create placeholder for assistant message
  const assistantDiv = createAssistantMessageDiv();

  try {
    const result = await sendChatRequest(baseUrl, token, model, messages, tools, assistantDiv);

    if (result.content) {
      state.chatHistory.push({ role: 'assistant', content: result.content });
      log('success', 'Response received');
    }

  } catch (error) {
    log('error', `Chat API error: ${error.message}`);
    updateAssistantMessage(assistantDiv, `Error: ${error.message}`, true);
  } finally {
    state.isGenerating = false;
    elements.chatSendBtn.disabled = false;
  }
}

async function sendChatRequest(baseUrl, token, model, messages, tools, assistantDiv) {
  const headers = {
    'Content-Type': 'application/json'
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const body = {
    model: model,
    messages: messages,
    stream: false // Disable streaming for tool calls
  };

  // Add tools if available
  if (tools && tools.length > 0) {
    body.tools = tools;
    body.tool_choice = 'auto';
  }

  const response = await fetch(`${baseUrl}/chat/completions`, {
    method: 'POST',
    headers: headers,
    body: JSON.stringify(body)
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.error?.message || `HTTP ${response.status}: ${response.statusText}`);
  }

  const data = await response.json();
  const choice = data.choices?.[0];
  const message = choice?.message;

  if (!message) {
    throw new Error('No response from API');
  }

  // Check if the model wants to call a tool
  if (message.tool_calls && message.tool_calls.length > 0) {
    log('info', `LLM wants to call tool: ${message.tool_calls[0].function.name}`);

    // Add assistant message with tool calls to history
    state.chatHistory.push({
      role: 'assistant',
      content: message.content || null,
      tool_calls: message.tool_calls
    });

    // Execute each tool call
    for (const toolCall of message.tool_calls) {
      const toolName = toolCall.function.name;
      const toolArgs = JSON.parse(toolCall.function.arguments || '{}');

      // Show tool execution status
      updateAssistantMessage(assistantDiv, `🔧 Calling tool: ${toolName}...`);
      log('info', `Executing tool: ${toolName} with args: ${JSON.stringify(toolArgs)}`);

      try {
        // Execute tool via MCP
        const toolResult = await executeToolForChat(toolName, toolArgs);

        // Add tool result to history
        state.chatHistory.push({
          role: 'tool',
          tool_call_id: toolCall.id,
          content: JSON.stringify(toolResult)
        });

        log('success', `Tool ${toolName} completed`);

      } catch (error) {
        log('error', `Tool ${toolName} failed: ${error.message}`);

        // Add error result to history
        state.chatHistory.push({
          role: 'tool',
          tool_call_id: toolCall.id,
          content: JSON.stringify({ error: error.message })
        });
      }
    }

    // Continue conversation with tool results
    updateAssistantMessage(assistantDiv, '💭 Processing results...');

    const updatedMessages = [
      ...(state.chatSettings.systemPrompt ? [{ role: 'system', content: state.chatSettings.systemPrompt }] : []),
      ...state.chatHistory
    ];

    // Make another API call to get final response
    return await sendChatRequest(baseUrl, token, model, updatedMessages, tools, assistantDiv);
  }

  // Regular text response
  if (message.content) {
    updateAssistantMessage(assistantDiv, message.content);
    return { content: message.content };
  }

  return { content: '' };
}

async function executeToolForChat(toolName, args) {
  // Use the existing MCP sendRequest function
  return new Promise((resolve, reject) => {
    if (!state.isConnected || !state.websocket) {
      reject(new Error('Not connected to MCP server'));
      return;
    }

    const id = generateRequestId();
    const request = {
      jsonrpc: '2.0',
      id: id,
      method: 'tools/call',
      params: {
        name: toolName,
        arguments: args
      }
    };

    // Set up response handler
    const timeout = setTimeout(() => {
      state.pendingRequests.delete(id);
      reject(new Error('Tool execution timeout'));
    }, 60000); // 60 second timeout for tool execution

    state.pendingRequests.set(id, {
      resolve: (result) => {
        clearTimeout(timeout);
        resolve(result);
      },
      reject: (error) => {
        clearTimeout(timeout);
        reject(error);
      }
    });

    state.websocket.send(JSON.stringify(request));
    log('sent', `→ tools/call: ${toolName} (id: ${id})`);
  });
}

function buildToolsForAPI() {
  const selectedTool = state.tools[state.selectedToolIndex];
  if (!selectedTool) {
    return [];
  }

  // Convert MCP tool schema to OpenAI function format
  const tool = {
    type: 'function',
    function: {
      name: selectedTool.name,
      description: selectedTool.description || `Execute the ${selectedTool.name} tool`,
      parameters: selectedTool.inputSchema || { type: 'object', properties: {} }
    }
  };

  return [tool];
}

function createAssistantMessageDiv() {
  const emptyState = elements.chatBody.querySelector('.empty-state');
  if (emptyState) {
    emptyState.remove();
  }

  const messageDiv = document.createElement('div');
  messageDiv.className = 'chat-message max-w-[80%] px-4 py-3 rounded-2xl text-sm leading-relaxed self-start bg-[#1c1c26] text-zinc-200 border border-white/10 rounded-bl-sm whitespace-pre-wrap';
  messageDiv.innerHTML = '<span class="typing-indicator">●●●</span>';
  elements.chatBody.appendChild(messageDiv);
  elements.chatBody.scrollTop = elements.chatBody.scrollHeight;

  return messageDiv;
}

function updateAssistantMessage(div, content, isError = false) {
  if (isError) {
    div.className = 'chat-message max-w-[80%] px-4 py-3 rounded-2xl text-sm leading-relaxed self-start bg-red-500/10 text-red-400 border border-red-500/20 rounded-bl-sm whitespace-pre-wrap';
  }
  div.textContent = content;
  elements.chatBody.scrollTop = elements.chatBody.scrollHeight;
}

function addChatMessage(content, role) {
  const emptyState = elements.chatBody.querySelector('.empty-state');
  if (emptyState) {
    emptyState.remove();
  }

  const messageDiv = document.createElement('div');
  const roleClasses = role === 'user'
    ? 'self-end bg-gradient-to-br from-indigo-500 to-violet-500 text-white rounded-br-sm'
    : 'self-start bg-[#1c1c26] text-zinc-200 border border-white/10 rounded-bl-sm';

  messageDiv.className = `chat-message max-w-[80%] px-4 py-3 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap ${roleClasses}`;
  messageDiv.textContent = content;
  elements.chatBody.appendChild(messageDiv);

  elements.chatBody.scrollTop = elements.chatBody.scrollHeight;
}

function clearChat() {
  state.chatHistory = [];
  elements.chatBody.innerHTML = `
    <div class="empty-state flex flex-col items-center justify-center h-full text-zinc-500 gap-4">
      <span class="empty-icon text-4xl opacity-50">💬</span>
      <p class="text-sm">Start a conversation...</p>
    </div>
  `;
  log('info', 'Chat cleared');
}

function getRecentHistory(maxMessages) {
  if (!maxMessages || state.chatHistory.length <= maxMessages) {
    return state.chatHistory;
  }
  // Keep the most recent messages
  return state.chatHistory.slice(-maxMessages);
}

// ============================================
// Settings Modal
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

  elements.settingsModal.classList.remove('hidden');
  elements.settingsModal.classList.add('flex');

  log('info', 'Settings modal opened');
}

function closeSettingsModal() {
  if (!elements.settingsModal) return;

  elements.settingsModal.classList.add('hidden');
  elements.settingsModal.classList.remove('flex');
}

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

  saveChatSettings();
  closeSettingsModal();

  log('success', 'Settings saved');
}

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
