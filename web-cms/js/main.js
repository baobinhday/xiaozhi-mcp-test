// Main Application Entry Point

// Global Application State
window.appState = {
  // Data
  endpoints: [],
  mcpServers: [],
  mcpTools: [],
  disabledTools: {},
  customTools: {},

  // UI State
  currentTab: 'endpoints',
  deleteTargetId: null,
  deleteMcpServerName: null,
  toolsServerFilter: '',
  statusPollingInterval: null,

  // DOM Elements (will be initialized on DOMContentLoaded)
  dom: {}
};

// Global Event Delegation (using event delegation to avoid inline onclick)
document.addEventListener('click', async (e) => {
  const target = e.target.closest('button');
  if (!target) return;

  // Endpoint actions
  if (target.classList.contains('btn-copy-url')) {
    const id = parseInt(target.dataset.endpointId);
    const endpoint = window.appState.endpoints.find(ep => ep.id === id);
    if (endpoint && endpoint.url) {
      try {
        await navigator.clipboard.writeText(endpoint.url);
        const originalHtml = target.innerHTML;
        target.innerHTML = `
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="20 6 9 17 4 12"></polyline>
          </svg>
        `;
        setTimeout(() => {
          target.innerHTML = originalHtml;
        }, 2000);
      } catch (err) {
        console.error('Failed to copy', err);
      }
    }
  }

  if (target.classList.contains('btn-toggle-endpoint')) {
    const id = parseInt(target.dataset.endpointId);
    const enabled = target.dataset.enabled === 'true';
    if (await updateEndpoint(id, { enabled: enabled ? 0 : 1 })) {
      await fetchEndpoints();
    }
  }

  if (target.classList.contains('btn-edit-endpoint')) {
    const id = parseInt(target.dataset.endpointId);
    const endpoint = window.appState.endpoints.find(e => e.id === id);
    if (endpoint) {
      showModal('Edit Endpoint', endpoint);
    }
  }

  if (target.classList.contains('btn-delete-endpoint')) {
    const id = parseInt(target.dataset.endpointId);
    const name = target.dataset.endpointName;
    showDeleteModal(id, name);
  }

  // MCP Server actions
  if (target.classList.contains('btn-toggle-server')) {
    const name = target.dataset.serverName;
    const disabled = target.dataset.disabled === 'true';
    if (await updateMcpServer(name, { disabled: !disabled })) {
      await fetchMcpServers();
    }
  }

  if (target.classList.contains('btn-edit-server')) {
    const name = target.dataset.serverName;
    const server = window.appState.mcpServers.find(s => s.name === name);
    if (server) {
      showMcpServerModal('Edit MCP Server', server);
    }
  }

  if (target.classList.contains('btn-delete-server')) {
    const name = target.dataset.serverName;
    showMcpDeleteModal(name);
  }

  // MCP Tools actions
  if (target.classList.contains('btn-edit-tool')) {
    const serverName = target.dataset.serverName;
    const toolName = target.dataset.toolName;
    const originalDesc = target.dataset.originalDesc;
    openToolEditModal(serverName, toolName, originalDesc);
  }

  if (target.classList.contains('btn-toggle-tool')) {
    const serverName = target.dataset.serverName;
    const toolName = target.dataset.toolName;
    const isDisabled = target.dataset.disabled === 'true';
    await toggleToolEnabled(serverName, toolName, isDisabled);
  }
});

