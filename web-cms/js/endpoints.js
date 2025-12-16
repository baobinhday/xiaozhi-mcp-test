// Endpoints Module

// API Functions
async function fetchEndpoints() {
  const response = await apiRequest('/api/endpoints');
  if (response.ok) {
    const data = await response.json();
    window.appState.endpoints = data.endpoints;
    renderEndpoints();
    updateStats();
  }
}

async function createEndpoint(name, url, enabled) {
  const response = await apiRequest('/api/endpoints', {
    method: 'POST',
    body: JSON.stringify({ name, url, enabled })
  });
  return response.ok;
}

async function updateEndpoint(id, data) {
  const response = await apiRequest(`/api/endpoints/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data)
  });
  return response.ok;
}

async function deleteEndpoint(id) {
  const response = await apiRequest(`/api/endpoints/${id}`, {
    method: 'DELETE'
  });
  return response.ok;
}

// UI Functions
function updateStats() {
  const total = window.appState.endpoints.length;
  const enabled = window.appState.endpoints.filter(e => e.enabled === 1).length;
  const disabled = total - enabled;

  document.getElementById('total-count').textContent = total;
  document.getElementById('enabled-count').textContent = enabled;
  document.getElementById('disabled-count').textContent = disabled;
}

function renderEndpoints() {
  const endpointsList = window.appState.dom.endpointsList;
  const emptyState = window.appState.dom.emptyState;
  const endpoints = window.appState.endpoints;

  if (endpoints.length === 0) {
    endpointsList.classList.add('hidden');
    emptyState.classList.remove('hidden');
    return;
  }

  endpointsList.classList.remove('hidden');
  emptyState.classList.add('hidden');

  endpointsList.innerHTML = endpoints.map(endpoint => {
    const connectionStatus = endpoint.connection_status || 'disconnected';
    const lastConnected = endpoint.last_connected_at ? formatDate(endpoint.last_connected_at) : 'Never';
    const errorMsg = endpoint.connection_error || '';
    const statusTitle = connectionStatus === 'error' ? `Error: ${errorMsg}` : connectionStatus.charAt(0).toUpperCase() + connectionStatus.slice(1);

    return `
                <div class="endpoint-card ${endpoint.enabled ? '' : 'disabled'}">
                    <div class="endpoint-status" title="${escapeHtml(statusTitle)}">
                        <span class="status-dot ${connectionStatus}"></span>
                    </div>
                    <div class="endpoint-info">
                        <h3 class="endpoint-name">${escapeHtml(endpoint.name)}</h3>
                        <div class="endpoint-url-container" style="display: flex; align-items: center; gap: 8px;">
                            <p class="endpoint-url" title="${escapeHtml(endpoint.url)}">${escapeHtml(maskUrl(endpoint.url))}</p>
                            <button class="btn-icon btn-copy-url" data-endpoint-id="${endpoint.id}" title="Copy full URL" style="font-size: 1rem; padding: 4px;">
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                                    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                                </svg>
                            </button>
                        </div>
                        <p class="endpoint-meta">
                            Status: ${statusTitle} • Last connected: ${lastConnected}
                        </p>
                    </div>
                    <div class="endpoint-actions">
                        <button class="btn btn-sm btn-toggle btn-toggle-endpoint" data-endpoint-id="${endpoint.id}" data-enabled="${endpoint.enabled}">
                            ${endpoint.enabled ? 'Disconnect' : 'Connect'}
                        </button>
                        <button class="btn btn-sm btn-edit btn-edit-endpoint" data-endpoint-id="${endpoint.id}">Edit</button>
                        <button class="btn btn-sm btn-delete btn-delete-endpoint" data-endpoint-id="${endpoint.id}" data-endpoint-name="${escapeHtml(endpoint.name)}">Delete</button>
                    </div>
                </div>
            `;
  }).join('');
}

function maskUrl(url) {
  if (!url) return '';
  if (url.length <= 40) return url;
  return url.substring(0, 25) + '...' + url.substring(url.length - 10);
}

// Status Streaming with SSE
function startStatusPolling() {
  // Close any existing EventSource connection
  stopStatusPolling();

  // Create SSE connection for real-time updates
  const eventSource = new EventSource('/api/endpoints/stream');

  eventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      if (data.endpoints) {
        window.appState.endpoints = data.endpoints;
        if (window.appState.currentTab === 'endpoints') {
          renderEndpoints();
          updateStats();
        }
      }
    } catch (e) {
      console.error('SSE parse error:', e);
    }
  };

  eventSource.onerror = (error) => {
    console.warn('SSE connection error, will auto-reconnect:', error);
    // EventSource will automatically attempt to reconnect
    // But if authentication fails, we should close and stop
    if (eventSource.readyState === EventSource.CLOSED) {
      console.log('SSE connection closed');
    }
  };

  // Store the EventSource reference for cleanup
  window.appState.statusEventSource = eventSource;
}

function stopStatusPolling() {
  if (window.appState.statusEventSource) {
    window.appState.statusEventSource.close();
    window.appState.statusEventSource = null;
  }
  // Also clear any legacy polling interval (for backward compatibility)
  if (window.appState.statusPollingInterval) {
    clearInterval(window.appState.statusPollingInterval);
    window.appState.statusPollingInterval = null;
  }
}

async function toggleEndpoint(id, newEnabledState) {
  if (await updateEndpoint(id, { enabled: newEnabledState ? 1 : 0 })) {
    await fetchEndpoints();
  }
}

async function editEndpoint(id) {
  const endpoint = window.appState.endpoints.find(e => e.id === id);
  if (endpoint) {
    showModal('Edit Endpoint', endpoint);
  }
}

function confirmDelete(id, name) {
  showDeleteModal(id, name);
}
