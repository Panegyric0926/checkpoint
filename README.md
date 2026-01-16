# AI Chat Agent with Time Travel

A demo application featuring a LangGraph-based chat agent with AI-powered checkpoint (time travel) functionality.

## Features

- **Multi-Session Support**: Each browser tab gets its own isolated chat session with unique session ID
- **Session Persistence**: Sessions persist within a tab (survives page refresh) with automatic cleanup after 60 minutes of inactivity
- **LangGraph Agent System**: Uses LangGraph for managing the agent workflow with checkpoint judge
- **AzureChatOpenAI**: Powered by Azure OpenAI's GPT models
- **Internet Search**: Tavily search integration for real-time web search
- **Message Editing & Branching**: Edit previously sent messages to create new conversation branches
- **AI-Powered Checkpoints**: AI judge automatically saves significant conversation moments
- **Manual Checkpoints**: Users can also save checkpoints manually at any time
- **Visual Distinction**: 🤖 AI checkpoints (blue) vs 👤 Manual checkpoints (green)
- **Smart Save Button**: Automatically disabled when AI has already saved
- **Langfuse Integration**: Prompt management and tracing for both main agent and checkpoint judge
- **Dash Frontend**: Clean web-based chat interface

## Project Structure

```
checkpoint/
├── app/
│   ├── __init__.py              # Package initialization
│   ├── agent.py                 # LangGraph agent with checkpoints
│   ├── checkpoint_judge_agent.py # AI checkpoint evaluation agent
│   ├── checkpoint_manager.py    # Checkpoint save/restore logic
│   ├── session_manager.py       # Multi-session management (per-tab agents)
│   ├── config.py                # Configuration from .env
│   ├── dash_app.py              # Dash frontend application
│   ├── langfuse_integration.py  # Langfuse setup
│   └── tools.py                 # Search tool setup
├── docs/
│   ├── TIME_TRAVEL.md           # Time travel feature documentation
│   └── MESSAGE_EDITING.md       # Message editing & branching documentation
├── main.py                      # Application entry point
├── pyproject.toml               # Project configuration (uv)
├── uv.lock                      # Locked dependencies
├── .env                         # Environment configuration
├── .env.example                 # Example configuration
└── .gitignore                   # Git ignore rules
```

## Setup

### 1. Install Dependencies

```bash
uv sync
```

### 2. Configure Environment

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Required environment variables:
- `AZURE_OPENAI_API_KEY`: Your Azure OpenAI API key
- `AZURE_OPENAI_ENDPOINT`: Your Azure OpenAI endpoint URL
- `AZURE_OPENAI_DEPLOYMENT_NAME`: Your GPT deployment name
- `AZURE_OPENAI_REASONING_EFFORT`: Reasoning effort for GPT-5 models (low/medium/high)
- `TAVILY_API_KEY`: Tavily API key for web search
- `LANGFUSE_PUBLIC_KEY`: Langfuse public key
- `LANGFUSE_SECRET_KEY`: Langfuse secret key
- `LANGFUSE_HOST`: Langfuse host URL
- `LANGFUSE_PROMPT_LABEL`: Label for fetching prompts from Langfuse

### 3. Create Prompts in Langfuse

Create two prompts in your Langfuse instance:

**1. Main Agent Prompt** (`test_checkpoint`):
- Create a prompt named `test_checkpoint`
- Add your desired system prompt for the main chat agent
- Add the label matching your `LANGFUSE_PROMPT_LABEL` configuration (default: `production`)

Example main agent prompt:
```
You are an advanced AI assistant powered by GPT with enhanced reasoning capabilities and access to real-time internet search.

## Core Capabilities
1. Deep Reasoning: Think through complex problems step-by-step
2. Internet Search: Access real-time information via search tool
3. Conversational Memory: Maintain context throughout the conversation

## Guidelines
- Use search for current events, news, or data verification
- Provide thorough, well-reasoned responses
- Cite sources when presenting factual information
- Acknowledge uncertainty when appropriate
```

