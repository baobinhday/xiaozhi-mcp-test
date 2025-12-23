/**
 * UI Utilities Module
 * Helper functions for UI rendering and formatting
 */
import { elements } from './state.js';

// ============================================
// Tool Icons
// ============================================
export function getToolIcon(toolName) {
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

// ============================================
// Name Formatting
// ============================================
export function formatToolName(name) {
  return name
    .replace(/_/g, ' ')
    .replace(/([a-z])([A-Z])/g, '$1 $2')
    .split(' ')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ');
}

export function formatFieldName(name) {
  return name
    .replace(/_/g, ' ')
    .replace(/([a-z])([A-Z])/g, '$1 $2')
    .split(' ')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ');
}

// ============================================
// HTML Escaping
// ============================================
export function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

export function parseMarkdownToHtml(mdString) {
  marked.setOptions({
    breaks: true,        // Convert \n to <br>
    gfm: true,          // GitHub Flavored Markdown
    headerIds: false,    // Don't add IDs to headers
    mangle: false,       // Don't mangle email addresses
  });

  // Parse markdown to HTML
  const htmlContent = marked.parse(mdString);
  return htmlContent;
}

export const parseTextFromMarkDown = (mdString) => {
  const plainText = marked.parse(mdString, {
    renderer: plainTextRenderer()
  });
  return plainText;
}

export function escapeForJs(text) {
  return text
    .replace(/\\/g, '\\\\')
    .replace(/`/g, '\\`')
    .replace(/"/g, '\\"')
    .replace(/\$/g, '\\$')
    .replace(/\n/g, '\\n')
    .replace(/\r/g, '\\r');
}

// ============================================
// Loading State
// ============================================
export function showLoading(message = 'Executing tool...') {
  let overlay = elements.responsePanel.querySelector('.loading-overlay');
  if (!overlay) {
    overlay = document.createElement('div');
    overlay.className = 'loading-overlay absolute inset-0 bg-[#0f0f14]/80 backdrop-blur-sm flex flex-col items-center justify-center z-10 rounded-2xl animate-in fade-in duration-200';
    overlay.innerHTML = `
      <div class="loading-spinner w-10 h-10 border-4 border-indigo-500/30 border-t-indigo-500 rounded-full animate-spin mb-3"></div>
      <div class="loading-text text-zinc-200 text-sm font-medium animate-pulse">${message}</div>
    `;
    elements.responsePanel.appendChild(overlay);
  } else {
    overlay.querySelector('.loading-text').textContent = message;
  }
}

export function hideLoading() {
  const overlay = elements.responsePanel.querySelector('.loading-overlay');
  if (overlay) {
    overlay.remove();
  }
}

// ============================================
// Response Display
// ============================================
export function displayResponse(data) {
  const html = syntaxHighlightJSON(data);
  elements.responseContent.innerHTML = `<div class="json-viewer max-h-[calc(100vh-148px)] md:max-h-[calc(100vh-600px)] font-mono text-sm leading-relaxed whitespace-pre-wrap break-words">${html}</div>`;
}

export function clearResponse() {
  elements.responseContent.innerHTML = `
    <div class="empty-state flex flex-col items-center justify-center h-full text-zinc-500 gap-4 min-h-[200px]">
      <span class="empty-icon text-4xl opacity-50">📭</span>
      <p class="text-sm">Execute a tool to see results here</p>
    </div>
  `;
}

export function displayRequest(data, tool = null) {
  let contentHtml = '';

  if (tool) {
    // Tool information section
    contentHtml = `
      <div class="tool-info mb-4 pb-4 border-b border-white/10">
        <div class="flex items-center gap-2 mb-2">
          <span class="text-2xl">${getToolIcon(tool.name)}</span>
          <h3 class="text-lg font-semibold text-zinc-100">${formatToolName(tool.name)}</h3>
        </div>
        <p class="text-xs text-zinc-500 font-mono mb-2">${escapeHtml(tool.name)}</p>
        ${tool.description ? `<p class="text-sm text-zinc-400 leading-relaxed">${escapeHtml(tool.description)}</p>` : ''}
      </div>
      
      <div class="input-schema mb-4 pb-4 border-b border-white/10">
        <h4 class="text-sm font-semibold text-zinc-300 mb-2">📋 Input Schema</h4>
        <div class="json-viewer font-mono text-xs leading-relaxed whitespace-pre-wrap break-words bg-[#1c1c26] p-3 rounded-lg overflow-auto max-h-[200px]">${syntaxHighlightJSON(tool.inputSchema || {})}</div>
      </div>
      
      <div class="request-arguments">
        <h4 class="text-sm font-semibold text-zinc-300 mb-2">📤 Request Arguments</h4>
        <div class="json-viewer font-mono text-sm leading-relaxed whitespace-pre-wrap break-words bg-[#1c1c26] p-3 rounded-lg">${syntaxHighlightJSON(data)}</div>
      </div>
    `;
  } else {
    // Fallback: just show arguments
    contentHtml = `<div class="json-viewer max-h-[calc(100vh-148px)] md:max-h-[calc(100vh-600px)] font-mono text-sm leading-relaxed whitespace-pre-wrap break-words">${syntaxHighlightJSON(data)}</div>`;
  }

  elements.requestContent.innerHTML = `<div class="request-display max-h-[calc(100vh-148px)] md:max-h-[calc(100vh-600px)] overflow-y-auto">${contentHtml}</div>`;
}

export function clearRequest() {
  elements.requestContent.innerHTML = `
    <div class="empty-state flex flex-col items-center justify-center h-full text-zinc-500 gap-4 min-h-[200px]">
      <span class="empty-icon text-4xl opacity-50">📤</span>
      <p class="text-sm">Execute a tool to see request parameters here</p>
    </div>
  `;
}

export function syntaxHighlightJSON(obj) {
  const json = JSON.stringify(obj, null, 2);
  return json.replace(
    /("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g,
    (match) => {
      let cls = 'text-amber-400';
      if (/^"/.test(match)) {
        if (/:$/.test(match)) {
          cls = 'text-purple-400';
        } else {
          cls = 'text-green-400';
        }
      } else if (/true|false/.test(match)) {
        cls = 'text-pink-400';
      } else if (/null/.test(match)) {
        cls = 'text-slate-500';
      }
      return `<span class="${cls}">${escapeHtml(match)}</span>`;
    }
  );
}

// ============================================
// Logging
// ============================================
export function log(type, message) {
  const time = new Date().toLocaleTimeString('en-US', { hour12: false });
  const entry = document.createElement('div');

  const typeClasses = {
    'info': 'border-blue-500 bg-blue-500/5 text-blue-400',
    'success': 'border-green-500 bg-green-500/5 text-green-400',
    'warning': 'border-yellow-500 bg-yellow-500/5 text-yellow-400',
    'error': 'border-red-500 bg-red-500/5 text-red-400',
    'sent': 'border-indigo-500 bg-indigo-500/5 text-indigo-400',
    'received': 'border-violet-500 bg-violet-500/5 text-violet-400'
  };

  const colorClass = typeClasses[type] || typeClasses['info'];

  entry.className = `log-entry flex gap-3 p-2 hover:bg-white/5 rounded-md mb-1 border-l-2 transition-colors ${colorClass}`;
  entry.innerHTML = `
    <span class="log-time opacity-60 text-xs font-mono flex-shrink-0 pt-[2px]">${time}</span>
    <span class="log-message font-mono text-xs break-all">${escapeHtml(message)}</span>
  `;

  elements.logContent.appendChild(entry);
  elements.logContent.scrollTop = elements.logContent.scrollHeight;
}

export function clearLogs() {
  elements.logContent.innerHTML = '';
  log('info', 'Logs cleared');
}

export function plainTextRenderer(options = {}) {
  const render = new marked.Renderer();

  const whitespaceDelimiter = options?.spaces ? ' ' : '\n';

  // render just the text of a link
  render.link = function (href, title, text) {
    return text;
  };

  // render just the text of a paragraph
  render.paragraph = function (text) {
    return whitespaceDelimiter + text + whitespaceDelimiter
  };

  // render just the text of a heading element, but indecate level
  render.heading = function (text) {
    return text;
  };

  // render nothing for images
  render.image = function () {
    return '';
  };

  render.list = function (body) {
    return body;
  };

  render.listitem = function (text) {
    return '\t' + text + whitespaceDelimiter;
  };

  render.hr = function () {
    return whitespaceDelimiter + whitespaceDelimiter;
  };

  render.table = function (header, body) {
    return whitespaceDelimiter + header + whitespaceDelimiter + body + whitespaceDelimiter;
  };

  render.tablerow = function (content) {
    return content + whitespaceDelimiter;
  };

  render.tablecell = function (content, flags) {
    return content + '\t';
  };

  render.strong = function (text) {
    return text;
  };

  render.em = function (text) {
    return text;
  };

  render.codespan = function (text) {
    return text;
  };

  render.code = function (code) {
    return this.whitespaceDelimiter + this.whitespaceDelimiter + code + this.whitespaceDelimiter + this.whitespaceDelimiter;
  };

  render.br = function () {
    return whitespaceDelimiter + whitespaceDelimiter;
  };

  render.del = function (text) {
    return text;
  };

  render.blockquote = function (quote) {
    return '\t' + quote + this.whitespaceDelimiter;
  };

  render.html = function (html) {
    return html;
  };

  return render;
}