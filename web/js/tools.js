/**
 * Tools Module
 * Tool loading, rendering, and execution
 */

// ============================================
// No Tools Message
// ============================================
function showNoToolsMessage() {
  elements.toolNav.innerHTML = `
    <div class="no-tools-message flex flex-col items-center justify-center p-6 text-center text-zinc-500">
      <span class="no-tools-icon text-4xl mb-3 opacity-50">🔌</span>
      <p class="text-sm">Connect to MCP server to see available tools</p>
    </div>
  `;
  elements.toolPanel.innerHTML = `
    <div class="empty-state flex flex-col items-center justify-center h-full min-h-[200px] text-zinc-500 gap-4">
      <span class="empty-icon text-4xl opacity-50">🔧</span>
      <p class="text-sm">No tools available. Connect to an MCP server first.</p>
    </div>
  `;
}

// ============================================
// Fetch Tools
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

// ============================================
// Tool Selection
// ============================================
function selectTool(index) {
  state.selectedToolIndex = index;

  elements.toolNav.querySelectorAll('.tool-btn').forEach((btn, i) => {
    btn.classList.toggle('active', i === index);
  });

  const tool = state.tools[index];
  if (tool) {
    renderToolForm(tool);
    log('info', `Selected tool: ${tool.name}`);
  }
}

// ============================================
// Render Tools List
// ============================================
function renderToolsList(tools) {
  elements.toolNav.innerHTML = tools.map((tool, index) => `
    <button class="tool-btn w-full flex flex-row items-start gap-2 p-3 rounded-lg hover:bg-[#1c1c26] transition-all text-left group ${index === 0 ? 'active' : ''}" data-tool-index="${index}">
      <span class="tool-icon text-2xl mb-1">${getToolIcon(tool.name)}</span>
      <div class="flex flex-col gap-1">
        <span class="tool-name whitespace-pre-wrap break-all font-medium text-sm text-zinc-200 group-hover:text-indigo-400 transition-colors">${formatToolName(tool.name)}</span>
        <span class="tool-desc whitespace-pre-wrap break-all font-mono text-[10px] text-zinc-500 truncate w-full">${tool.name}</span>
      </div>
    </button>
  `).join('');

  elements.toolNav.querySelectorAll('.tool-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const index = parseInt(btn.dataset.toolIndex);
      selectTool(index);
    });
  });
}

// ============================================
// Render Tool Form
// ============================================
function renderToolForm(tool) {
  const inputSchema = tool.inputSchema || {};
  const properties = inputSchema.properties || {};
  const required = inputSchema.required || [];

  let formHtml = `
    <div class="tool-form active animate-in fade-in slide-in-from-bottom-2 duration-300" id="tool-form-${tool.name}">
      <div class="tool-header mb-6">
        <h2 class="text-xl font-semibold mb-2 flex items-center gap-2 text-zinc-100">
          <span class="text-2xl">${getToolIcon(tool.name)}</span> 
          ${formatToolName(tool.name)}
        </h2>
        <p class="text-sm text-zinc-400 leading-relaxed whitespace-pre-wrap">${tool.description || 'No description available'}</p>
      </div>
  `;

  for (const [propName, propSchema] of Object.entries(properties)) {
    const isRequired = required.includes(propName);
    const fieldId = `field-${tool.name}-${propName}`;

    formHtml += `
      <div class="form-group mb-4">
        <label for="${fieldId}" class="block text-sm font-medium text-zinc-400 mb-2">
          ${formatFieldName(propName)}
          ${isRequired ? '<span class="text-red-500 ml-1">*</span>' : ''}
        </label>
        ${renderFormField(fieldId, propName, propSchema)}
        ${propSchema.description ? `<small class="block mt-1 text-xs text-zinc-500">${propSchema.description}</small>` : ''}
      </div>
    `;
  }

  formHtml += `
      <button class="btn btn-execute w-full mt-6 py-3 px-6 bg-gradient-to-br from-indigo-500 to-violet-500 text-white text-base rounded-lg font-medium hover:shadow-lg hover:shadow-indigo-500/20 hover:-translate-y-px transition-all flex items-center justify-center gap-2 cursor-pointer" onclick="executeSelectedTool()">
        <span class="btn-icon">▶</span>
        Execute ${formatToolName(tool.name)}
      </button>
    </div>
  `;

  elements.toolPanel.innerHTML = formHtml;
}

// ============================================
// Render Form Field
// ============================================
function renderFormField(id, name, schema) {
  const type = schema.type || 'string';
  const defaultValue = schema.default !== undefined ? schema.default : '';
  const baseInputClass = "w-full px-4 py-2.5 bg-[#1c1c26] border border-white/10 rounded-lg text-zinc-200 text-sm focus:outline-none focus:border-indigo-500/50 focus:shadow-[0_0_20px_rgba(99,102,241,0.2)] transition-all placeholder:text-zinc-600";

  switch (type) {
    case 'integer':
    case 'number':
      return `<input type="number" id="${id}" data-param="${name}" 
        value="${defaultValue}" 
        ${schema.minimum !== undefined ? `min="${schema.minimum}"` : ''} 
        ${schema.maximum !== undefined ? `max="${schema.maximum}"` : ''} 
        class="${baseInputClass} max-w-[150px]">`;

    case 'boolean':
      return `<select id="${id}" data-param="${name}" class="${baseInputClass} max-w-[150px]">
        <option value="true" ${defaultValue === true ? 'selected' : ''}>True</option>
        <option value="false" ${defaultValue === false ? 'selected' : ''}>False</option>
      </select>`;

    case 'array':
      return `<textarea id="${id}" data-param="${name}" 
        placeholder="Enter values separated by newlines or as JSON array" 
        class="${baseInputClass} font-mono min-h-[100px] resize-y">${defaultValue}</textarea>`;

    case 'object':
      return `<textarea id="${id}" data-param="${name}" 
        placeholder="Enter JSON object" 
        class="${baseInputClass} font-mono min-h-[100px] resize-y">${JSON.stringify(defaultValue || {}, null, 2)}</textarea>`;

    default:
      if (schema.enum) {
        return `<select id="${id}" data-param="${name}" class="${baseInputClass}">
          ${schema.enum.map(opt => `<option value="${opt}" ${opt === defaultValue ? 'selected' : ''}>${opt}</option>`).join('')}
        </select>`;
      }
      return `<input type="text" id="${id}" data-param="${name}" 
        value="${defaultValue}" 
        placeholder="${schema.description || `Enter ${formatFieldName(name)}...`}" 
        class="${baseInputClass}">`;
  }
}

// ============================================
// Execute Tool
// ============================================
function executeSelectedTool() {
  const tool = state.tools[state.selectedToolIndex];
  if (!tool) {
    log('error', 'No tool selected');
    return;
  }

  const args = collectFormArguments(tool);
  if (args === null) return;

  log('info', `Executing: ${tool.name}`);
  displayRequest(args, tool);
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

// ============================================
// Collect Form Arguments
// ============================================
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

    if (value === '' && required.includes(propName)) {
      log('error', `${formatFieldName(propName)} is required`);
      element.focus();
      return null;
    }

    if (value === '') continue;

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