// Initialize application
document.addEventListener('DOMContentLoaded', async () => {
  // Initialize DOM references
  window.appState.dom = {
    loginView: document.getElementById('login-view'),
    dashboardView: document.getElementById('dashboard-view'),
    loginForm: document.getElementById('login-form'),
    loginError: document.getElementById('login-error'),
    logoutBtn: document.getElementById('logout-btn'),
    addEndpointBtn: document.getElementById('add-endpoint-btn'),
    endpointsList: document.getElementById('endpoints-list'),
    emptyState: document.getElementById('empty-state'),
    modalOverlay: document.getElementById('modal-overlay'),
    modalTitle: document.getElementById('modal-title'),
    modalClose: document.getElementById('modal-close'),
    modalCancel: document.getElementById('modal-cancel'),
    endpointForm: document.getElementById('endpoint-form'),
    deleteModalOverlay: document.getElementById('delete-modal-overlay'),
    deleteEndpointName: document.getElementById('delete-endpoint-name'),
    deleteConfirmBtn: document.getElementById('delete-confirm'),
    deleteCancelBtn: document.getElementById('delete-cancel')
  };

  // Setup event listeners
  setupEventListeners();

  // Check authentication
  if (await checkAuth()) {
    showView(window.appState.dom.dashboardView);
    await fetchEndpoints();
    await fetchMcpServers();
    startStatusPolling();
  } else {
    showView(window.appState.dom.loginView);
  }
});

