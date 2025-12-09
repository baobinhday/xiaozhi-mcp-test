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
    mcpServers: [],  // List of connected server names
    requestId: 1,
    pendingRequests: new Map(),
    tools: [], // Store available tools
    selectedToolIndex: 0
};

// ============================================
// DOM Elements
// ============================================
const elements = {
    wsEndpoint: document.getElementById('ws-endpoint'),
    connectBtn: document.getElementById('connect-btn'),
    connectionStatus: document.getElementById('connection-status'),
    responsePanel: document.querySelector('.response-panel'),
    responseContent: document.getElementById('response-content'),
    logContent: document.getElementById('log-content'),
    toolNav: document.querySelector('.tool-nav'),
    toolPanel: document.querySelector('.tool-panel')
};

// ============================================
// Initialize
// ============================================
document.addEventListener('DOMContentLoaded', () => {
    initConnectionHandler();
    showNoToolsMessage();
    log('info', 'Application initialized');
});

function showNoToolsMessage() {
    elements.toolNav.innerHTML = `
        <div class="no-tools-message">
            <span class="no-tools-icon">🔌</span>
            <p>Connect to MCP server to see available tools</p>
        </div>
    `;
    elements.toolPanel.innerHTML = `
        <div class="empty-state">
            <span class="empty-icon">🔧</span>
            <p>No tools available. Connect to an MCP server first.</p>
        </div>
    `;
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
            // Clear tools on disconnect
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

    // Remove all status classes
    statusEl.classList.remove('connected', 'waiting');

    if (status === 'connected') {
        statusEl.classList.add('connected');
        const serverCount = state.mcpServers.length;
        const serverText = serverCount === 1 ? '1 server' : `${serverCount} servers`;
        textEl.textContent = `Connected (${serverText})`;
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
    let message;
    try {
        message = JSON.parse(data);
    } catch (error) {
        // Silently ignore non-JSON messages (debug output from MCP servers)
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
            // Initialize MCP session
            sendInitialize();
        } else {
            updateConnectionUI('waiting');
            log('warning', 'MCP servers disconnected');
            // Clear tools when MCP disconnects
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
        // Notification or other message
        displayResponse(message);
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
        // Wait a bit before fetching tools to allow servers to finish initialization
        setTimeout(() => {
            fetchTools();
        }, 500);
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
// Dynamic Tool Loading
// ============================================
function fetchTools() {
    log('info', 'Fetching available tools...');
    sendRequest('tools/list', {}).then(result => {
        const tools = result.tools || [];
        state.tools = tools;
        log('success', `Found ${tools.length} tool(s)`);

        if (tools.length > 0) {
            renderToolsList(tools);
            selectTool(0);
        } else {
            showNoToolsMessage();
        }
    }).catch(error => {
        log('error', `Failed to fetch tools: ${error.message}`);
        showNoToolsMessage();
    });
}

function renderToolsList(tools) {
    elements.toolNav.innerHTML = tools.map((tool, index) => `
        <button class="tool-btn ${index === 0 ? 'active' : ''}" data-tool-index="${index}">
            <span class="tool-icon">${getToolIcon(tool.name)}</span>
            <span class="tool-name">${formatToolName(tool.name)}</span>
            <span class="tool-desc">${tool.name}</span>
        </button>
    `).join('');

    // Add click handlers
    elements.toolNav.querySelectorAll('.tool-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const index = parseInt(btn.dataset.toolIndex);
            selectTool(index);
        });
    });
}

function selectTool(index) {
    state.selectedToolIndex = index;

    // Update button states
    elements.toolNav.querySelectorAll('.tool-btn').forEach((btn, i) => {
        btn.classList.toggle('active', i === index);
    });

    // Render the form for selected tool
    const tool = state.tools[index];
    if (tool) {
        renderToolForm(tool);
        log('info', `Selected tool: ${tool.name}`);
    }
}

function renderToolForm(tool) {
    const inputSchema = tool.inputSchema || {};
    const properties = inputSchema.properties || {};
    const required = inputSchema.required || [];

    let formHtml = `
        <div class="tool-form active" id="tool-form-${tool.name}">
            <div class="tool-header">
                <h2>${getToolIcon(tool.name)} ${formatToolName(tool.name)}</h2>
                <p>${tool.description || 'No description available'}</p>
            </div>
    `;

    // Generate form fields from schema
    for (const [propName, propSchema] of Object.entries(properties)) {
        const isRequired = required.includes(propName);
        const fieldId = `field-${tool.name}-${propName}`;

        formHtml += `
            <div class="form-group">
                <label for="${fieldId}">
                    ${formatFieldName(propName)}
                    ${isRequired ? '<span class="required">*</span>' : ''}
                </label>
                ${renderFormField(fieldId, propName, propSchema)}
                ${propSchema.description ? `<small class="field-hint">${propSchema.description}</small>` : ''}
            </div>
        `;
    }

    formHtml += `
            <button class="btn btn-execute" onclick="executeSelectedTool()">
                <span class="btn-icon">▶</span>
                Execute ${formatToolName(tool.name)}
            </button>
        </div>
    `;

    elements.toolPanel.innerHTML = formHtml;
}