**2. Checkpoint Judge Prompt** (`checkpoint_judge`):
- Create a prompt named `checkpoint_judge`
- Add the checkpoint evaluation prompt
- Use the same label as above

Example checkpoint judge prompt:
```
You are a checkpoint management assistant. Your role is to decide whether the current point in a conversation is significant enough to save as a checkpoint for time-travel functionality.

**When to recommend saving a checkpoint:**
- After completing a significant task or solving a problem
- At natural conversation boundaries (topic shifts, completed explanations)
- After important decisions or conclusions are reached
- When substantial new information has been shared
- After code implementations, debugging sessions, or technical solutions
- When the user receives a comprehensive answer to their question

**When NOT to recommend saving:**
- During ongoing, incomplete discussions
- After simple greetings or acknowledgments
- During clarification questions without resolution
- In the middle of multi-step processes
- After trivial exchanges or small talk
- If very few messages have been exchanged since the last checkpoint

**Guidelines:**
- Consider the conversation's depth and value added since last checkpoint
- Prioritize quality over quantity - save meaningful milestones
- Think about whether a user would want to return to this exact point
- Suggested checkpoint names should be descriptive (e.g., "Solved login bug", "Completed design review", "Explained Python decorators")

Analyze the recent conversation context and make a decision.
```

### 4. Run the Application

```bash
uv run python main.py
```

The application will start at `http://127.0.0.1:8050`

## Usage

### Multi-Tab Sessions

Each browser tab operates independently:

1. **New Tab**: Opening a new tab creates a fresh session with a unique 8-character session ID
2. **Session ID Display**: Your session ID is visible in the top-right corner of the navbar
3. **Independent State**: Each tab has its own:
   - Conversation history
   - Checkpoint storage
   - Agent instance
4. **Session Persistence**: Sessions survive page refresh within the same tab (stored in browser session storage)
5. **Auto-Cleanup**: Inactive sessions are automatically removed after 60 minutes

### Chat Interface

1. Type your message in the input box
2. Press Enter or click the send button
3. The AI will respond (using web search when needed)
4. **AI Auto-Save**: After significant responses, the AI judge may automatically create a checkpoint

### Message Editing & Branching

You can edit your previously sent messages to explore different conversation paths:

1. **Edit Message**: Click the edit button (pencil icon) on any of your messages
2. **Modify Content**: Edit the message text in the modal dialog
3. **Create Branch**: Click "Save & Regenerate"
   - All messages after the edited one are discarded
   - AI generates a new response to your edited message
   - Creates a new conversation branch from that point
4. **Checkpoint Protection**: Saved checkpoints remain unchanged
   - If you saved "My name is Mickey" as a checkpoint
   - Then edit it to "My name is Levin"
   - The checkpoint will still contain "Mickey"
   - You can restore to the checkpoint anytime to return to the original branch

**Use Cases:**
- Try different phrasings of a question
- Explore alternative conversation paths
- Correct typos or refine your questions
- Experiment with different approaches without losing checkpoints

### Checkpoint System (Time Travel)

The system features both **AI-powered automatic checkpoints** and **manual user-created checkpoints**:

#### AI-Powered Automatic Checkpoints
- The AI judge evaluates each conversation turn
- Automatically saves checkpoints at significant moments
- Identified by 🤖 icon and blue border
- Shows AI-suggested name and reasoning

#### Manual Checkpoints
1. **Save Checkpoint**: Click "Save" to manually save the current conversation state
   - Button is green when you can save
   - Button is grey/disabled if AI already saved or no changes exist
   - Hover over button to see tooltip explaining its state
2. **View Checkpoints**: See all saved checkpoints in the right panel
   - 🤖 Blue border = AI-created checkpoint
   - 👤 Green border = Human-created checkpoint
3. **Restore Checkpoint**: Click the restore button (↩️) on any checkpoint
   - This will restore the conversation to that point in time
   - All later checkpoints remain available for future restoration
