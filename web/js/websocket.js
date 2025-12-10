/**
 * WebSocket Connection Module
 * Handles WebSocket connection to the MCP hub
 */

// ============================================
// Connection Handler
// ============================================
function initConnectionHandler() {
  elements.connectBtn.addEventListener('click', () => {
    if (state.isConnected) {
      disconnect();
    } else {
      connect();
    }
  });
}

function connect() {
  const endpoint = elements.wsEndpoint.value.trim();

  if (!endpoint) {
    log('error', 'Please enter a WebSocket endpoint URL');
    return;
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
    elements.connectBtn.innerHTML = '<span class="btn-icon">⚡</span> Disconnect';
  } else if (status === 'waiting') {
    statusEl.classList.add('waiting');
    textEl.textContent = 'Waiting for MCP servers...';
    elements.connectBtn.innerHTML = '<span class="btn-icon">⚡</span> Disconnect';
  } else {
    textEl.textContent = 'Disconnected';
    elements.connectBtn.innerHTML = '<span class="btn-icon">⚡</span> Connect';
    state.mcpConnected = false;
    state.mcpServers = [];
    dotEl.classList.remove('bg-green-500');
    dotEl.classList.add('bg-red-500');
  }
}