function renderFormField(id, name, schema) {
    const type = schema.type || 'string';
    const defaultValue = schema.default !== undefined ? schema.default : '';

    switch (type) {
        case 'integer':
        case 'number':
            return `<input type="number" id="${id}" data-param="${name}" 
                    value="${defaultValue}" 
                    ${schema.minimum !== undefined ? `min="${schema.minimum}"` : ''} 
                    ${schema.maximum !== undefined ? `max="${schema.maximum}"` : ''} 
                    class="input input-small">`;

        case 'boolean':
            return `<select id="${id}" data-param="${name}" class="input input-small">
                <option value="true" ${defaultValue === true ? 'selected' : ''}>True</option>
                <option value="false" ${defaultValue === false ? 'selected' : ''}>False</option>
            </select>`;

        case 'array':
            return `<textarea id="${id}" data-param="${name}" 
                    placeholder="Enter values separated by newlines or as JSON array" 
                    class="input input-textarea">${defaultValue}</textarea>`;

        case 'object':
            return `<textarea id="${id}" data-param="${name}" 
                    placeholder="Enter JSON object" 
                    class="input input-textarea">${JSON.stringify(defaultValue || {}, null, 2)}</textarea>`;

        default: // string
            if (schema.enum) {
                return `<select id="${id}" data-param="${name}" class="input">
                    ${schema.enum.map(opt => `<option value="${opt}" ${opt === defaultValue ? 'selected' : ''}>${opt}</option>`).join('')}
                </select>`;
            }
            return `<input type="text" id="${id}" data-param="${name}" 
                    value="${defaultValue}" 
                    placeholder="${schema.description || `Enter ${formatFieldName(name)}...`}" 
                    class="input">`;
    }
}

// ============================================
// Tool Execution
// ============================================
function executeSelectedTool() {
    const tool = state.tools[state.selectedToolIndex];
    if (!tool) {
        log('error', 'No tool selected');
        return;
    }

    const args = collectFormArguments(tool);
    if (args === null) return; // Validation failed

    log('info', `Executing: ${tool.name}`);
    showLoading(`Running ${tool.name}...`);

    sendRequest('tools/call', {
        name: tool.name,
        arguments: args
    }).then(result => {
        hideLoading();
        log('success', `${tool.name} completed`);
    }).catch(error => {
        hideLoading();
        log('error', `${tool.name} failed: ${error.message}`);
    });
}

function collectFormArguments(tool) {
    const inputSchema = tool.inputSchema || {};
    const properties = inputSchema.properties || {};
    const required = inputSchema.required || [];
    const args = {};

    for (const [propName, propSchema] of Object.entries(properties)) {
        const fieldId = `field-${tool.name}-${propName}`;
        const element = document.getElementById(fieldId);

        if (!element) continue;

        let value = element.value.trim();
        const type = propSchema.type || 'string';

        // Handle empty values
        if (value === '' && required.includes(propName)) {
            log('error', `${formatFieldName(propName)} is required`);
            element.focus();
            return null;
        }

        if (value === '') continue; // Skip optional empty fields

        // Type conversion
        switch (type) {
            case 'integer':
                value = parseInt(value);
                if (isNaN(value)) {
                    log('error', `${formatFieldName(propName)} must be a valid integer`);
                    return null;
                }
                break;
            case 'number':
                value = parseFloat(value);
                if (isNaN(value)) {
                    log('error', `${formatFieldName(propName)} must be a valid number`);
                    return null;
                }
                break;
            case 'boolean':
                value = value === 'true';
                break;
            case 'array':
                try {
                    if (value.startsWith('[')) {
                        value = JSON.parse(value);
                    } else {
                        value = value.split('\n').map(v => v.trim()).filter(v => v);
                    }
                } catch (e) {
                    log('error', `${formatFieldName(propName)} must be a valid array`);
                    return null;
                }
                break;
            case 'object':
                try {
                    value = JSON.parse(value);
                } catch (e) {
                    log('error', `${formatFieldName(propName)} must be valid JSON`);
                    return null;
                }
                break;
        }

        args[propName] = value;
    }

    return args;
}

// ============================================
// Utility Functions
// ============================================
function getToolIcon(toolName) {
    const iconMap = {
        'search': '🔍',
        'web': '🌐',
        'news': '📰',
        'calculator': '🧮',
        'calc': '🧮',
        'file': '📁',
        'read': '📖',
        'write': '✍️',
        'email': '📧',
        'weather': '🌤️',
        'time': '⏰',
        'translate': '🌍',
        'image': '🖼️',
        'audio': '🎵',
        'video': '🎬',
        'database': '🗄️',
        'api': '🔗',
        'code': '💻',
        'git': '📦',
        'shell': '💻',
        'python': '🐍',
        'random': '🎲'
    };

    const lowerName = toolName.toLowerCase();
    for (const [key, icon] of Object.entries(iconMap)) {
        if (lowerName.includes(key)) return icon;
    }
    return '🔧';
}

function formatToolName(name) {
    return name
        .replace(/_/g, ' ')
        .replace(/([a-z])([A-Z])/g, '$1 $2')
        .split(' ')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
        .join(' ');
}

function formatFieldName(name) {
    return name
        .replace(/_/g, ' ')
        .replace(/([a-z])([A-Z])/g, '$1 $2')
        .split(' ')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
        .join(' ');
}

// ============================================
// Response Display
// ============================================
function showLoading(message = 'Executing tool...') {
    // Check if loading overlay already exists
    let overlay = elements.responsePanel.querySelector('.loading-overlay');
    if (!overlay) {
        overlay = document.createElement('div');
        overlay.className = 'loading-overlay';
        overlay.innerHTML = `
            <div class="loading-spinner"></div>
            <div class="loading-text">${message}</div>
        `;
        elements.responsePanel.appendChild(overlay);
    } else {
        overlay.querySelector('.loading-text').textContent = message;
    }
}

function hideLoading() {
    const overlay = elements.responsePanel.querySelector('.loading-overlay');
    if (overlay) {
        overlay.remove();
    }
}

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
    if (e.key === 'Enter' && e.target.classList.contains('input') && !e.target.classList.contains('input-textarea')) {
        const form = e.target.closest('.tool-form');
        if (form) {
            const btn = form.querySelector('.btn-execute');
            if (btn) btn.click();
        }
    }
});

