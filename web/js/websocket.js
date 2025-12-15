/**
 * WebSocket Connection Module
 * Handles WebSocket connection to the MCP hub
 */

// ============================================
// Connection Handler
// ============================================
function initConnectionHandler() {
  // Single toggle button handler
  elements.connectionToggleBtn.addEventListener('click', toggleConnection);

  // Copy endpoint button handler
  elements.copyEndpointBtn.addEventListener('click', copyEndpointUrl);
}

/**
 * Toggle connection state
 */
function toggleConnection() {
  if (state.isConnected) {
    disconnect();
  } else {
    connect();
  }
}

/**
 * Copy WebSocket endpoint URL to clipboard
 */
async function copyEndpointUrl() {
  const wsUrl = buildWebSocketUrl() + '/mcp';
  try {
    await navigator.clipboard.writeText(wsUrl);
    // Show feedback
    const btn = elements.copyEndpointBtn;
    const iconEl = btn.querySelector('.btn-icon');
    const originalIcon = iconEl.textContent;
    iconEl.textContent = '✓';
    setTimeout(() => {
      iconEl.textContent = originalIcon;
    }, 2000);
    log('success', `Copied endpoint: ${wsUrl}`);
  } catch (err) {
    log('error', `Failed to copy: ${err.message}`);
  }
}

/**
 * Build WebSocket URL from current page host
 * @returns {string} WebSocket URL
 */
function buildWebSocketUrl() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.hostname;
  // Use same port scheme: if HTTP is 8888, WS is 8889
  // We can derive this or use a fixed difference
  const httpPort = parseInt(window.location.port) || (window.location.protocol === 'https:' ? 443 : 80);
  const wsPort = httpPort === 8888 ? 8889 : httpPort + 1;
  return `${protocol}//${host}:${wsPort}`;
}

/**
 * Get session token from cookies
 * @returns {string} Session token or empty string
 */
function getSessionToken() {
  const cookies = document.cookie.split(';');
  for (const cookie of cookies) {
    const [name, value] = cookie.trim().split('=');
    if (name === 'web_session') return value;
  }
  return '';
}

function connect() {
  // Build WebSocket URL from current host
  let endpoint = buildWebSocketUrl();

  // Add session token for authentication
  const sessionToken = getSessionToken();
  if (sessionToken) {
    endpoint = `${endpoint}?token=${sessionToken}`;
  }

  try {
    log('info', `Connecting to ${endpoint.split('?')[0]}...`);
    state.websocket = new WebSocket(endpoint);

    // Update toggle button to show "Disconnect"
    updateToggleButton(true);

    state.websocket.onopen = () => {
      state.isConnected = true;
      updateConnectionUI('waiting');
      log('success', 'Connected to hub! Waiting for MCP servers...');
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
  // Reset toggle button to show "Connect"
  updateToggleButton(false);
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

/**
 * Update toggle button text and style based on connection state
 * @param {boolean} isConnected - Whether currently connected
 */
function updateToggleButton(isConnected) {
  const btn = elements.connectionToggleBtn;
  const iconEl = btn.querySelector('.btn-icon');
  const textEl = btn.querySelector('.btn-text');

  if (isConnected) {
    iconEl.textContent = '⛓️‍💥';
    textEl.textContent = 'Disconnect';
    btn.classList.remove('from-indigo-500', 'to-violet-500', 'hover:shadow-indigo-500/20');
    btn.classList.add('bg-[#1c1c26]', 'text-zinc-400', 'border', 'border-white/10', 'hover:bg-red-500/20', 'hover:text-red-400');
  } else {
    iconEl.textContent = '🔗';
    textEl.textContent = 'Connect';
    btn.classList.remove('bg-[#1c1c26]', 'text-zinc-400', 'border', 'border-white/10', 'hover:bg-red-500/20', 'hover:text-red-400');
    btn.classList.add('from-indigo-500', 'to-violet-500', 'hover:shadow-indigo-500/20');
  }
}
