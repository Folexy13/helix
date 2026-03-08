# Helix Frontend Architecture Design

## Overview

The Helix frontend serves as a real-time, interactive dashboard complementing the CLI interface. It provides visual orchestration of the multi-agent system, offering deep insights into active pipelines, intelligent parsing of agent outputs, and seamless interaction for Human-in-the-Loop (HITL) checkpoints. 

The aesthetic is developer-focused: dark mode default, clean typography, syntax highlighting, and a layout that prioritizes information density without feeling cluttered.

## Tech Stack

*   **Framework:** React 18+ with Next.js (App Router) for hybrid rendering (SSR/CSR).
*   **State Management:** Zustand for global state, React Query for server state/caching.
*   **Styling:** Tailwind CSS combined with shadcn/ui for rapid, consistent component design.
*   **Real-time Communication:** Socket.io-client for WebSocket connections to the backend.
*   **Syntax Highlighting:** Prism.js or Shiki for rendering code blocks with custom themes.
*   **Markdown Parsing:** React-Markdown with custom renderers for intelligent agent comment parsing.
*   **Visualization:** Framer Motion for smooth transitions, React Flow for dynamic pipeline node visualization.

## Core Architectural Components

### 1. Global State Management (Zustand)

Manages the core application state, ensuring all components react instantly to backend updates.

*   `useSessionStore`: Tracks active sessions, selected pillar, and overall system status.
*   `usePipelineStore`: Manages the state of active agent pipelines, including current stage, agent handoffs, and operation logs.
*   `useHitlStore`: Tracks pending HITL checkpoints, available options, and user decisions.
*   `useVoiceStore`: Manages Nova 2 Sonic voice session state, active speaker, and transcription logs.

### 2. Real-time Communication Layer (WebSocket)

A dedicated custom hook (`useHelixSocket`) establishes a persistent connection to the Python backend (FastAPI + WebSockets).

*   **Events Received (Server -> Client):**
    *   `pipeline_update`: Stage changes, agent handoffs.
    *   `agent_log`: Real-time streaming of agent thoughts and actions.
    *   `hitl_checkpoint`: New checkpoint requiring user interaction.
    *   `voice_transcript`: Live transcription of voice input/output.
    *   `system_metrics`: CPU/Memory usage, token consumption.
*   **Events Emitted (Client -> Server):**
    *   `hitl_decision`: User approval, rejection, or edit payload.
    *   `start_pipeline`: Initiate a new workflow.
    *   `interrupt_pipeline`: Force pause or abort active execution.

### 3. Intelligent Parsing & Rendering Engine

Agent outputs (often Markdown or JSON) require specific rendering strategies.

*   **Code Block Renderer:** Custom component wrapping React-Markdown to detect code blocks, apply appropriate syntax highlighting (Shiki), and provide one-click "Copy" or "Open in Editor" actions.
*   **Semantic Categorization:** Parses agent logs to visually distinguish between "Thinking" (dimmed, italic), "Action" (bold, colored), and "Result" (standard text).
*   **Diff Viewer:** For the REVIEWER agent, renders code changes side-by-side or inline using a library like `react-diff-viewer`.

## UI Component Structure

### Main Layout (`/app/layout.tsx`)

*   **Sidebar:** Navigation between Pillars, active session list, global settings, and system metrics sparkline.
*   **Header:** Current project context, global voice toggle (Nova 2 Sonic), and user profile.
*   **Main Content Area:** Dynamic view based on the selected Pillar.
*   **Global Command Palette (Cmd+K):** Quick access to start new workflows or jump to specific agents.

### Key Views

#### 1. The Pipeline Visualizer (React Flow)
A dynamic node-graph representing the active workflow.
*   **Nodes:** Represent agents (e.g., PLANNER, CODER) or HITL gates.
*   **Edges:** Show data flow and dependencies.
*   **State:** Nodes glow or pulse when active. Checkpoint nodes turn orange when awaiting input.

#### 2. The Agent Log Stream (Terminal View)
A scrollable, terminal-like component showing live activity.
*   Intelligent coloring based on agent role (e.g., ARIA is blue, FELIX is green).
*   Expandable JSON payloads for deep inspection.
*   Auto-scroll toggle.

#### 3. The HITL Interaction Modal/Panel
When a checkpoint is reached, a focused UI component appears.
*   **Context:** Displays the agent's draft or the specific question.
*   **Diff View (if applicable):** Shows proposed code changes.
*   **Action Buttons:** Primary buttons for `Approve`, `Reject`, `Edit`.
*   **Input Field:** For providing clarification or specific edit instructions.

#### 4. Pillar-Specific Dashboards
*   **Pillar 1 (Founding Team):** Card-based layout displaying the evolving Startup Brief (Tech Stack, Financials, Marketing, Score).
*   **Pillar 2 (Engineering):** Split view: Pipeline on top, File Tree & Code Viewer on the bottom.
*   **Pillar 3 (Codebase SAGE):** Chat-interface style with deep links into the codebase file structure.

## API Contracts & Data Flow

### REST API (FastAPI)
For stateless operations and initial data fetching.
*   `GET /api/sessions`: List active/past sessions.
*   `POST /api/sessions`: Create a new session.
*   `GET /api/index/{repo}`: Get codebase index status.

### WebSocket Payload Examples

**Pipeline Update Payload:**
```json
{
  "type": "pipeline_update",
  "data": {
    "session_id": "uuid",
    "pillar": 2,
    "current_stage": "coding",
    "active_agent": "CODER",
    "progress_percent": 45
  }
}
```

**HITL Checkpoint Payload:**
```json
{
  "type": "hitl_checkpoint",
  "data": {
    "checkpoint_id": "uuid",
    "gate_type": "gate_2_4",
    "agent": "REVIEWER",
    "prompt": "Security vulnerability detected...",
    "options": ["fix", "ignore", "explain"],
    "context_diff": "...diff string..."
  }
}
```

## Integration with Existing CLI

The frontend is designed to be a companion, not a replacement. 

1.  **Headless Mode:** The CLI can run workflows independently.
2.  **Attached Mode:** Running `helix dashboard` launches the Next.js frontend, which immediately connects to the local backend daemon via WebSocket. 
3.  **Sync:** Any CLI command executed while the dashboard is open immediately reflects in the UI visualizer. HITL checkpoints triggered via CLI can be resolved via the UI, and vice versa.