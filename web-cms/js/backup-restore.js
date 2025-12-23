// Backup and Restore Module

// This module handles backup and restore functionality for:
// - Endpoints
// - MCP Servers
// - MCP Tools

// Initialize event listeners (called from main.js)
function initBackupRestoreListeners() {
  // === ENDPOINTS BACKUP/RESTORE ===
  const endpointsBackupBtn = document.getElementById('endpoints-backup-btn');
  const endpointsRestoreBtn = document.getElementById('endpoints-restore-btn');
  const endpointsRestoreInput = document.getElementById('endpoints-restore-file-input');

  if (endpointsBackupBtn) {
    endpointsBackupBtn.addEventListener('click', backupEndpoints);
  }

  if (endpointsRestoreBtn) {
    endpointsRestoreBtn.addEventListener('click', () => {
      endpointsRestoreInput.click();
    });
  }

  if (endpointsRestoreInput) {
    endpointsRestoreInput.addEventListener('change', restoreEndpoints);
  }

  // === MCP SERVERS BACKUP/RESTORE ===
  const mcpBackupBtn = document.getElementById('mcp-backup-btn');
  const mcpRestoreBtn = document.getElementById('mcp-restore-btn');
  const mcpRestoreInput = document.getElementById('mcp-restore-file-input');

  if (mcpBackupBtn) {
    mcpBackupBtn.addEventListener('click', backupMcpServers);
  }

  if (mcpRestoreBtn) {
    mcpRestoreBtn.addEventListener('click', () => {
      mcpRestoreInput.click();
    });
  }

  if (mcpRestoreInput) {
    mcpRestoreInput.addEventListener('change', restoreMcpServers);
  }

  // === TOOLS BACKUP/RESTORE ===
  const toolsBackupBtn = document.getElementById('tools-backup-btn');
  const toolsRestoreBtn = document.getElementById('tools-restore-btn');
  const toolsRestoreInput = document.getElementById('tools-restore-file-input');

  if (toolsBackupBtn) {
    toolsBackupBtn.addEventListener('click', backupTools);
  }

  if (toolsRestoreBtn) {
    toolsRestoreBtn.addEventListener('click', () => {
      toolsRestoreInput.click();
    });
  }

  if (toolsRestoreInput) {
    toolsRestoreInput.addEventListener('change', restoreTools);
  }
}

// Endpoints Backup/Restore
async function backupEndpoints() {
  try {
    const response = await apiRequest('/api/backup');
    if (response.ok) {
      const data = await response.json();
      downloadJSON(data, `mcp_endpoints_backup_${getDateString()}.json`);
    } else {
      alert('Failed to create backup');
    }
  } catch (error) {
    alert('Error creating backup: ' + error.message);
  }
}

async function restoreEndpoints(e) {
  const file = e.target.files[0];
  if (!file) return;

  try {
    const text = await file.text();
    const data = JSON.parse(text);

    if (!data.endpoints || !Array.isArray(data.endpoints)) {
      alert('Invalid backup file format');
      e.target.value = '';
      return;
    }

    const confirmMsg = `Are you sure you want to restore from backup?\\n\\nThis will replace all ${window.appState.endpoints.length} current endpoints with ${data.endpoints.length} endpoints from the backup file.\\n\\nThis action cannot be undone.`;

    if (!confirm(confirmMsg)) {
      e.target.value = '';
      return;
    }

    const response = await apiRequest('/api/restore', {
      method: 'POST',
      body: JSON.stringify({ endpoints: data.endpoints })
    });

    if (response.ok) {
      alert('Backup restored successfully!');
      await fetchEndpoints();
    } else {
      alert('Failed to restore backup');
    }
  } catch (error) {
    alert('Error restoring backup: ' + error.message);
  }

  e.target.value = '';
}

// MCP Servers Backup/Restore
async function backupMcpServers() {
  try {
    const response = await apiRequest('/api/mcp-config/backup');
    if (response.ok) {
      const data = await response.json();
      downloadJSON(data, `mcp_config_backup_${getDateString()}.json`);
    } else {
      alert('Failed to create backup');
    }
  } catch (error) {
    alert('Error creating backup: ' + error.message);
  }
}

async function restoreMcpServers(e) {
  const file = e.target.files[0];
  if (!file) return;

  try {
    const text = await file.text();
    const data = JSON.parse(text);

    if (!data.mcpServers) {
      alert('Invalid backup file format');
      e.target.value = '';
      return;
    }

    const serverCount = Object.keys(data.mcpServers).length;
    const confirmMsg = `Are you sure you want to restore from backup?\\n\\nThis will replace all ${window.appState.mcpServers.length} current MCP servers with ${serverCount} servers from the backup file.\\n\\nThis action cannot be undone.`;

    if (!confirm(confirmMsg)) {
      e.target.value = '';
      return;
    }

    const response = await apiRequest('/api/mcp-config/restore', {
      method: 'POST',
      body: JSON.stringify(data)
    });

    if (response.ok) {
      alert('Backup restored successfully! The application will reload.');
      window.location.reload();
    } else {
      alert('Failed to restore backup');
    }
  } catch (error) {
    alert('Error restoring backup: ' + error.message);
  }

  e.target.value = '';
}

// Tools Backup/Restore
async function backupTools() {
  try {
    const response = await apiRequest('/api/mcp-tools/backup');
    if (response.ok) {
      const data = await response.json();
      downloadJSON(data, `mcp_tools_backup_${getDateString()}.json`);
    } else {
      alert('Failed to create backup');
    }
  } catch (error) {
    alert('Error creating backup: ' + error.message);
  }
}

async function restoreTools(e) {
  const file = e.target.files[0];
  if (!file) return;

  try {
    const text = await file.text();
    const data = JSON.parse(text);

    if (!data.disabledTools) {
      alert('Invalid backup file format');
      e.target.value = '';
      return;
    }

    const disabledCount = Object.keys(data.disabledTools).length;
    const customCount = Object.keys(data.customTools || {}).length;
    const confirmMsg = `Are you sure you want to restore from backup?\\n\\nThis will replace all current tools configuration with the backup (${disabledCount} server(s) with disabled tools, ${customCount} server(s) with custom tools).\\n\\nThis action cannot be undone.`;

    if (!confirm(confirmMsg)) {
      e.target.value = '';
      return;
    }

    const response = await apiRequest('/api/mcp-tools/restore', {
      method: 'POST',
      body: JSON.stringify(data)
    });

    if (response.ok) {
      alert('Backup restored successfully! The application will reload.');
      window.location.reload();
    } else {
      alert('Failed to restore backup');
    }
  } catch (error) {
    alert('Error restoring backup: ' + error.message);
  }

  e.target.value = '';
}

// Helper Functions
function downloadJSON(data, filename) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

function getDateString() {
  return new Date().toISOString().split('T')[0];
}
