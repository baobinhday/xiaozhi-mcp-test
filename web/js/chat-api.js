/**
 * Chat API Module
 * LLM chat integration with tool calling support
 */

// ============================================
// Text Cleaning Utilities
// ============================================
/**
 * Clean text for speech synthesis by removing URLs, links, and special symbols
 * @param {string} text - The text to clean
 * @returns {string} - Cleaned text suitable for TTS
 */
function cleanTextForSpeech(text) {
  if (!text) return '';

  let cleaned = text;

  // Remove code blocks (```...```)
  cleaned = cleaned.replace(/```[\s\S]*?```/g, ' code block ');

  // Remove inline code (`...`)
  cleaned = cleaned.replace(/`([^`]+)`/g, '$1');

  // Remove markdown links [text](url) - keep only the text
  cleaned = cleaned.replace(/\[([^\]]+)\]\([^\)]+\)/g, '$1');

  // Remove plain URLs (http://, https://, www.)
  cleaned = cleaned.replace(/https?:\/\/[^\s]+/g, '');
  cleaned = cleaned.replace(/www\.[^\s]+/g, '');

  // Remove markdown headers (#, ##, ###, etc.)
  cleaned = cleaned.replace(/^#+\s+/gm, '');

  // Remove markdown bold/italic (**text**, *text*, __text__, _text_)
  cleaned = cleaned.replace(/\*\*([^\*]+)\*\*/g, '$1');
  cleaned = cleaned.replace(/\*([^\*]+)\*/g, '$1');
  cleaned = cleaned.replace(/__([^_]+)__/g, '$1');
  cleaned = cleaned.replace(/_([^_]+)_/g, '$1');

  // Remove special symbols that don't contribute to speech
  cleaned = cleaned.replace(/[•]/g, '');
  cleaned = cleaned.replace(/[→←↑↓]/g, '');
  cleaned = cleaned.replace(/[✓✗✕]/g, '');

  // Clean up multiple spaces
  cleaned = cleaned.replace(/\s+/g, ' ');

  // Trim
  cleaned = cleaned.trim();

  return cleaned;
}

// ============================================
// Chat Handler Initialization
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

// ============================================
// Send Message
// ============================================
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
  const historyIndex = state.chatHistory.length;
  state.chatHistory.push({ role: 'user', content: message });
  addChatMessage(message, 'user', historyIndex);

  // Clear input
  elements.chatInput.value = '';
  elements.chatInput.style.height = 'auto';

  log('info', `Chat message sent: ${message.substring(0, 50)}${message.length > 50 ? '...' : ''} `);

  // Call LLM API
  await callChatAPI();
}

// ============================================
// API Calls
// ============================================
async function callChatAPI() {
  const { baseUrl, token, model, systemPrompt, maxHistory } = state.chatSettings;

  // Build messages array
  const messages = [];

  // Add system prompt with current time
  const currentTime = new Date().toLocaleString('en-US', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    timeZoneName: 'short'
  });
  const timeContext = `Current date and time: ${currentTime}`;

  if (systemPrompt) {
    messages.push({ role: 'system', content: `${systemPrompt}\n\n${timeContext}` });
  } else {
    messages.push({ role: 'system', content: timeContext });
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
    log('error', `Chat API error: ${error.message} `);
    updateAssistantMessage(assistantDiv, `Error: ${error.message} `, true);
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
    headers['Authorization'] = `Bearer ${token} `;
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

      // Find the tool info from state.tools
      const tool = state.tools.find(t => t.name === toolName);

      // Show tool execution status
      updateAssistantMessage(assistantDiv, `🔧 Calling tool: ${toolName}...`);
      log('info', `Executing tool: ${toolName} with args: ${JSON.stringify(toolArgs)}`);
      displayRequest(toolArgs, tool);

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

    // Build system prompt with current time
    const currentTimeForContinuation = new Date().toLocaleString('en-US', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      timeZoneName: 'short'
    });
    const timeContextForContinuation = `Current date and time: ${currentTimeForContinuation}`;

    let systemContent;
    if (state.chatSettings.systemPrompt) {
      systemContent = `${state.chatSettings.systemPrompt}\n\n${timeContextForContinuation}`;
    } else {
      systemContent = timeContextForContinuation;
    }

    const updatedMessages = [
      { role: 'system', content: systemContent },
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

// ============================================
// Tool Execution
// ============================================
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
    log('sent', `→ tools / call: ${toolName} (id: ${id})`);
  });
}

function buildToolsForAPI() {
  const { toolMode, customTools } = state.chatSettings;

  if (toolMode === 'custom' && customTools && customTools.length > 0) {
    // Use custom selected tools
    return customTools
      .map(toolName => {
        const tool = state.tools.find(t => t.name === toolName);
        if (!tool) return null;
        return {
          type: 'function',
          function: {
            name: tool.name,
            description: tool.description || `Execute the ${tool.name} tool`,
            parameters: tool.inputSchema || { type: 'object', properties: {} }
          }
        };
      })
      .filter(t => t !== null);
  }

  // Default: use selected tool from sidebar
  const selectedTool = state.tools[state.selectedToolIndex];
  if (!selectedTool) {
    return [];
  }

  return [{
    type: 'function',
    function: {
      name: selectedTool.name,
      description: selectedTool.description || `Execute the ${selectedTool.name} tool`,
      parameters: selectedTool.inputSchema || { type: 'object', properties: {} }
    }
  }];
}

// ============================================
// Message UI
// ============================================
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
    div.className = 'chat-message-wrapper max-w-[80%] self-start';
    div.innerHTML = `
      <div class="chat-message px-4 py-3 rounded-2xl text-sm leading-relaxed bg-red-500/10 text-red-400 border border-red-500/20 rounded-bl-sm whitespace-pre-wrap">${escapeHtml(content)}</div>
      <div class="speak-controls">
        <button class="regenerate-btn icon-btn" title="Regenerate response">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="23 4 23 10 17 10"></polyline>
            <polyline points="1 20 1 14 7 14"></polyline>
            <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
          </svg>
        </button>
      </div>
    `;
  } else {
    // Parse markdown to HTML
    const htmlContent = parseMarkdownToHtml(content);

    div.className = 'chat-message-wrapper max-w-[80%] self-start';
    div.innerHTML = `
      <div class="chat-message px-4 py-3 rounded-2xl text-sm leading-relaxed bg-[#1c1c26] text-zinc-200 border border-white/10 rounded-bl-sm">
        <div class="markdown-content">${htmlContent}</div>
      </div>
      <div class="speak-controls">
        <select class="tts-voice-select" onchange="setTtsVoice(this.value)" title="Select voice">
          ${getVoiceOptionsHtml()}
        </select>
        <button class="speak-btn icon-btn" title="Speak message" data-speak-text="${parseTextFromMarkDown(content)}">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
            <path d="M8 5v14l11-7z"/>
          </svg>
        </button>
        <button class="copy-btn icon-btn" title="Copy to clipboard" data-copy-text="${parseTextFromMarkDown(content)}">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
          </svg>
        </button>
        <button class="regenerate-btn icon-btn" title="Regenerate response">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="23 4 23 10 17 10"></polyline>
            <polyline points="1 20 1 14 7 14"></polyline>
            <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
          </svg>
        </button>
      </div>
