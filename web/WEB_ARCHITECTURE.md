# Web Architecture

This document describes the architecture of the web interface for the MCP Tools Tester application.

## Overview

The web interface is a single-page application (SPA) that provides:
- **WebSocket connection** to the MCP hub for tool discovery and execution
- **Tool testing UI** with dynamic form generation based on tool schemas
- **Chat interface** with LLM integration supporting function calling
- **Text-to-Speech** playback for assistant responses

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              Browser (index.html)                               │
├─────────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────┐  ┌───────────────────────┐  │
│  │   app.js    │  │  state.js    │  │ ui-utils.js │  │      tabs.js          │  │
│  │  (Entry)    │  │  (State)     │  │ (Rendering) │  │ (Tab Management)      │  │
│  └──────┬──────┘  └──────────────┘  └─────────────┘  └───────────────────────┘  │
│         │                                                                       │
│  ┌──────┴─────────────────────────────────────────────────────────────────────┐ │
│  │                        Core Modules                                        │ │
│  │  ┌──────────────┐  ┌────────────────┐  ┌───────────────┐  ┌─────────────┐  │ │
│  │  │ websocket.js │  │ mcp-protocol.js│  │   tools.js    │  │ settings.js │  │ │
│  │  │ (Connection) │  │  (JSON-RPC)    │  │ (Tool Forms)  │  │  (Config)   │  │ │
│  │  └──────────────┘  └────────────────┘  └───────────────┘  └─────────────┘  │ │
│  └────────────────────────────────────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────┐  ┌───────────────────────────────────┐ │
│  │           chat-api.js               │  │             tts.js                │ │
│  │  (LLM Chat + Tool Calling)          │  │    (Text-to-Speech API)           │ │
│  └─────────────────────────────────────┘  └───────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────────┘
                                    ▲
                                    │ WebSocket (ws://localhost:8889)
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            server.py (WebSocket Hub)                            │
│                                                                                 │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                         WebSocketHub Class                               │   │
│  │  - browser_clients: Browser connections                                  │   │
│  │  - mcp_tools: MCP server connections                                     │   │
│  │  - tools_cache: Aggregated tools from all MCP servers                    │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  HTTP Server (localhost:8888)          WebSocket Server (localhost:8889)        │
│  └─ Serves static files                └─ /mcp endpoint for MCP pipes          │
│                                         └─ Browser client connections           │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## File Structure

```
web/
├── index.html          # Main HTML page with UI structure
├── app.js              # Entry point, initializes all modules
├── server.py           # WebSocket hub server (Python)
├── style.css           # Primary styles (TailwindCSS)
├── common.css          # Shared component styles
└── js/
    ├── state.js        # Global state and DOM references
    ├── websocket.js    # WebSocket connection management
    ├── mcp-protocol.js # MCP JSON-RPC protocol handling
    ├── tools.js        # Tool discovery and form rendering
    ├── chat-api.js     # LLM chat integration with tool calling
    ├── settings.js     # Settings modal and configuration
    ├── tts.js          # Text-to-Speech API integration
    ├── tabs.js         # Tab switching (Response/Request/Chat)
    └── ui-utils.js     # UI helpers (formatting, logging, etc.)
```

## Backend Server (`server.py`)

### WebSocketHub Class

The hub manages WebSocket connections between browser clients and MCP tool pipes:

| Method | Purpose |
|--------|---------|
| `register_browser()` | Register incoming browser connections |
| `register_mcp()` | Register MCP tool pipe connections |
| `forward_to_mcp()` | Route browser requests to appropriate MCP server |
| `forward_to_browsers()` | Broadcast MCP responses to all browsers |
| `handle_browser_message()` | Intercept and process browser messages |
| `handle_mcp_message()` | Cache tool lists from MCP servers |
| `get_cached_aggregated_tools()` | Return merged tools from all MCP servers |

### Endpoints

| Port | Protocol | Purpose |
|------|----------|---------|
| 8888 | HTTP | Static file server for web interface |
| 8889 | WebSocket | MCP hub (`/mcp` for pipes, `/` for browsers) |

---

## Frontend Modules

### `state.js` - State Management

Central state store holding:
- `websocket`: Current WebSocket connection
- `isConnected`, `mcpConnected`: Connection status
- `tools[]`: Available MCP tools
- `chatHistory[]`: Chat conversation messages
- `chatSettings{}`: LLM API configuration (baseUrl, token, model, etc.)

### `websocket.js` - Connection Management

| Function | Purpose |
|----------|---------|
| `initConnectionHandler()` | Setup connect button listener |
| `connect()` | Establish WebSocket connection to hub |
| `disconnect()` | Close WebSocket connection |
| `updateConnectionUI()` | Update UI status indicators |

### `mcp-protocol.js` - MCP Protocol

Implements JSON-RPC 2.0 protocol for MCP communication:

| Function | Purpose |
|----------|---------|
| `sendRequest()` | Send JSON-RPC request with promise handling |
| `handleMessage()` | Parse and route incoming messages |
| `sendInitialize()` | Initialize MCP session handshake |
| `sendNotification()` | Send one-way notifications |

### `tools.js` - Tool UI

Dynamic tool interface generation:

| Function | Purpose |
|----------|---------|
| `fetchTools()` | Request tools list from hub |
| `renderToolsList()` | Generate sidebar tool buttons |
| `renderToolForm()` | Build input form from tool schema |
| `executeSelectedTool()` | Execute tool with form parameters |
| `collectFormArguments()` | Gather typed form values |

### `chat-api.js` - LLM Chat Integration

Full-featured chat with function calling:

| Function | Purpose |
|----------|---------|
| `initChatHandler()` | Setup chat input handlers |
| `sendChatMessage()` | Send user message to chat |
| `callChatAPI()` | Make LLM API request |
| `sendChatRequest()` | Stream LLM response with tool calls |
| `executeToolForChat()` | Execute MCP tool during chat |
| `buildToolsForAPI()` | Convert MCP tools to OpenAI function format |
| `regenerateResponse()` | Re-generate last assistant message |
| `editUserMessage()` | Edit and resubmit user message |

### `settings.js` - Configuration Modal

Settings management for LLM API:

| Function | Purpose |
|----------|---------|
| `openSettingsModal()` | Display settings dialog |
| `saveSettings()` | Persist settings to localStorage |
| `fetchModels()` | Fetch available models from API |
| `toggleCustomToolsPanel()` | Toggle custom tool selection |

### `tts.js` - Text-to-Speech

Audio playback using external TTS API:

| Function | Purpose |
|----------|---------|
| `fetchVoices()` | Load available voices from API |
| `speakText()` | Convert text to speech and play |
| `setTtsVoice()` | Change selected voice |

### `tabs.js` - Tab Navigation

Simple tab switching between Response/Request/Chat views:

| Function | Purpose |
|----------|---------|
| `initTabHandler()` | Setup tab click handlers |
| `switchTab()` | Toggle active tab content |

### `ui-utils.js` - Utilities

Helper functions for UI rendering:

| Function | Purpose |
|----------|---------|
| `getToolIcon()` | Return emoji icon for tool type |
| `formatToolName()` | Convert snake_case to Title Case |
| `escapeHtml()` | Sanitize HTML special characters |
| `parseMarkdownToHtml()` | Render markdown content |
| `showLoading()` / `hideLoading()` | Loading overlay management |
| `displayResponse()` | Show tool execution results |
| `log()` | Add log entries to log panel |
| `syntaxHighlightJSON()` | Colorize JSON for display |

---

## UI Components

### Main Layout

```
┌────────────────────────────────────────────────────────────────┐
│ Header: Brand, WebSocket Endpoint, Connect Button, Status      │
├─────────┬──────────────────┬───────────────────────────────────┤
│ Sidebar │   Tool Form      │   Response Panel                  │
│ (Tools) │   - Parameters   │   [Response] [Request] [Chat]     │
│         │   - Execute Btn  │   ─────────────────────────────   │
│         │                  │   Content / Chat Messages         │
│         │                  │   ─────────────────────────────   │
│         │                  │   Input (Chat mode only)          │
└─────────┴──────────────────┴───────────────────────────────────┘
```

### Tab Views

| Tab | Content |
|-----|---------|
| **Response** | JSON output from tool execution |
| **Request** | JSON request parameters sent to tool |
| **Chat** | LLM conversation with tool calling |

---

## Data Flow

### Tool Execution Flow

```
1. User selects tool → renderToolForm()
2. User fills parameters → collectFormArguments()
3. User clicks Execute → executeSelectedTool()
4. JSON-RPC request via sendRequest() → WebSocket
5. Hub forwards to MCP pipe → MCP Server
6. Response bubbles back → handleMessage()
7. Results displayed → displayResponse()
```

### Chat with Tool Calling Flow

```
1. User types message → sendChatMessage()
2. Build messages array → callChatAPI()
3. LLM returns tool_calls → sendChatRequest() parses stream
4. Execute each tool → executeToolForChat() via MCP
5. Tool results added to messages
6. Continue LLM request with results
7. Final response displayed with TTS option
```

---

## External Dependencies

| Library | Source | Purpose |
|---------|--------|---------|
| TailwindCSS | CDN | Utility-first CSS framework |
| Google Fonts | CDN | Inter + JetBrains Mono fonts |
| marked.js | CDN | Markdown to HTML parser |
| highlight.js | CDN | Code syntax highlighting |

## External APIs

| API | Endpoint | Purpose |
|-----|----------|---------|
| TTS API | `https://ttsapi.site/v1/audio/speech` | Text-to-Speech synthesis |
| Voices API | `https://ttsapi.site/api/voices` | Available TTS voices list |
| LLM API | Configurable (OpenAI-compatible) | Chat completions with function calling |
