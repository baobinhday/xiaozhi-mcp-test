// MCP Tools Module

// API Functions
async function fetchToolsConfig() {
  const response = await apiRequest('/api/mcp-tools');
  if (response.ok) {
    const data = await response.json();
    window.appState.disabledTools = data.disabledTools || {};
    window.appState.customTools = data.customTools || {};
  }
}

async function updateToolMeta(serverName, toolName, customName, customDescription) {
  const response = await apiRequest('/api/mcp-tools/update', {
    method: 'POST',
    body: JSON.stringify({ serverName, toolName, customName, customDescription })
  });
  return response.ok;
}

async function resetToolMeta(serverName, toolName) {
  const response = await apiRequest('/api/mcp-tools/reset', {
    method: 'POST',
    body: JSON.stringify({ serverName, toolName })
  });
  return response.ok;
}

async function toggleToolEnabled(serverName, toolName, enabled) {
  const response = await apiRequest('/api/mcp-tools/toggle', {
    method: 'POST',
    body: JSON.stringify({ serverName, toolName, enabled })
  });
  if (response.ok) {
    // Update local state
    if (!enabled) {
      if (!window.appState.disabledTools[serverName]) window.appState.disabledTools[serverName] = [];
      if (!window.appState.disabledTools[serverName].includes(toolName)) {
        window.appState.disabledTools[serverName].push(toolName);
      }
    } else {
      if (window.appState.disabledTools[serverName]) {
        window.appState.disabledTools[serverName] = window.appState.disabledTools[serverName].filter(t => t !== toolName);
        if (window.appState.disabledTools[serverName].length === 0) delete window.appState.disabledTools[serverName];
      }
    }
    renderMcpTools();
    updateToolsStats();
  }
  return response.ok;
}

async function fetchMcpTools() {
  const toolsLoadingState = document.getElementById('tools-loading-state');
  const toolsEmptyState = document.getElementById('tools-empty-state');
  const mcpToolsList = document.getElementById('mcp-tools-list');

  console.log('[fetchMcpTools] Starting fetch...');
  toolsLoadingState.classList.remove('hidden');
  toolsEmptyState.classList.add('hidden');
  mcpToolsList.innerHTML = '';

  try {
    // Fetch tools config (disabled tools, custom descriptions)
    await fetchToolsConfig();

    // Fetch cached tools list from bridge (all tools, unfiltered)
    const response = await apiRequest('/api/mcp-tools/cache');

    toolsLoadingState.classList.add('hidden');

    if (response.ok) {
      const data = await response.json();
      console.log('[fetchMcpTools] Received data:', data);
      console.log('[fetchMcpTools] Tools object:', data.tools);

      // Convert tools object to array
      // data.tools is {serverName: [tool1, tool2, ...], ...}
      // We need to flatten it and add server info to each tool
      const toolsArray = [];
      if (data.tools && typeof data.tools === 'object') {
        for (const serverName in data.tools) {
          if (Array.isArray(data.tools[serverName])) {
            data.tools[serverName].forEach(tool => {
              // Add server name to the tool object
              toolsArray.push({
                ...tool,
                serverName: serverName
              });
            });
          }
        }
      }

      window.appState.mcpTools = toolsArray;
      console.log('[fetchMcpTools] Flattened to array:', window.appState.mcpTools);
      renderMcpTools();
      updateToolsStats();
      updateServerFilter();

      if (window.appState.mcpTools.length === 0) {
        toolsEmptyState.classList.remove('hidden');
      }
    } else {
      console.error('[fetchMcpTools] Response not OK:', response.status);
    }
  } catch (error) {
    toolsLoadingState.classList.add('hidden');
    console.error('Failed to load tools:', error);
  }
}

// UI Functions
function updateServerFilter() {
  const toolsServerFilterEl = document.getElementById('tools-server-filter');
  if (!toolsServerFilterEl) {
    console.warn('[updateServerFilter] tools-server-filter element not found');
    return;
  }

  const servers = new Set();
  window.appState.mcpTools.forEach(tool => {
    if (tool.serverName) {
      servers.add(tool.serverName);
    }
  });

  toolsServerFilterEl.innerHTML = '<option value="">All Servers</option>';
  servers.forEach(server => {
    toolsServerFilterEl.innerHTML += `<option value="${escapeHtml(server)}">${escapeHtml(server)}</option>`;
  });

  console.log('[updateServerFilter] Updated filter with servers:', Array.from(servers));
}

