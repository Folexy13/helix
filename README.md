# 🧬 Helix — Intelligence That Spirals Forward

> *From idea to deployed product, with an entire AI founding team behind you.*

[![Amazon Nova](https://img.shields.io/badge/Powered%20by-Amazon%20Nova-orange)](https://aws.amazon.com/bedrock/nova/)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## What is Helix?

Helix is an AI-powered platform that gives any developer or entrepreneur a complete, autonomous team of intelligent agents that can **think about their business**, **build their software**, and **understand their codebase** — all in one unified system.

The name **Helix** reflects the core philosophy: like a double helix, two strands — human and AI — spiral forward together. Neither works without the other. You bring the vision and the decisions. Helix brings the team and the execution.

---

## 🏗️ The Three Pillars

### Pillar 1: The Founding Team 🚀
*AI Startup Co-Founder*

When you describe your startup idea, Helix assembles a virtual founding team:

| Agent | Role | Specialty |
|-------|------|-----------|
| **ARIA** | CTO | Technical feasibility, architecture, tech stack |
| **FELIX** | CFO | Financial projections, burn rate, runway |
| **NOVA** | CMO | Marketing strategy, landing page copy, positioning |
| **JUDGE** | Investor | Critical evaluation, fundability score |
| **ROUTER** | Orchestrator | Coordinates all agents, synthesizes brief |

**Output:** A comprehensive **Helix Startup Brief** with technical architecture, financial projections, marketing strategy, and investor feedback.

### Pillar 2: The Engineering Workforce 🔧
*Autonomous Coding Agents*

Describe a feature in plain English, and Helix deploys an engineering team:

| Agent | Role | Specialty |
|-------|------|-----------|
| **PLANNER** | Architect | Decomposes requests into engineering specs |
| **CODER** | Developer | Writes production-ready code |
| **TESTER** | QA | Creates and validates tests |
| **DOCS** | Technical Writer | Documentation and changelogs |
| **REVIEWER** | Senior Engineer | Security, performance, code quality |
| **ORCHESTRATOR** | Tech Lead | Coordinates the full pipeline |

**Output:** Code + Tests + Documentation + Review Report + **Live GitHub PR** (via Nova Act)

### Pillar 3: Codebase Intelligence 🧠
*Ask Your Codebase*

Connect your GitHub repository and have natural conversations about your code:

| Agent | Role | Specialty |
|-------|------|-----------|
| **SAGE** | Senior Engineer | Patient, grounded answers about your codebase |

**Capabilities:**
- "Where is authentication handled?"
- "What will break if I delete this file?"
- "Explain the data flow from API to database"
- Upload error screenshots for multimodal analysis

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend** | Python 3.10+ |
| **Agent Orchestration** | Strands Agents SDK pattern |
| **Reasoning Model** | Amazon Nova 2 Lite |
| **Voice Model** | Amazon Nova 2 Sonic |
| **UI Automation** | Amazon Nova Act |
| **Embeddings / RAG** | Amazon Nova Multimodal Embeddings |
| **Infrastructure** | AWS (Amazon Bedrock) |

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10 or higher
- AWS account with Bedrock access
- AWS credentials configured

### Installation

```bash
# Clone the repository
git clone https://github.com/your-org/helix.git
cd helix

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Edit .env with your AWS credentials
```

### Configuration

Edit `.env` with your settings:

```env
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key

# Optional: GitHub integration
GITHUB_TOKEN=your_github_token
```

### Usage

```bash
# Pillar 1: Analyze a startup idea
python -m src.main startup "An AI-powered code review tool"

# Pillar 2: Build a feature
python -m src.main build "Add user authentication with OAuth"

# Pillar 3: Ask about your codebase
python -m src.main ask "Where is the database connection configured?" --repo ./my-project

# Interactive mode
python -m src.main interactive

# Show version
python -m src.main version
```

---

## 🎯 Human-in-the-Loop (HITL) Design

Helix is **NOT** fully autonomous. Every major decision requires explicit human approval:

### Pillar 1 Gates
- **Gate 1.1**: Idea clarification before analysis
- **Gate 1.2**: Review each agent's draft
- **Gate 1.3**: Approve final Startup Brief

### Pillar 2 Gates
- **Gate 2.1**: Task intake clarification
- **Gate 2.2**: Approve engineering spec
- **Gate 2.3**: Mid-task interruption
- **Gate 2.4**: Resolve reviewer flags
- **Gate 2.5**: Approve final package

### Pillar 3 Gates
- **Gate 3.1**: Confirm files to index
- **Gate 3.2**: Approve re-indexing
- **Gate 3.3**: Clarification when uncertain
- **Gate 3.4**: Confirm context sharing

---

## 🎤 Voice-First Experience

Helix uses **Nova 2 Sonic** as the primary interaction layer:

- **Bidirectional streaming**: Natural conversation flow
- **Turn-taking**: Configurable voice activity detection
- **Crossmodal**: Switch between voice and text seamlessly
- **Distinct voices**: Each agent has a unique voice persona
- **Async tool use**: Conversation continues while agents process

---

## 📁 Project Structure

```
helix/
├── src/
│   ├── agents/
│   │   ├── pillar1/          # Founding Team agents
│   │   │   ├── aria.py       # CTO Agent
│   │   │   ├── felix.py      # CFO Agent
│   │   │   ├── nova_cmo.py   # CMO Agent
│   │   │   ├── judge.py      # Investor Agent
│   │   │   └── router.py     # Orchestrator
│   │   ├── pillar2/          # Engineering Workforce
│   │   │   ├── planner.py    # Planning Agent
│   │   │   ├── coder.py      # Coding Agent
│   │   │   ├── tester.py     # Testing Agent
│   │   │   ├── docs.py       # Documentation Agent
│   │   │   ├── reviewer.py   # Review Agent
│   │   │   └── orchestrator.py
│   │   ├── pillar3/          # Codebase Intelligence
│   │   │   ├── sage.py       # SAGE Agent
│   │   │   ├── rag.py        # RAG System
│   │   │   └── indexer.py    # Codebase Indexer
│   │   └── base.py           # Base Agent class
│   ├── core/
│   │   ├── config.py         # Configuration
│   │   ├── models.py         # Data models
│   │   └── bedrock_client.py # AWS Bedrock client
│   ├── voice/
│   │   ├── sonic_client.py   # Nova 2 Sonic client
│   │   ├── voice_config.py   # Voice configurations
│   │   └── voice_session.py  # Voice session manager
│   ├── hitl/
│   │   ├── checkpoint_manager.py
│   │   └── handlers.py       # HITL handlers
│   └── main.py               # CLI entry point
├── tests/
├── requirements.txt
├── pyproject.toml
└── README.md
```

---

## 🏆 Amazon Nova Features Used

| Feature | Where Used | Why |
|---------|------------|-----|
| **Nova 2 Lite** | All agents | Fast, cost-effective reasoning |
| **Extended Thinking** | PLANNER, ARIA, REVIEWER | Deep reasoning for complex tasks |
| **Web Grounding** | FELIX (CFO) | Live pricing and market data |
| **Code Interpreter** | TESTER | Run and validate tests |
| **Nova 2 Sonic** | All voice interactions | Primary user interface |
| **Async Tool Use** | HITL checkpoints | Keep conversation alive |
| **Crossmodal** | All sessions | Voice ↔ text switching |
| **Nova Act** | GitHub PRs, repo browsing | Real browser automation |
| **Multimodal Embeddings** | Pillar 3 RAG | Code + images + diagrams |

---

## 🎬 Demo Flow (3 minutes)

1. **0:00-0:20**: User speaks startup idea → Nova 2 Sonic responds
2. **0:20-0:35**: ROUTER asks clarifying questions (HITL Gate 1.1)
3. **0:35-1:00**: ARIA, FELIX, NOVA, JUDGE speak their analysis
4. **1:00-1:15**: User pushes back on FELIX → revision with web grounding
5. **1:15-1:30**: "Build authentication module" → PLANNER creates spec
6. **1:30-1:45**: User approves spec → CODER runs with RAG context
7. **1:45-2:05**: REVIEWER flags issue → user fixes → Nova Act creates PR
8. **2:05-2:40**: User uploads error screenshot → SAGE answers with multimodal
9. **2:40-3:00**: Dashboard showing all three pillars active

---

## 🤝 Contributing

Contributions are welcome! Please read our contributing guidelines before submitting PRs.

---

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

Built for the **Amazon Nova AI Hackathon, March 2026**.

Powered by:
- Amazon Nova 2 Lite
- Amazon Nova 2 Sonic
- Amazon Nova Act
- Amazon Nova Multimodal Embeddings
- Amazon Bedrock

---

*Helix — Intelligence That Spirals Forward.*
