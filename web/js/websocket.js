/**
 * WebSocket Connection Module
 * Handles WebSocket connection to the MCP hub
 */

// ============================================
// Connection Handler
// ============================================
function initConnectionHandler() {
  // Fetch endpoints on init
  fetchEndpoints();

  // Connect/disconnect on select change
  elements.wsEndpoint.addEventListener('change', () => {
    const endpoint = elements.wsEndpoint.value;
    if (endpoint) {
      connect();
    } else {
      disconnect();
    }
  });

  // Refresh button handler
  elements.refreshEndpointsBtn.addEventListener('click', fetchEndpoints);
}

async function fetchEndpoints() {
  try {
    log('info', 'Fetching endpoints...');
    const response = await fetch('/api/endpoints', {
      credentials: 'include'
    });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const data = await response.json();
    populateEndpointSelect(data.endpoints || []);
    log('success', `Found ${data.endpoints?.length || 0} endpoint(s)`);
  } catch (error) {
    log('error', `Failed to fetch endpoints: ${error.message}`);
  }
}

function populateEndpointSelect(endpoints) {
  const select = elements.wsEndpoint;
  const currentValue = select.value;

  // Clear and add default option
  select.innerHTML = '<option value="">Select an endpoint...</option>';

  // Add endpoint options
  endpoints.forEach(ep => {
    const option = document.createElement('option');
    option.value = ep.url;
    option.textContent = ep.name;
    select.appendChild(option);
  });

  // Restore previous selection if still valid
  if (currentValue) {
    const exists = Array.from(select.options).some(opt => opt.value === currentValue);
    if (exists) {
      select.value = currentValue;
    }
  }
}

function connect() {
  let endpoint = elements.wsEndpoint.value.trim();

  if (!endpoint) {
    log('error', 'Please select an endpoint');
    return;
  }

  // Strip /mcp suffix if present - browser connects to hub root, not MCP tool path
  endpoint = endpoint.replace(/\/mcp\/?(\?.*)?$/, '$1');

  // Upgrade protocol if page is loaded via HTTPS
  if (window.location.protocol === 'https:' && endpoint.startsWith('ws://')) {
    endpoint = endpoint.replace('ws://', 'wss://');
    log('info', 'Upgraded WebSocket protocol to WSS (Secure)');
  }

  // If endpoint is localhost, replace with current window hostname
  // This allows connecting to the server when accessing from a different device
  if (endpoint.includes('//localhost') || endpoint.includes('//127.0.0.1')) {
    const hostname = window.location.hostname;
    // Don't replace if we're actually on localhost
    if (hostname !== 'localhost' && hostname !== '127.0.0.1') {
      endpoint = endpoint.replace('//localhost', `//${hostname}`).replace('//127.0.0.1', `//${hostname}`);
      log('info', `Adjusted endpoint to: ${endpoint}`);
    }
  }

  try {
    log('info', `Connecting to ${endpoint}...`);
    state.websocket = new WebSocket(endpoint);

    state.websocket.onopen = () => {
      state.isConnected = true;
      updateConnectionUI('waiting');
      log('success', 'Connected to hub! Waiting for MCP tool...');
    };

    state.websocket.onclose = (event) => {
      state.isConnected = false;
      updateConnectionUI(false);
      log('warning', `Connection closed: ${event.code} ${event.reason || ''}`);
      state.tools = [];
      showNoToolsMessage();
    };

    state.websocket.onerror = (error) => {
      log('error', `WebSocket error: ${error.message || 'Unknown error'}`);
    };

    state.websocket.onmessage = (event) => {
      handleMessage(event.data);
    };

  } catch (error) {
    log('error', `Failed to connect: ${error.message}`);
  }
}

function disconnect() {
  if (state.websocket) {
    state.websocket.close();
    state.websocket = null;
  }
  state.isConnected = false;
  state.tools = [];
  updateConnectionUI(false);
  showNoToolsMessage();
  log('info', 'Disconnected');
}

function updateConnectionUI(status) {
  const statusEl = elements.connectionStatus;
  const textEl = statusEl.querySelector('.status-text');
  const dotEl = statusEl.querySelector('.status-dot');

  statusEl.classList.remove('connected', 'waiting');

  if (status === 'connected') {
    statusEl.classList.add('connected');
    const serverCount = state.mcpServers.length;
    const serverText = serverCount === 1 ? '1 server' : `${serverCount} servers`;
    textEl.textContent = `Connected (${serverText})`;
    dotEl.classList.remove('bg-red-500');
    dotEl.classList.add('bg-green-500');
  } else if (status === 'waiting') {
    statusEl.classList.add('waiting');
    textEl.textContent = 'Waiting for MCP servers...';
  } else {
    textEl.textContent = 'Disconnected';
    state.mcpConnected = false;
    state.mcpServers = [];
    dotEl.classList.remove('bg-green-500');
    dotEl.classList.add('bg-red-500');
  }
}
