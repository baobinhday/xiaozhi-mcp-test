/**
 * MCP JSON-RPC Protocol Module
 * Handles MCP protocol communication
 */

// ============================================
// Request ID Generation
// ============================================
function generateRequestId() {
  return state.requestId++;
}

// ============================================
// Send Request
// ============================================
function sendRequest(method, params = {}) {
  if (!state.isConnected || !state.websocket) {
    log('error', 'Not connected to server');
    return Promise.reject(new Error('Not connected'));
  }

  const id = generateRequestId();
  const request = {
    jsonrpc: '2.0',
    id: id,
    method: method,
    params: params
  };

  return new Promise((resolve, reject) => {
    state.pendingRequests.set(id, { resolve, reject });

    const message = JSON.stringify(request);
    state.websocket.send(message);
    log('sent', `→ ${method} (id: ${id})`);

    // Timeout after 30 seconds
    setTimeout(() => {
      if (state.pendingRequests.has(id)) {
        state.pendingRequests.delete(id);
        reject(new Error('Request timeout'));
      }
    }, 30000);
  });
}

// ============================================
// Handle Incoming Messages
// ============================================
function handleMessage(data) {
  let message;
  try {
    message = JSON.parse(data);
  } catch (error) {
    return;
  }

  // Handle status messages from hub
  if (message.type === 'status') {
    state.mcpConnected = message.mcp_connected;
    state.mcpServers = message.mcp_servers || [];

    if (message.mcp_connected && state.mcpServers.length > 0) {
      updateConnectionUI('connected');
      const serverList = state.mcpServers.join(', ');
      log('success', `MCP servers connected: ${serverList}`);
      sendInitialize();
    } else {
      updateConnectionUI('waiting');
      log('warning', 'MCP servers disconnected');
      state.tools = [];
      showNoToolsMessage();
    }
    return;
  }

  log('received', `← Response received`);

  if (message.id && state.pendingRequests.has(message.id)) {
    const { resolve, reject } = state.pendingRequests.get(message.id);
    state.pendingRequests.delete(message.id);

    if (message.error) {
      reject(new Error(message.error.message || 'Unknown error'));
      displayResponse({ error: message.error });
    } else {
      resolve(message.result);
      displayResponse(message.result);
    }
  } else {
    displayResponse(message);
  }
}

// ============================================
// Initialize MCP Session
// ============================================
function sendInitialize() {
  sendRequest('initialize', {
    protocolVersion: '2024-11-05',
    capabilities: {},
    clientInfo: {
      name: 'MCP Web Tester',
      version: '1.0.0'
    }
  }).then(result => {
    log('success', 'MCP session initialized');
    sendNotification('notifications/initialized', {});
    setTimeout(() => {
      fetchTools();
    }, 500);
  }).catch(error => {
    log('warning', `Initialize failed: ${error.message}`);
  });
}

// ============================================
// Send Notification
// ============================================
function sendNotification(method, params = {}) {
  if (!state.isConnected || !state.websocket) return;

  const notification = {
    jsonrpc: '2.0',
    method: method,
    params: params
  };

  state.websocket.send(JSON.stringify(notification));
  log('sent', `→ Notification: ${method}`);
}
