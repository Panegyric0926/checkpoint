"""
Checkpoint Manager for managing conversation state checkpoints
Allows users to save, list, and restore conversation states
"""
import json
import copy
from datetime import datetime
from typing import Optional, Any
from dataclasses import dataclass, field, asdict
import uuid


@dataclass
class Checkpoint:
    """Represents a saved checkpoint of conversation state"""
    id: str
    name: str
    timestamp: str
    state: dict
    message_count: int
    description: str = ""
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "Checkpoint":
        return cls(**data)


class CheckpointManager:
    """
    Manages conversation checkpoints for time-travel functionality.
    
    Features:
    - Save current conversation state as a checkpoint
    - List all available checkpoints
    - Restore to a previous checkpoint (discards all states after that point)
    - Delete checkpoints
    """
    
    def __init__(self):
        self.checkpoints: dict[str, Checkpoint] = {}
        self.checkpoint_order: list[str] = []  # Maintains chronological order
        
    def save_checkpoint(
        self, 
        state: dict, 
        name: Optional[str] = None,
        description: str = ""
    ) -> Checkpoint:
        """
        Save the current conversation state as a checkpoint.
        
        Args:
            state: The current LangGraph state to save
            name: Optional name for the checkpoint
            description: Optional description of what happened at this point
            
        Returns:
            The created Checkpoint object
        """
        checkpoint_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().isoformat()
        
        # Count messages in state
        messages = state.get("messages", [])
        message_count = len(messages)
        
        # Generate default name if not provided
        if not name:
            name = f"Checkpoint {len(self.checkpoints) + 1}"
        
        # Deep copy the state to prevent mutations
        saved_state = copy.deepcopy(state)
        
        checkpoint = Checkpoint(
            id=checkpoint_id,
            name=name,
            timestamp=timestamp,
            state=saved_state,
            message_count=message_count,
            description=description
        )
        
        self.checkpoints[checkpoint_id] = checkpoint
        self.checkpoint_order.append(checkpoint_id)
        
        return checkpoint
    
    def list_checkpoints(self) -> list[dict]:
        """
        List all available checkpoints in chronological order.
        
        Returns:
            List of checkpoint info dictionaries (without full state for efficiency)
        """
        result = []
        for cp_id in self.checkpoint_order:
            cp = self.checkpoints.get(cp_id)
            if cp:
                result.append({
                    "id": cp.id,
                    "name": cp.name,
                    "timestamp": cp.timestamp,
                    "message_count": cp.message_count,
                    "description": cp.description
                })
        return result
    
    def get_checkpoint(self, checkpoint_id: str) -> Optional[Checkpoint]:
        """
        Get a specific checkpoint by ID.
        
        Args:
            checkpoint_id: The ID of the checkpoint to retrieve
            
        Returns:
            The Checkpoint object or None if not found
        """
        return self.checkpoints.get(checkpoint_id)
    
    def restore_checkpoint(self, checkpoint_id: str) -> Optional[dict]:
        """
        Restore to a previous checkpoint, discarding all checkpoints after it.
        
        This implements the "time travel" feature - when you restore to a checkpoint,
        all subsequent checkpoints are removed as if they never happened.
        
        Args:
            checkpoint_id: The ID of the checkpoint to restore to
            
        Returns:
            The restored state dict, or None if checkpoint not found
        """
        if checkpoint_id not in self.checkpoints:
            return None
        
        checkpoint = self.checkpoints[checkpoint_id]
        
        # Find the index of this checkpoint
        try:
            index = self.checkpoint_order.index(checkpoint_id)
        except ValueError:
            return None
        
        # Remove all checkpoints after this one
        checkpoints_to_remove = self.checkpoint_order[index + 1:]
        for cp_id in checkpoints_to_remove:
            if cp_id in self.checkpoints:
                del self.checkpoints[cp_id]
        
        # Truncate the order list
        self.checkpoint_order = self.checkpoint_order[:index + 1]
        
        # Return a deep copy of the saved state
        return copy.deepcopy(checkpoint.state)
    
    def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """
        Delete a specific checkpoint.
        
        Args:
            checkpoint_id: The ID of the checkpoint to delete
            
        Returns:
            True if deleted, False if not found
        """
        if checkpoint_id not in self.checkpoints:
            return False
        
        del self.checkpoints[checkpoint_id]
        self.checkpoint_order.remove(checkpoint_id)
        return True
    
    def clear_all(self) -> None:
        """Clear all checkpoints"""
        self.checkpoints.clear()
        self.checkpoint_order.clear()
    
    def get_latest_checkpoint(self) -> Optional[Checkpoint]:
        """Get the most recent checkpoint"""
        if not self.checkpoint_order:
            return None
        return self.checkpoints.get(self.checkpoint_order[-1])
    
    def export_checkpoints(self) -> str:
        """Export all checkpoints to JSON string"""
        data = {
            "checkpoints": {k: v.to_dict() for k, v in self.checkpoints.items()},
            "order": self.checkpoint_order
        }
        return json.dumps(data, indent=2, default=str)
    
    def import_checkpoints(self, json_str: str) -> None:
        """Import checkpoints from JSON string"""
        data = json.loads(json_str)
        self.checkpoints = {
            k: Checkpoint.from_dict(v) 
            for k, v in data.get("checkpoints", {}).items()
        }
        self.checkpoint_order = data.get("order", [])
