"""
LangGraph Agent Module
Implements the chat agent with AzureChatOpenAI and checkpoint support
"""
from typing import Annotated, TypedDict, Sequence
from langchain_openai import AzureChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langgraph.graph.message import add_messages
from langfuse.langchain import CallbackHandler as LangfuseCallbackHandler
from langfuse import Langfuse

from app.config import config
from app.tools import get_tools
from app.checkpoint_manager import CheckpointManager
from app.checkpoint_judge_agent import CheckpointJudgeAgent

# Fallback prompt if Langfuse is unavailable
DEFAULT_SYSTEM_PROMPT = """You are a helpful AI assistant with access to internet search capabilities. Answer questions accurately and use the search tool when you need current information."""


class AgentState(TypedDict):
    """State schema for the agent"""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    should_auto_checkpoint: bool  # Flag to indicate if AI judge recommended checkpoint
    auto_checkpoint_name: str  # Suggested checkpoint name from AI judge
    auto_checkpoint_reason: str  # Reason for checkpoint from AI judge


class ChatAgent:
    """
    Chat Agent using LangGraph with AzureChatOpenAI
    
    Features:
    - Uses AzureChatOpenAI as the LLM
    - Has internet search capability via Tavily
    - Supports checkpoint save/restore for conversation time-travel
    - Integrated with Langfuse for tracing
    """
    
    def __init__(self):
        self.langfuse_client = self._create_langfuse_client()
        self.system_prompt = self._get_system_prompt()
        self.llm = self._create_llm()
        self.tools = get_tools()
        self.llm_with_tools = self.llm.bind_tools(self.tools)
        self.checkpoint_manager = CheckpointManager()
        self.checkpoint_judge = CheckpointJudgeAgent()
        self.current_state: AgentState = {
            "messages": [],
            "should_auto_checkpoint": False,
            "auto_checkpoint_name": "",
            "auto_checkpoint_reason": ""
        }
        self.langfuse_handler = self._create_langfuse_handler()
        self.graph = self._build_graph()
    
    def _create_langfuse_client(self) -> Langfuse:
        """Create Langfuse client for prompt management"""
        return Langfuse(
            public_key=config.LANGFUSE_PUBLIC_KEY,
            secret_key=config.LANGFUSE_SECRET_KEY,
            host=config.LANGFUSE_HOST,
        )
    
    def _get_system_prompt(self) -> str:
        """Get system prompt from Langfuse"""
        try:
            prompt = self.langfuse_client.get_prompt("test_checkpoint", label=config.LANGFUSE_PROMPT_LABEL)
            return prompt.compile()
        except Exception as e:
            print(f"Warning: Could not fetch prompt from Langfuse: {e}")
            print("Using default fallback prompt.")
            return DEFAULT_SYSTEM_PROMPT
        
    def _create_llm(self) -> AzureChatOpenAI:
        """Create the AzureChatOpenAI instance"""
        return AzureChatOpenAI(
            azure_endpoint=config.AZURE_OPENAI_ENDPOINT,
            azure_deployment=config.AZURE_OPENAI_DEPLOYMENT_NAME,
            api_version=config.AZURE_OPENAI_API_VERSION,
            api_key=config.AZURE_OPENAI_API_KEY,
            reasoning_effort=config.AZURE_OPENAI_REASONING_EFFORT,
        )
    
    def _create_langfuse_handler(self) -> LangfuseCallbackHandler:
        """Create Langfuse callback handler for tracing"""
        # Langfuse 3.x uses environment variables automatically
        # Set them before creating the handler
        import os
        os.environ["LANGFUSE_PUBLIC_KEY"] = config.LANGFUSE_PUBLIC_KEY
        os.environ["LANGFUSE_SECRET_KEY"] = config.LANGFUSE_SECRET_KEY
        os.environ["LANGFUSE_HOST"] = config.LANGFUSE_HOST
        return LangfuseCallbackHandler()
    
    def _should_continue(self, state: AgentState) -> str:
        """Determine if the agent should continue or end"""
        messages = state["messages"]
        last_message = messages[-1]
        
        # If the LLM makes a tool call, route to the tools node
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        
        # After agent completes, go to checkpoint judge
        return "checkpoint_judge"
    
    def _judge_checkpoint(self, state: AgentState) -> dict:
        """
        Judge whether to create an automatic checkpoint.
        This is called after the agent responds to the user.
        """
        messages = state["messages"]
        
        # Get recent conversation history
        recent_messages = []
        for msg in messages[-8:]:  # Last 4 exchanges (8 messages)
            if isinstance(msg, HumanMessage):
                recent_messages.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                recent_messages.append({"role": "assistant", "content": msg.content})
        
        # Get last checkpoint message count
        latest_checkpoint = self.checkpoint_manager.get_latest_checkpoint()
        last_checkpoint_count = latest_checkpoint.message_count if latest_checkpoint else 0
        
        # Ask the judge agent
        decision = self.checkpoint_judge.should_create_checkpoint(
            recent_messages=recent_messages,
            message_count=len(messages),
            last_checkpoint_message_count=last_checkpoint_count
        )
        
        # Update state with judge's decision
        return {
            "should_auto_checkpoint": decision.should_save,
            "auto_checkpoint_name": decision.suggested_name if decision.should_save else "",
            "auto_checkpoint_reason": decision.reason
        }
    
    def _call_model(self, state: AgentState) -> dict:
        """Call the LLM with the current state"""
        messages = state["messages"]
        
        # Add system message if not present
        if not messages or not isinstance(messages[0], SystemMessage):
            messages = [SystemMessage(content=self.system_prompt)] + list(messages)
        
        response = self.llm_with_tools.invoke(
            messages,
            config={"callbacks": [self.langfuse_handler]}
        )
        
        return {"messages": [response]}
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow"""
        # Create the graph
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("agent", self._call_model)
        workflow.add_node("tools", ToolNode(self.tools))
        workflow.add_node("checkpoint_judge", self._judge_checkpoint)
        
        # Set entry point
        workflow.set_entry_point("agent")
        
        # Add conditional edges from agent
        workflow.add_conditional_edges(
            "agent",
            self._should_continue,
            {
                "tools": "tools",
                "checkpoint_judge": "checkpoint_judge",
            }
        )
        
        # Tools always return to agent
        workflow.add_edge("tools", "agent")
        
        # Checkpoint judge ends the workflow
        workflow.add_edge("checkpoint_judge", END)
        
        # Compile the graph
        return workflow.compile()
    
    def chat(self, user_message: str) -> str:
        """
        Process a user message and return the agent's response.
        
        Args:
            user_message: The user's input message
            
        Returns:
            The agent's response text
        """
        # Add user message to state
        self.current_state["messages"] = list(self.current_state["messages"]) + [
            HumanMessage(content=user_message)
        ]
        
        # Run the graph (includes agent, tools, and checkpoint judge)
        result = self.graph.invoke(
            self.current_state,
            config={"callbacks": [self.langfuse_handler]}
        )
        
        # Update current state
        self.current_state = result
        
        # If AI judge recommends checkpoint, create it automatically
        if result.get("should_auto_checkpoint", False):
            self._create_auto_checkpoint()
        
        # Extract the last AI message
        for msg in reversed(result["messages"]):
            if isinstance(msg, AIMessage):
                return msg.content
        
        return "I apologize, but I couldn't generate a response."
    
    def _create_auto_checkpoint(self):
        """Create an automatic checkpoint based on AI judge's recommendation"""
        name = self.current_state.get("auto_checkpoint_name", "Auto-saved")
        reason = self.current_state.get("auto_checkpoint_reason", "AI recommended checkpoint")
        
        # Convert messages to serializable format
        serializable_state = {
            "messages": [
                {
                    "type": type(msg).__name__,
                    "content": msg.content,
                    "additional_kwargs": getattr(msg, "additional_kwargs", {}),
                    "tool_calls": getattr(msg, "tool_calls", []) if hasattr(msg, "tool_calls") else []
                }
                for msg in self.current_state["messages"]
            ]
        }
        
        self.checkpoint_manager.save_checkpoint(
            serializable_state,
            name=name,
            description=reason,
            created_by="ai"
        )
    
    def has_auto_checkpoint_for_current_state(self) -> bool:
        """Check if an AI checkpoint exists for the current message count"""
        current_msg_count = len(self.current_state["messages"])
        checkpoints = self.checkpoint_manager.list_checkpoints()
        
        # Check if the latest checkpoint is AI-created and matches current state
        if checkpoints:
            latest = checkpoints[-1]
            if latest["created_by"] == "ai" and latest["message_count"] == current_msg_count:
                return True
        return False
    
    def save_checkpoint(self, name: str = None, description: str = "") -> dict:
        """
        Save the current conversation state as a checkpoint (human-initiated).
        
        Args:
            name: Optional name for the checkpoint
            description: Optional description
            
        Returns:
            Checkpoint info dict
        """
        # Convert messages to serializable format
        serializable_state = {
            "messages": [
                {
                    "type": type(msg).__name__,
                    "content": msg.content,
                    "additional_kwargs": getattr(msg, "additional_kwargs", {}),
                    "tool_calls": getattr(msg, "tool_calls", []) if hasattr(msg, "tool_calls") else []
                }
                for msg in self.current_state["messages"]
            ]
        }
        
        checkpoint = self.checkpoint_manager.save_checkpoint(
            serializable_state, 
            name=name,
            description=description,
            created_by="human"
        )
        
        return {
            "id": checkpoint.id,
            "name": checkpoint.name,
            "timestamp": checkpoint.timestamp,
            "message_count": checkpoint.message_count,
            "description": checkpoint.description,
            "created_by": checkpoint.created_by
        }
    
    def list_checkpoints(self) -> list[dict]:
        """List all available checkpoints"""
        return self.checkpoint_manager.list_checkpoints()
    
    def restore_checkpoint(self, checkpoint_id: str) -> bool:
        """
        Restore to a previous checkpoint.
        All conversation after this checkpoint will be discarded.
        
        Args:
            checkpoint_id: The ID of the checkpoint to restore
            
        Returns:
            True if successful, False otherwise
        """
        restored_state = self.checkpoint_manager.restore_checkpoint(checkpoint_id)
        
        if restored_state is None:
            return False
        
        # Reconstruct messages from serialized state
        messages = []
        for msg_data in restored_state.get("messages", []):
            msg_type = msg_data.get("type", "")
            content = msg_data.get("content", "")
            
            if msg_type == "HumanMessage":
                messages.append(HumanMessage(content=content))
            elif msg_type == "AIMessage":
                messages.append(AIMessage(
                    content=content,
                    additional_kwargs=msg_data.get("additional_kwargs", {})
                ))
            elif msg_type == "SystemMessage":
                messages.append(SystemMessage(content=content))
        
        self.current_state = {"messages": messages}
        return True
    
    def get_conversation_history(self) -> list[dict]:
        """
        Get the current conversation history in a display-friendly format.
        
        Returns:
            List of message dicts with 'role' and 'content'
        """
        history = []
        for msg in self.current_state["messages"]:
            if isinstance(msg, HumanMessage):
                history.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                history.append({"role": "assistant", "content": msg.content})
            # Skip system messages for display
        return history
    
    def clear_conversation(self) -> None:
        """Clear the current conversation"""
        self.current_state = {
            "messages": [],
            "should_auto_checkpoint": False,
            "auto_checkpoint_name": "",
            "auto_checkpoint_reason": ""
        }
    
    def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """Delete a specific checkpoint"""
        return self.checkpoint_manager.delete_checkpoint(checkpoint_id)