`;
    // Add event listener to the speak button
    const speakBtn = div.querySelector('.speak-btn');
    if (speakBtn) {
      speakBtn.addEventListener('click', function () {
        const text = this.getAttribute('data-speak-text');
        const cleanedText = cleanTextForSpeech(text);
        speakText(cleanedText, this);
      });
    }

    // Add event listener to the copy button
    const copyBtn = div.querySelector('.copy-btn');
    if (copyBtn) {
      copyBtn.addEventListener('click', async function () {
        const text = this.getAttribute('data-copy-text');
        try {
          await navigator.clipboard.writeText(text);

          // Visual feedback - show checkmark icon
          const originalHTML = this.innerHTML;
          this.innerHTML = `
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="20 6 9 17 4 12"></polyline>
            </svg>
          `;
          this.classList.add('copied');

          // Reset after 2 seconds
          setTimeout(() => {
            this.innerHTML = originalHTML;
            this.classList.remove('copied');
          }, 2000);

          log('success', 'Copied to clipboard');
        } catch (err) {
          log('error', 'Failed to copy to clipboard');
          console.error('Copy failed:', err);
        }
      });
    }
  }

  // Add event listener to the regenerate button
  const regenerateBtn = div.querySelector('.regenerate-btn');
  if (regenerateBtn) {
    regenerateBtn.addEventListener('click', async function () {
      await regenerateResponse(div);
    });
  }

  elements.chatBody.scrollTop = elements.chatBody.scrollHeight;
}

function addChatMessage(content, role, historyIndex = null) {
  const emptyState = elements.chatBody.querySelector('.empty-state');
  if (emptyState) {
    emptyState.remove();
  }

  if (role === 'user') {
    // Create wrapper for user message with edit button
    const messageWrapper = document.createElement('div');
    messageWrapper.className = 'chat-message-wrapper max-w-[80%] self-end';
    messageWrapper.setAttribute('data-message-content', content);
    if (historyIndex !== null) {
      messageWrapper.setAttribute('data-history-index', historyIndex);
    }

    messageWrapper.innerHTML = `
      <div class="chat-message px-4 py-3 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap bg-gradient-to-br from-indigo-500 to-violet-500 text-white rounded-br-sm selection:bg-blue-100! selection:text-neutral-700">${escapeHtml(content)}</div>
      <div class="speak-controls">
        <button class="edit-btn icon-btn" title="Edit message">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
            <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
          </svg>
        </button>
      </div>
    `;

    // Add event listener to edit button
    const editBtn = messageWrapper.querySelector('.edit-btn');
    if (editBtn) {
      editBtn.addEventListener('click', function () {
        editUserMessage(messageWrapper);
      });
    }

    elements.chatBody.appendChild(messageWrapper);
  } else {
    // Assistant message (keep existing behavior)
    const messageDiv = document.createElement('div');
    const roleClasses = 'self-start bg-[#1c1c26] text-zinc-200 border border-white/10 rounded-bl-sm';

    messageDiv.className = `chat-message max-w-[80%] px-4 py-3 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap ${roleClasses}`;
    messageDiv.textContent = content;
    elements.chatBody.appendChild(messageDiv);
  }

  elements.chatBody.scrollTop = elements.chatBody.scrollHeight;
}

// ============================================
// Regenerate Response
// ============================================
async function regenerateResponse(currentDiv) {
  // Prevent multiple simultaneous requests
  if (state.isGenerating) {
    log('warning', 'Please wait for the current response to complete');
    return;
  }

  // Check if settings are configured
  if (!state.chatSettings.baseUrl || !state.chatSettings.model) {
    log('warning', 'Please configure chat settings first (Base URL and Model required)');
    openSettingsModal();
    return;
  }

  // Find the user message wrapper that precedes this assistant response
  const chatMessages = Array.from(elements.chatBody.children);
  const currentIndex = chatMessages.indexOf(currentDiv);

  if (currentIndex === -1) {
    log('error', 'Could not find message to regenerate');
    return;
  }

  // Find the previous user message wrapper (search backward from currentDiv)
  let userMessageWrapper = null;
  for (let i = currentIndex - 1; i >= 0; i--) {
    const el = chatMessages[i];
    if (el.classList.contains('chat-message-wrapper') && el.hasAttribute('data-history-index')) {
      userMessageWrapper = el;
      break;
    }
  }

  if (!userMessageWrapper) {
    log('error', 'No user message found to regenerate from');
    return;
  }

  // Get the history index from the user message
  const userHistoryIndex = parseInt(userMessageWrapper.getAttribute('data-history-index'), 10);

  if (isNaN(userHistoryIndex) || userHistoryIndex < 0) {
    log('error', 'Invalid history index for regeneration');
    return;
  }

  // Remove the current assistant message from the DOM
  currentDiv.remove();

  // Remove all messages after the user message (keep the user message itself)
  state.chatHistory = state.chatHistory.slice(0, userHistoryIndex + 1);

  log('info', 'Regenerating response...');

  // Call LLM API to regenerate
  await callChatAPI();
}

// ============================================
// Edit User Message
// ============================================
function editUserMessage(messageWrapper) {
  // Prevent editing if currently generating
  if (state.isGenerating) {
    log('warning', 'Please wait for the current response to complete');
    return;
  }

  const currentContent = messageWrapper.getAttribute('data-message-content');
  const messageDiv = messageWrapper.querySelector('.chat-message');

  // Create textarea for editing
  const textarea = document.createElement('textarea');
  textarea.className = 'w-full px-4 py-3 bg-[#16161d] border border-indigo-500/50 rounded-lg text-white text-sm font-sans resize-none min-h-[44px] focus:outline-none focus:border-indigo-500 focus:shadow-[0_0_20px_rgba(99,102,241,0.2)] transition-all';
  textarea.value = currentContent;
  textarea.style.height = 'auto';
  textarea.style.height = Math.min(textarea.scrollHeight, 200) + 'px';

  // Replace message div with textarea
  messageDiv.replaceWith(textarea);
  textarea.focus();
  textarea.setSelectionRange(textarea.value.length, textarea.value.length);

  // Auto-resize textarea
  textarea.addEventListener('input', () => {
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 200) + 'px';
  });

  // Create action buttons
  const actionDiv = document.createElement('div');
  actionDiv.className = 'flex gap-2 mt-2';
  actionDiv.innerHTML = `
    <button class="save-edit-btn px-3 py-1.5 bg-gradient-to-br from-indigo-500 to-violet-500 text-white rounded text-xs font-medium hover:shadow-lg transition-all cursor-pointer border-0">
      Save
    </button>
    <button class="cancel-edit-btn px-3 py-1.5 bg-[#1c1c26] border border-white/10 rounded text-zinc-400 text-xs font-medium hover:bg-[#272732] hover:text-zinc-200 transition-all cursor-pointer">
      Cancel
    </button>
  `;

  messageWrapper.appendChild(actionDiv);

  // Handle save
  const saveBtn = actionDiv.querySelector('.save-edit-btn');
  saveBtn.addEventListener('click', () => {
    const newContent = textarea.value.trim();
    if (!newContent) {
      log('warning', 'Message cannot be empty');
      return;
    }

    // Get the history index from the data attribute
    const historyIndex = parseInt(messageWrapper.getAttribute('data-history-index'), 10);

    if (isNaN(historyIndex) || historyIndex < 0) {
      log('error', 'Could not find message index in chat history');
      return;
    }

    // Remove all messages after this one from the DOM
    const allMessageWrappers = Array.from(elements.chatBody.querySelectorAll('.chat-message-wrapper, .chat-message'));
    const currentDomIndex = allMessageWrappers.indexOf(messageWrapper);
    for (let i = allMessageWrappers.length - 1; i > currentDomIndex; i--) {
      allMessageWrappers[i].remove();
    }

    // Remove all messages after this user message in history and update with new content
    state.chatHistory = state.chatHistory.slice(0, historyIndex);
    state.chatHistory.push({ role: 'user', content: newContent });

    // Update the stored history index (same position since we sliced and pushed)
    messageWrapper.setAttribute('data-history-index', historyIndex);

    // Update the message wrapper
    messageWrapper.setAttribute('data-message-content', newContent);

    // Restore the message div
    const newMessageDiv = document.createElement('div');
    newMessageDiv.className = 'chat-message px-4 py-3 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap bg-gradient-to-br from-indigo-500 to-violet-500 text-white rounded-br-sm selection:bg-blue-100! selection:text-neutral-700';
    newMessageDiv.textContent = newContent;

    textarea.replaceWith(newMessageDiv);
    actionDiv.remove();

    log('success', 'Message edited and subsequent messages cleared');

    // Auto-send the edited message
    callChatAPI();
  });

  // Handle cancel
  const cancelBtn = actionDiv.querySelector('.cancel-edit-btn');
  cancelBtn.addEventListener('click', () => {
    // Restore original message div
    const restoredMessageDiv = document.createElement('div');
    restoredMessageDiv.className = 'chat-message px-4 py-3 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap bg-gradient-to-br from-indigo-500 to-violet-500 text-white rounded-br-sm selection:bg-blue-100! selection:text-neutral-700';
    restoredMessageDiv.textContent = currentContent;

    textarea.replaceWith(restoredMessageDiv);
    actionDiv.remove();

    log('info', 'Edit cancelled');
  });

  // Handle Enter key to save (Shift+Enter for new line)
  textarea.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      saveBtn.click();
    } else if (e.key === 'Escape') {
      e.preventDefault();
      cancelBtn.click();
    }
  });
}

// ============================================
// Chat History
// ============================================
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

  // Calculate the start index for slicing
  let startIndex = state.chatHistory.length - maxMessages;

  // Ensure we don't cut in the middle of a tool call chain
  // A tool call chain consists of: assistant (with tool_calls) -> tool (results)
  // We need to find a safe cut point that doesn't break this sequence

  // Move startIndex backward if we're cutting in the middle of a tool sequence
  while (startIndex > 0) {
    const msg = state.chatHistory[startIndex];

    // If we're starting at a tool result, we need to include the preceding assistant message
    if (msg.role === 'tool') {
      startIndex--;
      continue;
    }

    // If we're starting at an assistant message with tool_calls, 
    // we need to include the preceding user message for context
    if (msg.role === 'assistant' && msg.tool_calls) {
      startIndex--;
      continue;
    }

    // Safe cut point found (user message or regular assistant message)
    break;
  }

  return state.chatHistory.slice(startIndex);
}
