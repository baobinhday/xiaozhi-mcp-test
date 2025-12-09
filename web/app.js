/**
 * MCP Tools Tester - Client Application
 * WebSocket communication and MCP JSON-RPC handling
 */

// ============================================
// State Management
// ============================================
const state = {
    websocket: null,
    isConnected: false,
    mcpConnected: false,
    mcpToolName: null,
    requestId: 1,
    pendingRequests: new Map()
};

// ============================================
// DOM Elements
// ============================================
const elements = {
    wsEndpoint: document.getElementById('ws-endpoint'),
    connectBtn: document.getElementById('connect-btn'),
    connectionStatus: document.getElementById('connection-status'),
    responseContent: document.getElementById('response-content'),
    logContent: document.getElementById('log-content'),
    toolBtns: document.querySelectorAll('.tool-btn'),
    toolForms: document.querySelectorAll('.tool-form')
};

// ============================================
// Initialize
// ============================================
document.addEventListener('DOMContentLoaded', () => {
    initToolNavigation();
    initConnectionHandler();
    log('info', 'Application initialized');
});

// ============================================
// Tool Navigation
// ============================================
function initToolNavigation() {
    elements.toolBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const toolId = btn.dataset.tool;

            // Update active button
            elements.toolBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            // Update active form
            elements.toolForms.forEach(form => {
                form.classList.remove('active');
                if (form.id === `${toolId}-form`) {
                    form.classList.add('active');
                }
            });

            log('info', `Switched to tool: ${toolId}`);
        });
    });
}

// ============================================
// WebSocket Connection
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
    updateConnectionUI(false);
    log('info', 'Disconnected');
}

function updateConnectionUI(status) {
    const statusEl = elements.connectionStatus;
    const textEl = statusEl.querySelector('.status-text');

    // Remove all status classes
    statusEl.classList.remove('connected', 'waiting');

    if (status === 'connected') {
        statusEl.classList.add('connected');
        textEl.textContent = 'Connected';
        elements.connectBtn.innerHTML = '<span class="btn-icon">⚡</span> Disconnect';
    } else if (status === 'waiting') {
        statusEl.classList.add('waiting');
        textEl.textContent = 'Waiting for MCP tool...';
        elements.connectBtn.innerHTML = '<span class="btn-icon">⚡</span> Disconnect';
    } else {
        textEl.textContent = 'Disconnected';
        elements.connectBtn.innerHTML = '<span class="btn-icon">⚡</span> Connect';
        state.mcpConnected = false;
        state.mcpToolName = null;
    }
}

// ============================================
// MCP JSON-RPC Protocol
// ============================================
function generateRequestId() {
    return state.requestId++;
}

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

function handleMessage(data) {
    try {
        const message = JSON.parse(data);

        // Handle status messages from hub
        if (message.type === 'status') {
            state.mcpConnected = message.mcp_connected;
            state.mcpToolName = message.mcp_tool_name;

            if (message.mcp_connected) {
                updateConnectionUI('connected');
                log('success', `MCP tool connected: ${message.mcp_tool_name}`);
                // Initialize MCP session
                sendInitialize();
            } else {
                updateConnectionUI('waiting');
                log('warning', 'MCP tool disconnected');
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
            // Notification or other message
            displayResponse(message);
        }
    } catch (error) {
        log('error', `Failed to parse message: ${error.message}`);
    }
}

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
        // Send initialized notification
        sendNotification('notifications/initialized', {});
    }).catch(error => {
        log('warning', `Initialize failed: ${error.message}`);
    });
}

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

// ============================================
// Tool Execution Functions
// ============================================
function executeWebSearch() {
    const query = document.getElementById('search-query').value.trim();
    const maxResults = parseInt(document.getElementById('search-results').value) || 5;

    if (!query) {
        log('error', 'Please enter a search query');
        return;
    }

    log('info', `Executing web search: "${query}"`);

    sendRequest('tools/call', {
        name: 'tim_kiem_web',
        arguments: {
            truy_van: query,
            so_ket_qua: maxResults
        }
    }).then(result => {
        log('success', 'Web search completed');
    }).catch(error => {
        log('error', `Web search failed: ${error.message}`);
    });
}

function executeNewsReader() {
    const maxArticles = parseInt(document.getElementById('news-count').value) || 3;

    log('info', `Fetching news (max ${maxArticles} per source)...`);

    sendRequest('tools/call', {
        name: 'doc_tin_tuc_moi_nhat',
        arguments: {
            so_bai_bao_toi_da: maxArticles
        }
    }).then(result => {
        log('success', 'News fetched successfully');
    }).catch(error => {
        log('error', `News fetch failed: ${error.message}`);
    });
}

function executeCalculator() {
    const expression = document.getElementById('calc-expression').value.trim();

    if (!expression) {
        log('error', 'Please enter a Python expression');
        return;
    }

    log('info', `Calculating: ${expression}`);

    sendRequest('tools/call', {
        name: 'calculator',
        arguments: {
            python_expression: expression
        }
    }).then(result => {
        log('success', 'Calculation completed');
    }).catch(error => {
        log('error', `Calculation failed: ${error.message}`);
    });
}

// ============================================
// Response Display
// ============================================
function displayResponse(data) {
    const html = syntaxHighlightJSON(data);
    elements.responseContent.innerHTML = `<div class="json-viewer">${html}</div>`;
}

function clearResponse() {
    elements.responseContent.innerHTML = `
        <div class="empty-state">
            <span class="empty-icon">📭</span>
            <p>Execute a tool to see results here</p>
        </div>
    `;
}

function syntaxHighlightJSON(obj) {
    const json = JSON.stringify(obj, null, 2);
    return json.replace(
        /("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g,
        (match) => {
            let cls = 'json-number';
            if (/^"/.test(match)) {
                if (/:$/.test(match)) {
                    cls = 'json-key';
                } else {
                    cls = 'json-string';
                }
            } else if (/true|false/.test(match)) {
                cls = 'json-boolean';
            } else if (/null/.test(match)) {
                cls = 'json-null';
            }
            return `<span class="${cls}">${escapeHtml(match)}</span>`;
        }
    );
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ============================================
// Logging
// ============================================
function log(type, message) {
    const time = new Date().toLocaleTimeString('en-US', { hour12: false });
    const entry = document.createElement('div');
    entry.className = `log-entry log-${type}`;
    entry.innerHTML = `
        <span class="log-time">${time}</span>
        <span class="log-message">${escapeHtml(message)}</span>
    `;

    elements.logContent.appendChild(entry);
    elements.logContent.scrollTop = elements.logContent.scrollHeight;

    // Console output
    console.log(`[${type.toUpperCase()}] ${message}`);
}

function clearLogs() {
    elements.logContent.innerHTML = '';
    log('info', 'Logs cleared');
}

// ============================================
// Keyboard Shortcuts
// ============================================
document.addEventListener('keydown', (e) => {
    // Enter to submit in input fields
    if (e.key === 'Enter' && e.target.classList.contains('input')) {
        const form = e.target.closest('.tool-form');
        if (form) {
            const btn = form.querySelector('.btn-execute');
            if (btn) btn.click();
        }
    }
});