4. **Delete Checkpoint**: Click the trash button to remove a checkpoint

### How Time Travel Works

When you restore to a previous checkpoint:
- The conversation returns to that exact state
- All messages sent after that checkpoint are replaced with the saved state
- **All checkpoints (both earlier and later) remain available**
- You can continue from this point or restore to a different checkpoint
- This allows you to explore different conversation branches

### Save Button States

The save button provides visual feedback:
- **🟢 Green (Enabled)**: You can save a manual checkpoint
- **⚪ Grey (Disabled)**: Either AI already saved or no changes to save
- **Tooltip**: Hover over the button to see why it's enabled/disabled

## API Keys

### Azure OpenAI
1. Create an Azure OpenAI resource in Azure Portal
2. Deploy a GPT model (e.g., gpt-4)
3. Get your endpoint and API key from the resource

### Tavily (Search)
1. Sign up at https://tavily.com
2. Get your API key from the dashboard

### Langfuse (Required)
1. Sign up at https://langfuse.com (or use self-hosted instance)
2. Create a project and get your public/secret keys
3. Create **two prompts**:
   - `test_checkpoint` - System prompt for the main chat agent
   - `checkpoint_judge` - System prompt for the AI checkpoint judge
4. Add the appropriate label (e.g., `production`) to both prompts

## System Prompts

The system uses two AI agents, each fetching its prompt from Langfuse:

1. **Main Chat Agent** (`test_checkpoint`)
2. **Checkpoint Judge Agent** (`checkpoint_judge`)

See the setup section above for example prompt content for both agents.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   Dash Frontend (Multi-Tab)                 │
│  ┌─────────────────┐  ┌─────────────────────────────────┐  │
│  │   Chat Box      │  │   Checkpoint Panel              │  │
│  │   - Messages    │  │   - 🤖 AI Checkpoints (Blue)   │  │
│  │   - Input       │  │   - 👤 Manual Checkpoints (Green)│  │
│  │   - Smart Save  │  │   - Restore/Delete              │  │
│  │   - Session ID  │  │   - Per-session storage         │  │
│  └─────────────────┘  └─────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                  ┌───────────────────────┐
                  │   Session Manager     │
                  │   (Maps session IDs   │
                  │    to agent instances)│
                  └───────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
         Agent 1          Agent 2         Agent 3
      (Session: abc1)  (Session: def2)  (Session: ghi3)
              │               │               │
              └───────────────┴───────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    LangGraph Workflow                       │
│  ┌──────────┐   ┌──────────┐   ┌────────────────────────┐ │
│  │  Agent   │──►│  Tools   │   │  Checkpoint Judge      │ │
│  │  Node    │   │  Node    │──►│  Node (AI Evaluation)  │ │
│  └──────────┘   └──────────┘   └────────────────────────┘ │
│                                          │                   │
│                                          ▼                   │
│                              ┌──────────────────────┐       │
│                              │  Auto-create         │       │
│                              │  Checkpoint (if rec) │       │
│                              └──────────────────────┘       │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
      ┌──────────────┐ ┌─────────────┐ ┌──────────────┐
      │  Checkpoint  │ │   Tavily    │ │   Langfuse   │
      │   Manager    │ │   Search    │ │   (Prompts   │
      │ (per session)│ │             │ │   + Tracing) │
      └──────────────┘ └─────────────┘ └──────────────┘
                              │
                              ▼
                      ┌──────────────┐
                      │  Azure       │
                      │  OpenAI      │
                      │  (GPT-4/5)   │
                      └──────────────┘
```

## Documentation

For detailed documentation on features:
- [Time Travel Technical Documentation](docs/TIME_TRAVEL.md) - Detailed charts and explanations of checkpoint system
- [Message Editing & Branching](docs/MESSAGE_EDITING.md) - Comprehensive guide to editing messages and creating branches
