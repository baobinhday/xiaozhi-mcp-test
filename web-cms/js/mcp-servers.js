// MCP Servers Module

// API Functions
async function fetchMcpServers() {
  const response = await apiRequest('/api/mcp-servers');
  if (response.ok) {
    const data = await response.json();
    window.appState.mcpServers = data.servers;
    renderMcpServers();
    updateMcpStats();
  }
}

async function createMcpServer(serverData) {
  const response = await apiRequest('/api/mcp-servers', {
    method: 'POST',
    body: JSON.stringify(serverData)
  });
  return response.ok;
}

async function updateMcpServer(name, data) {
  const response = await apiRequest(`/api/mcp-servers/${encodeURIComponent(name)}`, {
    method: 'PUT',
    body: JSON.stringify(data)
  });
  return response.ok;
}

async function deleteMcpServerApi(name) {
  const response = await apiRequest(`/api/mcp-servers/${encodeURIComponent(name)}`, {
    method: 'DELETE'
  });
  return response.ok;
}

// UI Functions
function updateMcpStats() {
  const total = window.appState.mcpServers.length;
  const enabled = window.appState.mcpServers.filter(s => !s.disabled).length;
  const disabled = total - enabled;

  document.getElementById('mcp-total-count').textContent = total;
  document.getElementById('mcp-enabled-count').textContent = enabled;
  document.getElementById('mcp-disabled-count').textContent = disabled;
}

function renderMcpServers() {
  const mcpServersList = document.getElementById('mcp-servers-list');
  const mcpEmptyState = document.getElementById('mcp-empty-state');
  const mcpServers = window.appState.mcpServers;

  if (mcpServers.length === 0) {
    mcpServersList.classList.add('hidden');
    mcpEmptyState.classList.remove('hidden');
    return;
  }

  mcpServersList.classList.remove('hidden');
  mcpEmptyState.classList.add('hidden');

  mcpServersList.innerHTML = mcpServers.map(server => {
    const isHttp = server.type === 'http';
    const serverDetails = isHttp
      ? `<strong>URL:</strong> ${escapeHtml(server.url || '')}`
      : `<strong>${escapeHtml(server.command)}</strong> ${escapeHtml((server.args || []).join(' '))}`;
    const metaInfo = isHttp
      ? `Type: ${escapeHtml(server.type)}${server.headers && Object.keys(server.headers).length ? ' • Has headers' : ''}`
      : `Type: ${escapeHtml(server.type)}${server.env && Object.keys(server.env).length ? ' • Has env vars' : ''}`;

    return `
          <div class="endpoint-card ${server.disabled ? 'disabled' : ''}">
            <div class="endpoint-status">
              <span class="status-dot ${server.disabled ? 'inactive' : 'active'}"></span>
            </div>
            <div class="endpoint-info">
              <h3 class="endpoint-name">${escapeHtml(server.name)}</h3>
              <p class="endpoint-url">${serverDetails}</p>
              <p class="endpoint-meta">${metaInfo}</p>
            </div>
            <div class="endpoint-actions">
              <button class="btn btn-sm btn-toggle btn-toggle-server" data-server-name="${escapeHtml(server.name)}" data-disabled="${server.disabled}">
                ${server.disabled ? 'Enable' : 'Disable'}
              </button>
              <button class="btn btn-sm btn-edit btn-edit-server" data-server-name="${escapeHtml(server.name)}">Edit</button>
              <button class="btn btn-sm btn-delete btn-delete-server" data-server-name="${escapeHtml(server.name)}">Delete</button>
            </div>
          </div>
          `;
  }).join('');
}

// Modal Functions
function showMcpServerModal(title = 'Add MCP Server', server = null) {
  const mcpModalTitle = document.getElementById('mcp-modal-title');
  mcpModalTitle.textContent = title;
  document.getElementById('mcp-server-original-name').value = server?.name || '';
  document.getElementById('mcp-server-name').value = server?.name || '';
  document.getElementById('mcp-server-type').value = server?.type || 'stdio';
  document.getElementById('mcp-server-command').value = server?.command || '';
  document.getElementById('mcp-server-args').value = server?.args?.join('\\n') || '';
  document.getElementById('mcp-server-url').value = server?.url || '';

  // Convert env object to KEY=VALUE format
  const envStr = server?.env ? Object.entries(server.env).map(([k, v]) => `${k}=${v}`).join('\\n') : '';
  document.getElementById('mcp-server-env').value = envStr;

  // Convert headers object to KEY=VALUE format
  const headersStr = server?.headers ? Object.entries(server.headers).map(([k, v]) => `${k}=${v}`).join('\\n') : '';
  document.getElementById('mcp-server-headers').value = headersStr;

  document.getElementById('mcp-server-enabled').checked = !server?.disabled;

  toggleMcpTypeFields();
  document.getElementById('mcp-modal-overlay').classList.remove('hidden');
}

function toggleMcpTypeFields() {
  const type = document.getElementById('mcp-server-type').value;
  document.getElementById('stdio-fields').classList.toggle('hidden', type !== 'stdio');
  document.getElementById('http-fields').classList.toggle('hidden', type !== 'http');
}

function hideMcpServerModal() {
  document.getElementById('mcp-modal-overlay').classList.add('hidden');
  document.getElementById('mcp-server-form').reset();
}

function showMcpDeleteModal(name) {
  window.appState.deleteMcpServerName = name;
  document.getElementById('delete-mcp-server-name').textContent = name;
  document.getElementById('mcp-delete-modal-overlay').classList.remove('hidden');
}

function hideMcpDeleteModal() {
  document.getElementById('mcp-delete-modal-overlay').classList.add('hidden');
  window.appState.deleteMcpServerName = null;
}

// Event Handlers
async function toggleMcpServer(name, currentlyDisabled) {
  if (await updateMcpServer(name, { disabled: !currentlyDisabled })) {
    await fetchMcpServers();
  }
}

function editMcpServer(name) {
  const server = window.appState.mcpServers.find(s => s.name === name);
  if (server) {
    showMcpServerModal('Edit MCP Server', server);
  }
}

function confirmMcpDelete(name) {
  showMcpDeleteModal(name);
}

async function deleteMcpServer() {
  if (window.appState.deleteMcpServerName) {
    if (await deleteMcpServerApi(window.appState.deleteMcpServerName)) {
      hideMcpDeleteModal();
      await fetchMcpServers();
    }
  }
}