function setupEventListeners() {
  const { dom } = window.appState;

  // Initialize backup/restore listeners
  if (typeof initBackupRestoreListeners === 'function') {
    initBackupRestoreListeners();
  }

  // Tools server filter
  const toolsServerFilterEl = document.getElementById('tools-server-filter');
  if (toolsServerFilterEl) {
    toolsServerFilterEl.addEventListener('change', (e) => {
      window.appState.toolsServerFilter = e.target.value;
      if (typeof renderMcpTools === 'function') {
        renderMcpTools();
      }
    });
  }

  // Login
  dom.loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;

    dom.loginError.textContent = '';

    if (await login(username, password)) {
      showView(dom.dashboardView);
      await fetchEndpoints();
      await fetchMcpServers();
      startStatusPolling();
    } else {
      dom.loginError.textContent = 'Invalid username or password';
    }
  });

  // Logout
  dom.logoutBtn.addEventListener('click', async () => {
    stopStatusPolling();
    await logout();
    showView(dom.loginView);
  });

  // Endpoints
  dom.addEndpointBtn.addEventListener('click', () => {
    showModal('Add Endpoint');
  });

  dom.modalClose.addEventListener('click', () => {
    dom.modalOverlay.classList.add('hidden');
  });

  dom.modalCancel.addEventListener('click', () => {
    dom.modalOverlay.classList.add('hidden');
  });

  // Close modal when clicking outside the modal content
  dom.modalOverlay.addEventListener('click', (e) => {
    if (e.target === dom.modalOverlay) {
      dom.modalOverlay.classList.add('hidden');
    }
  });

  dom.endpointForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const id = document.getElementById('endpoint-id').value;
    const name = document.getElementById('endpoint-name').value;
    const url = document.getElementById('endpoint-url').value;
    const enabled = document.getElementById('endpoint-enabled').checked;

    let success = false;
    if (id) {
      success = await updateEndpoint(parseInt(id), { name, url, enabled: enabled ? 1 : 0 });
    } else {
      success = await createEndpoint(name, url, enabled ? 1 : 0);
    }

    if (success) {
      dom.modalOverlay.classList.add('hidden');
      await fetchEndpoints();
    }
  });

  // Delete confirmation
  if (dom.deleteCancelBtn) {
    dom.deleteCancelBtn.addEventListener('click', () => {
      dom.deleteModalOverlay.classList.add('hidden');
      window.appState.deleteTargetId = null;
    });
  }

  if (dom.deleteConfirmBtn) {
    dom.deleteConfirmBtn.addEventListener('click', async () => {
      if (window.appState.deleteTargetId) {
        if (await deleteEndpoint(window.appState.deleteTargetId)) {
          dom.deleteModalOverlay.classList.add('hidden');
          window.appState.deleteTargetId = null;
          await fetchEndpoints();
        }
      }
    });
  }

  // Tab switching
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      switchTab(btn.dataset.tab);
    });
  });

  // MCP Server Modal Event Listeners
  const mcpModalClose = document.getElementById('mcp-modal-close');
  const mcpModalCancel = document.getElementById('mcp-modal-cancel');
  const mcpModalOverlay = document.getElementById('mcp-modal-overlay');
  const mcpServerForm = document.getElementById('mcp-server-form');
  const mcpServerType = document.getElementById('mcp-server-type');

  if (mcpModalClose) {
    mcpModalClose.addEventListener('click', hideMcpServerModal);
  }

  if (mcpModalCancel) {
    mcpModalCancel.addEventListener('click', hideMcpServerModal);
  }

  if (mcpModalOverlay) {
    mcpModalOverlay.addEventListener('click', (e) => {
      if (e.target === mcpModalOverlay) hideMcpServerModal();
    });
  }

  if (mcpServerType) {
    mcpServerType.addEventListener('change', toggleMcpTypeFields);
  }

  if (mcpServerForm) {
    mcpServerForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const originalName = document.getElementById('mcp-server-original-name').value;
      const name = document.getElementById('mcp-server-name').value.trim();
      const type = document.getElementById('mcp-server-type').value;
      const enabled = document.getElementById('mcp-server-enabled').checked;

      const serverData = { name, type, disabled: !enabled };

      if (type === 'stdio') {
        serverData.command = document.getElementById('mcp-server-command').value.trim();
        const argsText = document.getElementById('mcp-server-args').value.trim();
        serverData.args = argsText ? argsText.split('\n').filter(a => a.trim()) : [];

        const envText = document.getElementById('mcp-server-env').value.trim();
        serverData.env = {};
        if (envText) {
          envText.split('\n').forEach(line => {
            const [key, ...valueParts] = line.split('=');
            if (key && valueParts.length > 0) {
              serverData.env[key.trim()] = valueParts.join('=').trim();
            }
          });
        }
      } else if (type === 'http') {
        serverData.url = document.getElementById('mcp-server-url').value.trim();
        const headersText = document.getElementById('mcp-server-headers').value.trim();
        serverData.headers = {};
        if (headersText) {
          headersText.split('\n').forEach(line => {
            const [key, ...valueParts] = line.split('=');
            if (key && valueParts.length > 0) {
              serverData.headers[key.trim()] = valueParts.join('=').trim();
            }
          });
        }
      }

      let success = false;
      if (originalName) {
        success = await updateMcpServer(originalName, serverData);
      } else {
        success = await createMcpServer(serverData);
      }

      if (success) {
        hideMcpServerModal();
        await fetchMcpServers();
      }
    });
  }

  // MCP Delete Modal Event Listeners
  const confirmMcpDeleteBtn = document.getElementById('confirm-mcp-delete-btn');
  const cancelMcpDeleteBtn = document.getElementById('cancel-mcp-delete-btn');
  const mcpDeleteModalOverlay = document.getElementById('mcp-delete-modal-overlay');

  if (confirmMcpDeleteBtn) {
    confirmMcpDeleteBtn.addEventListener('click', deleteMcpServer);
  }

  if (cancelMcpDeleteBtn) {
    cancelMcpDeleteBtn.addEventListener('click', hideMcpDeleteModal);
  }

  if (mcpDeleteModalOverlay) {
    mcpDeleteModalOverlay.addEventListener('click', (e) => {
      if (e.target === mcpDeleteModalOverlay) hideMcpDeleteModal();
    });
  }

  // Tool Edit Modal Event Listeners
  const toolEditModalClose = document.getElementById('tool-edit-modal-close');
  const toolEditCancel = document.getElementById('tool-edit-cancel');
  const toolEditModalOverlay = document.getElementById('tool-edit-modal-overlay');
  const toolEditForm = document.getElementById('tool-edit-form');
  const toolResetBtn = document.getElementById('tool-reset-btn');

  if (toolEditModalClose) {
    toolEditModalClose.addEventListener('click', hideToolEditModal);
  }

  if (toolEditCancel) {
    toolEditCancel.addEventListener('click', hideToolEditModal);
  }

  if (toolEditModalOverlay) {
    toolEditModalOverlay.addEventListener('click', (e) => {
      if (e.target === toolEditModalOverlay) hideToolEditModal();
    });
  }

  if (toolEditForm) {
    toolEditForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const serverName = document.getElementById('tool-edit-server-name').value;
      const toolName = document.getElementById('tool-edit-tool-name').value;
      const customName = document.getElementById('tool-edit-custom-name').value.trim();
      const customDescription = document.getElementById('tool-edit-custom-desc').value.trim();

      if (await updateToolMeta(serverName, toolName, customName, customDescription)) {
        hideToolEditModal();
        await fetchToolsConfig();
        renderMcpTools();
      } else {
        alert('Failed to update tool metadata');
      }
    });
  }

  if (toolResetBtn) {
    toolResetBtn.addEventListener('click', async () => {
      const serverName = document.getElementById('tool-edit-server-name').value;
      const toolName = document.getElementById('tool-edit-tool-name').value;

      if (await resetToolMeta(serverName, toolName)) {
        hideToolEditModal();
        await fetchToolsConfig();
        renderMcpTools();
      } else {
        alert('Failed to reset tool metadata');
      }
    });
  }
}

