"""
Langfuse Integration Module
Handles prompt management and enhanced tracing with Langfuse
"""
from langfuse import Langfuse
from langfuse.langchain import CallbackHandler as LangfuseCallbackHandler
from app.config import config

# Fallback prompt if Langfuse is unavailable
DEFAULT_SYSTEM_PROMPT = """You are a helpful AI assistant with access to internet search capabilities. Answer questions accurately and use the search tool when you need current information."""


class LangfuseManager:
    """
    Manages Langfuse integration for:
    - Prompt versioning and management
    - Trace monitoring
    - Cost tracking
    """
    
    def __init__(self):
        self.client = Langfuse(
            public_key=config.LANGFUSE_PUBLIC_KEY,
            secret_key=config.LANGFUSE_SECRET_KEY,
            host=config.LANGFUSE_HOST,
        )
    
    def get_system_prompt(self) -> str:
        """
        Get the system prompt from Langfuse.
        This allows dynamic prompt updates without code changes.
        """
        try:
            prompt = self.client.get_prompt("test_checkpoint", label=config.LANGFUSE_PROMPT_LABEL)
            return prompt.compile()
        except Exception as e:
            print(f"Warning: Could not fetch prompt from Langfuse: {e}")
            return DEFAULT_SYSTEM_PROMPT
    
    def get_callback_handler(
        self, 
        session_id: str = None,
        user_id: str = None,
        metadata: dict = None
    ) -> LangfuseCallbackHandler:
        """
        Get a configured Langfuse callback handler for tracing.
        
        Args:
            session_id: Optional session identifier for grouping traces
            user_id: Optional user identifier
            metadata: Optional additional metadata
            
        Returns:
            Configured LangfuseCallbackHandler
        """
        return LangfuseCallbackHandler(
            public_key=config.LANGFUSE_PUBLIC_KEY,
            secret_key=config.LANGFUSE_SECRET_KEY,
            host=config.LANGFUSE_HOST,
            session_id=session_id,
            user_id=user_id,
            metadata=metadata or {}
        )
    
    def log_checkpoint_event(
        self, 
        event_type: str, 
        checkpoint_id: str,
        metadata: dict = None
    ) -> None:
        """
        Log checkpoint events to Langfuse for tracking.
        
        Args:
            event_type: Type of event (save, restore, delete)
            checkpoint_id: ID of the checkpoint
            metadata: Additional metadata
        """
        try:
            trace = self.client.trace(
                name=f"checkpoint-{event_type}",
                metadata={
                    "event_type": event_type,
                    "checkpoint_id": checkpoint_id,
                    **(metadata or {})
                }
            )
            trace.event(
                name=f"Checkpoint {event_type}",
                metadata={"checkpoint_id": checkpoint_id}
            )
        except Exception as e:
            print(f"Failed to log checkpoint event: {e}")
    
    def flush(self) -> None:
        """Flush any pending events to Langfuse"""
        try:
            self.client.flush()
        except Exception:
            pass


# Global instance
langfuse_manager = None


def get_langfuse_manager() -> LangfuseManager:
    """Get or create the global LangfuseManager instance"""
    global langfuse_manager
    if langfuse_manager is None:
        langfuse_manager = LangfuseManager()
    return langfuse_manager
