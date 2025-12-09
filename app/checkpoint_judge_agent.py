"""
Checkpoint Judge Agent
AI agent that decides whether the current conversation state is worth saving as a checkpoint
"""
from typing import Literal
from langchain_openai import AzureChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, Field
from langfuse import Langfuse
from app.config import config

# Fallback prompt if Langfuse is unavailable
DEFAULT_CHECKPOINT_JUDGE_PROMPT = """You are a checkpoint management assistant. Your role is to decide whether the current point in a conversation is significant enough to save as a checkpoint for time-travel functionality.

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

Analyze the recent conversation context and make a decision."""


class CheckpointDecision(BaseModel):
    """Structured decision about whether to create a checkpoint"""
    should_save: bool = Field(description="Whether a checkpoint should be saved at this point")
    reason: str = Field(description="Brief explanation of the decision (1-2 sentences)")
    suggested_name: str = Field(description="Suggested name for the checkpoint if should_save is True")


class CheckpointJudgeAgent:
    """
    AI agent that evaluates whether to save a checkpoint after each conversation turn.
    Uses structured output to provide consistent, parseable decisions.
    Fetches its system prompt from Langfuse.
    """
    
    def __init__(self):
        self.langfuse_client = self._create_langfuse_client()
        self.system_prompt = self._get_system_prompt()
        self.llm = self._create_llm()
    
    def _create_langfuse_client(self) -> Langfuse:
        """Create Langfuse client for prompt management"""
        return Langfuse(
            public_key=config.LANGFUSE_PUBLIC_KEY,
            secret_key=config.LANGFUSE_SECRET_KEY,
            host=config.LANGFUSE_HOST,
        )
    
    def _get_system_prompt(self) -> str:
        """Get checkpoint judge system prompt from Langfuse"""
        try:
            prompt = self.langfuse_client.get_prompt("checkpoint_judge", label=config.LANGFUSE_PROMPT_LABEL)
            return prompt.compile()
        except Exception as e:
            print(f"Warning: Could not fetch checkpoint judge prompt from Langfuse: {e}")
            print("Using default fallback prompt.")
            return DEFAULT_CHECKPOINT_JUDGE_PROMPT
        
    def _create_llm(self) -> AzureChatOpenAI:
        """Create the AzureChatOpenAI instance with structured output"""
        base_llm = AzureChatOpenAI(
            azure_endpoint=config.AZURE_OPENAI_ENDPOINT,
            azure_deployment=config.AZURE_OPENAI_DEPLOYMENT_NAME,
            api_version=config.AZURE_OPENAI_API_VERSION,
            api_key=config.AZURE_OPENAI_API_KEY
        )
        # Use structured output for reliable parsing
        return base_llm.with_structured_output(CheckpointDecision)
    
    def should_create_checkpoint(
        self,
        recent_messages: list[dict],
        message_count: int,
        last_checkpoint_message_count: int = 0
    ) -> CheckpointDecision:
        """
        Evaluate whether a checkpoint should be created at this point.
        
        Args:
            recent_messages: Recent conversation messages (last 4-6 exchanges)
            message_count: Total number of messages in the conversation
            last_checkpoint_message_count: Message count at the last checkpoint
            
        Returns:
            CheckpointDecision with should_save flag, reason, and suggested name
        """
        # Build context about the conversation
        messages_since_last = message_count - last_checkpoint_message_count
        
        # Format recent conversation
        conversation_text = self._format_conversation(recent_messages)
        
        # Create the analysis prompt
        analysis_prompt = f"""Analyze this conversation segment and decide if a checkpoint should be saved.

**Conversation Context:**
- Total messages in conversation: {message_count}
- Messages since last checkpoint: {messages_since_last}
- Recent conversation (last few exchanges):

{conversation_text}

Should a checkpoint be saved at this point? Provide your decision with reasoning."""
        
        # Get the structured decision from the LLM
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=analysis_prompt)
        ]
        
        decision = self.llm.invoke(messages)
        return decision
    
    def _format_conversation(self, messages: list[dict]) -> str:
        """Format message list into readable conversation text"""
        lines = []
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            
            if role == "user":
                lines.append(f"USER: {content}")
            elif role == "assistant":
                # Truncate very long responses
                if len(content) > 500:
                    content = content[:500] + "..."
                lines.append(f"ASSISTANT: {content}")
        
        return "\n\n".join(lines)