// Tab Switching
function switchTab(tab) {
  window.appState.currentTab = tab;
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.tab === tab);
  });
  document.querySelectorAll('.tab-content').forEach(content => {
    content.classList.add('hidden');
  });
  document.getElementById(`${tab}-tab`).classList.remove('hidden');

  // Update button visibility
  window.appState.dom.addEndpointBtn.style.display = tab === 'endpoints' ? '' : 'none';

  // Add MCP server button if on MCP tab
  let addMcpBtn = document.getElementById('add-mcp-server-btn');
  if (!addMcpBtn) {
    addMcpBtn = document.createElement('button');
    addMcpBtn.id = 'add-mcp-server-btn';
    addMcpBtn.className = 'btn btn-primary';
    addMcpBtn.innerHTML = '<span class="icon">+</span> Add Server';
    addMcpBtn.onclick = () => showMcpServerModal('Add MCP Server');
    window.appState.dom.addEndpointBtn.parentNode.insertBefore(addMcpBtn, window.appState.dom.addEndpointBtn);
  }
  addMcpBtn.style.display = tab === 'mcp-servers' ? '' : 'none';

  // Manage status polling for endpoints tab
  if (tab === 'endpoints') {
    startStatusPolling();
  } else {
    stopStatusPolling();
  }

  // Load tools when switching to MCP Tools tab
  if (tab === 'mcp-tools') {
    if (typeof fetchMcpTools === 'function') {
      fetchMcpTools();
    }
  }
}

// Modal Functions
function showModal(title = 'Add Endpoint', endpoint = null) {
  const { dom } = window.appState;
  dom.modalTitle.textContent = title;

  if (endpoint) {
    document.getElementById('endpoint-id').value = endpoint.id;
    document.getElementById('endpoint-name').value = endpoint.name;
    document.getElementById('endpoint-url').value = endpoint.url;
    document.getElementById('endpoint-enabled').checked = endpoint.enabled === 1;
  } else {
    document.getElementById('endpoint-id').value = '';
    document.getElementById('endpoint-name').value = '';
    document.getElementById('endpoint-url').value = '';
    document.getElementById('endpoint-enabled').checked = true;
  }

  dom.modalOverlay.classList.remove('hidden');
}

function showDeleteModal(id, name) {
  window.appState.deleteTargetId = id;
  window.appState.dom.deleteEndpointName.textContent = name;
  window.appState.dom.deleteModalOverlay.classList.remove('hidden');
}
