"""
Session Manager for managing multiple chat agent instances
Each browser tab gets its own session with isolated state
"""
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict
from threading import Lock

from app.agent import ChatAgent


class SessionManager:
    """
    Manages multiple ChatAgent instances, one per session/browser tab.
    
    Features:
    - Automatic session creation with unique IDs
    - Session isolation - each tab has its own agent and checkpoints
    - Automatic cleanup of inactive sessions
    """
    
    def __init__(self, session_timeout_minutes: int = 60):
        """
        Initialize the session manager.
        
        Args:
            session_timeout_minutes: How long to keep inactive sessions (default 60 minutes)
        """
        self.agents: Dict[str, ChatAgent] = {}
        self.last_access: Dict[str, datetime] = {}
        self.session_timeout = timedelta(minutes=session_timeout_minutes)
        self.lock = Lock()
    
    def create_session(self) -> str:
        """
        Create a new session with a unique ID.
        
        Returns:
            The new session ID
        """
        session_id = str(uuid.uuid4())[:8]  # Short ID for display
        
        with self.lock:
            self.agents[session_id] = ChatAgent()
            self.last_access[session_id] = datetime.now()
        
        return session_id
    
    def get_agent(self, session_id: str) -> Optional[ChatAgent]:
        """
        Get the agent for a specific session.
        
        Args:
            session_id: The session ID
            
        Returns:
            The ChatAgent instance or None if session doesn't exist
        """
        with self.lock:
            if session_id in self.agents:
                self.last_access[session_id] = datetime.now()
                return self.agents[session_id]
        return None
    
    def get_or_create_agent(self, session_id: Optional[str] = None) -> tuple[str, ChatAgent]:
        """
        Get existing agent or create new session if needed.
        
        Args:
            session_id: Optional existing session ID
            
        Returns:
            Tuple of (session_id, agent)
        """
        if session_id:
            agent = self.get_agent(session_id)
            if agent:
                return session_id, agent
        
        # Create new session if ID is invalid or doesn't exist
        new_session_id = self.create_session()
        agent = self.get_agent(new_session_id)
        return new_session_id, agent
    
    def delete_session(self, session_id: str) -> bool:
        """
        Delete a specific session.
        
        Args:
            session_id: The session ID to delete
            
        Returns:
            True if deleted, False if not found
        """
        with self.lock:
            if session_id in self.agents:
                del self.agents[session_id]
                if session_id in self.last_access:
                    del self.last_access[session_id]
                return True
        return False
    
    def cleanup_inactive_sessions(self) -> int:
        """
        Remove sessions that have been inactive beyond the timeout.
        
        Returns:
            Number of sessions cleaned up
        """
        now = datetime.now()
        sessions_to_remove = []
        
        with self.lock:
            for session_id, last_time in self.last_access.items():
                if now - last_time > self.session_timeout:
                    sessions_to_remove.append(session_id)
            
            for session_id in sessions_to_remove:
                del self.agents[session_id]
                del self.last_access[session_id]
        
        return len(sessions_to_remove)
    
    def get_session_count(self) -> int:
        """Get the number of active sessions"""
        with self.lock:
            return len(self.agents)
    
    def get_session_info(self, session_id: str) -> Optional[dict]:
        """
        Get information about a session.
        
        Args:
            session_id: The session ID
            
        Returns:
            Dictionary with session info or None if not found
        """
        with self.lock:
            if session_id in self.agents:
                agent = self.agents[session_id]
                return {
                    "session_id": session_id,
                    "message_count": len(agent.current_state.get("messages", [])),
                    "checkpoint_count": len(agent.checkpoint_manager.checkpoints),
                    "last_access": self.last_access[session_id].isoformat()
                }
        return None
