# AI Chat Agent with Time Travel

A demo application featuring a LangGraph-based chat agent with checkpoint (time travel) functionality.

## Features

- **LangGraph Agent System**: Uses LangGraph for managing the agent workflow
- **AzureChatOpenAI**: Powered by Azure OpenAI's GPT models
- **Internet Search**: Tavily search integration for real-time web search
- **Checkpoint System**: Save and restore conversation states (time travel!)
- **Langfuse Integration**: Prompt management and tracing
- **Dash Frontend**: Clean web-based chat interface

## Project Structure

```
checkpoint/
├── app/
│   ├── __init__.py           # Package initialization
│   ├── agent.py              # LangGraph agent with checkpoints
│   ├── checkpoint_manager.py # Checkpoint save/restore logic
│   ├── config.py             # Configuration from .env
│   ├── dash_app.py           # Dash frontend application
│   ├── langfuse_integration.py # Langfuse setup
│   └── tools.py              # Search tool setup
├── main.py                   # Application entry point
├── pyproject.toml            # Project configuration (uv)
├── uv.lock                   # Locked dependencies
├── .env                      # Environment configuration
└── .env.example              # Example configuration
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

### 3. Create Prompt in Langfuse

Create a prompt named `test_checkpoint` in your Langfuse instance with your desired system prompt. Add the label matching your `LANGFUSE_PROMPT_LABEL` configuration (default: `production`).

### 4. Run the Application

```bash
uv run python main.py
```

The application will start at `http://127.0.0.1:8050`

## Usage

### Chat Interface

1. Type your message in the input box
2. Press Enter or click the send button
3. The AI will respond (using web search when needed)

### Checkpoint System (Time Travel)

1. **Save Checkpoint**: Click "Save" to save the current conversation state
2. **View Checkpoints**: See all saved checkpoints in the right panel
3. **Restore Checkpoint**: Click the restore button (↩️) on any checkpoint
   - **Warning**: This will discard all messages after that checkpoint!
4. **Delete Checkpoint**: Click the trash button to remove a checkpoint

### How Time Travel Works

When you restore to a previous checkpoint:
- The conversation returns to that exact state
- All messages sent after that checkpoint are permanently removed
- All checkpoints created after that point are also removed
- It's like going back in time - the future never happened!

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
3. Create a prompt named `test_checkpoint` with your system prompt
4. Add the appropriate label (e.g., `production`) to the prompt

## System Prompt

The agent fetches its system prompt from Langfuse. Create a prompt named `test_checkpoint` in your Langfuse instance.

Example prompt content:
```
You are an advanced AI assistant powered by GPT-5 with enhanced reasoning capabilities and access to real-time internet search.

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

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Dash Frontend                          │
│  ┌─────────────────┐  ┌─────────────────────────────────┐  │
│  │   Chat Box      │  │   Checkpoint Panel              │  │
│  │   - Messages    │  │   - Save/Restore/Delete         │  │
│  │   - Input       │  │   - Time Travel                 │  │
│  └─────────────────┘  └─────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    LangGraph Agent                          │
│  ┌─────────┐    ┌─────────┐    ┌─────────────────────────┐  │
│  │  Agent  │◄──►│  Tools  │◄──►│  AzureChatOpenAI (LLM)  │  │
│  │  Node   │    │  Node   │    └─────────────────────────┘  │
│  └─────────┘    └─────────┘                                 │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
      ┌──────────────┐ ┌─────────────┐ ┌──────────────┐
      │  Checkpoint  │ │   Tavily    │ │   Langfuse   │
      │   Manager    │ │   Search    │ │   Tracing    │
      └──────────────┘ └─────────────┘ └──────────────┘
```

## Documentation

For detailed documentation on the time travel feature, see:
- [Time Travel Technical Documentation](docs/TIME_TRAVEL.md) - Detailed charts and explanations

## License

MIT License