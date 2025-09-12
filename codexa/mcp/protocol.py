"""
JSON-RPC 2.0 protocol implementation for MCP servers.
"""

import json
import uuid
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum


class MCPMessageType(Enum):
    """MCP message types."""
    REQUEST = "request"
    RESPONSE = "response" 
    NOTIFICATION = "notification"
    ERROR = "error"


@dataclass
class MCPMessage:
    """MCP message wrapper for JSON-RPC 2.0 protocol."""

    jsonrpc: str = "2.0"
    id: Optional[str] = None
    method: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Generate ID if not provided for requests."""
        if self.method and not self.id:
            self.id = str(uuid.uuid4())
    
    @property
    def message_type(self) -> MCPMessageType:
        """Determine message type."""
        if self.error:
            return MCPMessageType.ERROR
        elif self.result is not None:
            return MCPMessageType.RESPONSE
        elif self.method and self.id:
            return MCPMessageType.REQUEST
        elif self.method:
            return MCPMessageType.NOTIFICATION
        else:
            raise ValueError("Invalid message structure")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {"jsonrpc": self.jsonrpc}
        
        if self.id is not None:
            result["id"] = self.id
        if self.method:
            result["method"] = self.method
        # Only include params if they are provided (JSON-RPC 2.0 compliance)
        if self.params is not None:
            result["params"] = self.params
        if self.result is not None:
            result["result"] = self.result
        if self.error:
            result["error"] = self.error
            
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MCPMessage":
        """Create message from dictionary."""
        return cls(
            jsonrpc=data.get("jsonrpc", "2.0"),
            id=data.get("id"),
            method=data.get("method"),
            params=data.get("params"),
            result=data.get("result"),
            error=data.get("error")
        )
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, json_str: str) -> "MCPMessage":
        """Create message from JSON string."""
        try:
            data = json.loads(json_str)
            return cls.from_dict(data)
        except json.JSONDecodeError as e:
            raise MCPError(f"Invalid JSON: {e}")


class MCPError(Exception):
    """MCP-specific error."""
    
    def __init__(self, message: str, code: int = -32603, data: Any = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.data = data
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to error dictionary."""
        error = {
            "code": self.code,
            "message": self.message
        }
        if self.data:
            error["data"] = self.data
        return error


class MCPProtocol:
    """JSON-RPC 2.0 protocol handler for MCP communication."""
    
    # Standard JSON-RPC error codes
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603
    
    # MCP-specific error codes
    SERVER_UNAVAILABLE = -32000
    CAPABILITY_NOT_FOUND = -32001
    TIMEOUT_ERROR = -32002
    
    @staticmethod
    def create_request(method: str, params: Optional[Dict[str, Any]] = None,
                      request_id: Optional[str] = None) -> MCPMessage:
        """Create a JSON-RPC 2.0 request message."""
        # Handle None params - don't include params field if None
        if params is None:
            return MCPMessage(
                method=method,
                id=request_id or str(uuid.uuid4())
            )
        else:
            return MCPMessage(
                method=method,
                params=params,
                id=request_id or str(uuid.uuid4())
            )
    
    @staticmethod
    def create_response(request_id: str, result: Any) -> MCPMessage:
        """Create a JSON-RPC 2.0 response message."""
        return MCPMessage(
            id=request_id,
            result=result
        )
    
    @staticmethod
    def create_error_response(request_id: Optional[str], error: MCPError) -> MCPMessage:
        """Create a JSON-RPC 2.0 error response message."""
        return MCPMessage(
            id=request_id,
            error=error.to_dict()
        )
    
    @staticmethod
    def create_notification(method: str, params: Optional[Dict[str, Any]] = None) -> MCPMessage:
        """Create a JSON-RPC 2.0 notification message."""
        return MCPMessage(
            method=method,
            params=params
        )
    
    @staticmethod
    def validate_message(message: MCPMessage) -> bool:
        """Validate message structure according to JSON-RPC 2.0."""
        # Check required jsonrpc field
        if message.jsonrpc != "2.0":
            return False
        
        # Validate based on message type
        msg_type = message.message_type
        
        if msg_type == MCPMessageType.REQUEST:
            return bool(message.method and message.id)
        elif msg_type == MCPMessageType.RESPONSE:
            return bool(message.id and message.result is not None)
        elif msg_type == MCPMessageType.ERROR:
            return bool(message.error and "code" in message.error)
        elif msg_type == MCPMessageType.NOTIFICATION:
            return bool(message.method and message.id is None)
        
        return False
    
    @staticmethod
    def parse_capabilities(capabilities: Dict[str, Any]) -> Dict[str, Any]:
        """Parse server capabilities from initialization response."""
        parsed = {
            "tools": [],
            "resources": [],
            "prompts": [],
            "experimental": {}
        }
        
        # Extract tools
        if "tools" in capabilities:
            parsed["tools"] = capabilities["tools"]
        
        # Extract resources  
        if "resources" in capabilities:
            parsed["resources"] = capabilities["resources"]
            
        # Extract prompts
        if "prompts" in capabilities:
            parsed["prompts"] = capabilities["prompts"]
            
        # Extract experimental features
        if "experimental" in capabilities:
            parsed["experimental"] = capabilities["experimental"]
            
        return parsed
    
    @staticmethod
    def create_initialize_request(client_info: Dict[str, Any]) -> MCPMessage:
        """Create MCP initialization request."""
        params = {
            "protocolVersion": "2024-11-05",
            "clientInfo": client_info,
            "capabilities": {
                "roots": {
                    "listChanged": True
                },
                "sampling": {},
                "tools": {}  # Add tools capability
            }
        }

        return MCPProtocol.create_request("initialize", params)
    
    @staticmethod
    def create_initialized_notification() -> MCPMessage:
        """Create MCP initialized notification."""
        return MCPProtocol.create_notification("initialized")
    
    @staticmethod
    def validate_request(message: MCPMessage) -> bool:
        """Validate that a request message follows MCP protocol requirements."""
        if not message.method:
            return False
        if not message.id:
            return False
        # For requests, params field should always be present (even if empty)
        return True
    
    @staticmethod
    def debug_format_message(message: MCPMessage, direction: str = "SEND") -> str:
        """Format message for debug logging."""
        msg_dict = message.to_dict()
        return f"{direction} MCP: {json.dumps(msg_dict, indent=2)}"