function updateToolsStats() {
  const total = window.appState.mcpTools.length;
  let disabled = 0;

  window.appState.mcpTools.forEach(tool => {
    const serverName = tool.serverName || 'unknown';
    if (window.appState.disabledTools[serverName]?.includes(tool.name)) {
      disabled++;
    }
  });

  const enabled = total - disabled;

  document.getElementById('tools-total-count').textContent = total;
  document.getElementById('tools-enabled-count').textContent = enabled;
  document.getElementById('tools-disabled-count').textContent = disabled;
}

function renderMcpTools() {
  const mcpToolsList = document.getElementById('mcp-tools-list');
  const toolsEmptyState = document.getElementById('tools-empty-state');

  // Ensure mcpTools is an array
  if (!Array.isArray(window.appState.mcpTools)) {
    window.appState.mcpTools = [];
  }

  let filteredTools = window.appState.mcpTools;

  // Apply server filter
  if (window.appState.toolsServerFilter) {
    filteredTools = filteredTools.filter(tool => {
      return tool.serverName === window.appState.toolsServerFilter;
    });
  }

  // Apply status filter (enabled/disabled)
  if (window.appState.toolsStatusFilter) {
    filteredTools = filteredTools.filter(tool => {
      const serverName = tool.serverName || 'unknown';
      const isDisabled = window.appState.disabledTools[serverName]?.includes(tool.name) || false;
      if (window.appState.toolsStatusFilter === 'enabled') {
        return !isDisabled;
      } else if (window.appState.toolsStatusFilter === 'disabled') {
        return isDisabled;
      }
      return true;
    });
  }

  if (!filteredTools || filteredTools.length === 0) {
    mcpToolsList.innerHTML = '';
    if (window.appState.mcpTools.length === 0) {
      toolsEmptyState.classList.remove('hidden');
    }
    return;
  }

  toolsEmptyState.classList.add('hidden');

  mcpToolsList.innerHTML = filteredTools.map(tool => {
    const serverName = tool.serverName || 'unknown';
    const originalDescription = tool.description || '';
    const isDisabled = window.appState.disabledTools[serverName]?.includes(tool.name) || false;

    // Check for custom metadata
    const toolCustom = window.appState.customTools[serverName]?.[tool.name] || {};
    const displayName = toolCustom.name || tool.name;
    const displayDescription = toolCustom.description || originalDescription;
    const hasCustomMeta = toolCustom.name || toolCustom.description;

    return `
          <div class="endpoint-card ${isDisabled ? 'disabled' : ''}">
            <div class="endpoint-status">
              <span class="status-dot ${isDisabled ? 'inactive' : 'active'}"></span>
            </div>
            <div class="endpoint-info">
              <h3 class="endpoint-name">
                ${escapeHtml(displayName)}
                ${hasCustomMeta ? '<span style="font-size: 0.75rem; color: var(--accent-blue); margin-left: 0.5rem;">✎ custom</span>' : ''}
              </h3>
              <p class="endpoint-url">${escapeHtml(displayDescription || 'No description')}</p>
              <p class="endpoint-meta">Server: ${escapeHtml(serverName)} • Tool: ${escapeHtml(tool.name)}</p>
            </div>
            <div class="endpoint-actions">
              <button class="btn btn-sm btn-edit btn-edit-tool" data-server-name="${escapeHtml(serverName)}" data-tool-name="${escapeHtml(tool.name)}" data-original-desc="${escapeHtml(originalDescription || '')}">Edit</button>
              <button class="btn btn-sm btn-toggle btn-toggle-tool" data-server-name="${escapeHtml(serverName)}" data-tool-name="${escapeHtml(tool.name)}" data-disabled="${isDisabled}">
                ${isDisabled ? 'Enable' : 'Disable'}
              </button>
            </div>
          </div>
        `;
  }).join('');
}

// Event Handlers
async function handleToolToggle(serverName, toolName, isCurrentlyDisabled) {
  await toggleToolEnabled(serverName, toolName, isCurrentlyDisabled);
}

function openToolEditModal(serverName, toolName, originalDescription) {
  document.getElementById('tool-edit-server-name').value = serverName;
  document.getElementById('tool-edit-tool-name').value = toolName;
  document.getElementById('tool-edit-original-desc').value = originalDescription;
  document.getElementById('tool-edit-original-desc-display').textContent = originalDescription || 'No description';
  document.getElementById('tool-edit-modal-title').textContent = `Edit Tool: ${toolName}`;

  // Pre-fill with existing custom values if any
  const toolCustom = window.appState.customTools[serverName]?.[toolName] || {};
  document.getElementById('tool-edit-custom-desc').value = toolCustom.description || '';

  document.getElementById('tool-edit-modal-overlay').classList.remove('hidden');
}

function hideToolEditModal() {
  document.getElementById('tool-edit-modal-overlay').classList.add('hidden');
  document.getElementById('tool-edit-form').reset();
}
