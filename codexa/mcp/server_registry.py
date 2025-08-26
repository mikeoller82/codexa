"""
MCP server registry for capability discovery and intelligent routing.
"""

import logging
from typing import Dict, List, Optional, Set, Any, Callable
from dataclasses import dataclass
from enum import Enum

from .connection_manager import MCPConnectionManager, MCPServerConfig
from .protocol import MCPError


class ServerCapability(Enum):
    """Standard server capabilities."""
    TOOLS = "tools"
    RESOURCES = "resources"
    PROMPTS = "prompts"
    SAMPLING = "sampling"
    COMPLETION = "completion"
    EMBEDDING = "embedding"
    SEARCH = "search"
    ANALYSIS = "analysis"
    GENERATION = "generation"


@dataclass
class CapabilityMatch:
    """Result of capability matching."""
    server_name: str
    confidence: float  # 0.0 - 1.0
    capabilities: List[str]
    metadata: Dict[str, Any]


class MCPServerRegistry:
    """Registry for MCP servers with capability-based routing."""
    
    def __init__(self, connection_manager: MCPConnectionManager):
        self.connection_manager = connection_manager
        self.logger = logging.getLogger("mcp.registry")
        
        # Server metadata and routing
        self.server_metadata: Dict[str, Dict[str, Any]] = {}
        self.capability_index: Dict[str, Set[str]] = {}
        self.routing_rules: List[Callable[[str, Dict], List[CapabilityMatch]]] = []
        
        # Performance tracking
        self.server_performance: Dict[str, Dict[str, float]] = {}
        
        self._initialize_default_routing()
    
    def register_server(self, config: MCPServerConfig, 
                       metadata: Optional[Dict[str, Any]] = None):
        """Register an MCP server with metadata."""
        self.server_metadata[config.name] = {
            "config": config,
            "capabilities": config.capabilities,
            "priority": config.priority,
            "enabled": config.enabled,
            **(metadata or {})
        }
        
        # Index capabilities
        for capability in config.capabilities:
            if capability not in self.capability_index:
                self.capability_index[capability] = set()
            self.capability_index[capability].add(config.name)
        
        # Initialize performance tracking
        self.server_performance[config.name] = {
            "response_time": 0.0,
            "success_rate": 1.0,
            "usage_count": 0
        }
        
        self.logger.info(f"Registered MCP server: {config.name} with capabilities: {config.capabilities}")
    
    def unregister_server(self, server_name: str):
        """Unregister an MCP server."""
        if server_name in self.server_metadata:
            # Remove from capability index
            config = self.server_metadata[server_name]["config"]
            for capability in config.capabilities:
                if capability in self.capability_index:
                    self.capability_index[capability].discard(server_name)
                    if not self.capability_index[capability]:
                        del self.capability_index[capability]
            
            # Remove metadata and performance data
            del self.server_metadata[server_name]
            if server_name in self.server_performance:
                del self.server_performance[server_name]
            
            self.logger.info(f"Unregistered MCP server: {server_name}")
    
    def find_servers_by_capability(self, capability: str) -> List[str]:
        """Find servers that provide a specific capability."""
        return list(self.capability_index.get(capability, set()))
    
    def find_best_server(self, request: str, 
                        required_capabilities: Optional[List[str]] = None,
                        context: Optional[Dict[str, Any]] = None) -> Optional[CapabilityMatch]:
        """Find the best server for a request using routing rules."""
        context = context or {}
        required_capabilities = required_capabilities or []
        
        # Get all potential matches
        matches = self.find_matches(request, required_capabilities, context)
        
        if not matches:
            return None
        
        # Sort by confidence and performance
        scored_matches = []
        for match in matches:
            server_perf = self.server_performance.get(match.server_name, {})
            
            # Calculate composite score
            performance_score = (
                server_perf.get("success_rate", 0.5) * 0.4 +
                (1.0 - min(server_perf.get("response_time", 1.0), 1.0)) * 0.3 +
                match.confidence * 0.3
            )
            
            scored_matches.append((performance_score, match))
        
        # Return highest scoring match
        scored_matches.sort(key=lambda x: x[0], reverse=True)
        return scored_matches[0][1]
    
    def find_matches(self, request: str,
                    required_capabilities: List[str],
                    context: Dict[str, Any]) -> List[CapabilityMatch]:
        """Find all servers that match the request criteria."""
        matches = []
        
        # Apply routing rules
        for rule in self.routing_rules:
            try:
                rule_matches = rule(request, context)
                matches.extend(rule_matches)
            except Exception as e:
                self.logger.error(f"Error applying routing rule: {e}")
        
        # Filter by required capabilities
        if required_capabilities:
            filtered_matches = []
            for match in matches:
                server_caps = set(self.server_metadata.get(match.server_name, {}).get("capabilities", []))
                if set(required_capabilities).issubset(server_caps):
                    filtered_matches.append(match)
            matches = filtered_matches
        
        # Filter by server availability
        available_servers = self.connection_manager.get_available_servers()
        matches = [m for m in matches if m.server_name in available_servers]
        
        return matches
    
    def add_routing_rule(self, rule: Callable[[str, Dict], List[CapabilityMatch]]):
        """Add a custom routing rule."""
        self.routing_rules.append(rule)
    
    def update_performance(self, server_name: str, 
                         response_time: float,
                         success: bool):
        """Update server performance metrics."""
        if server_name not in self.server_performance:
            return
        
        perf = self.server_performance[server_name]
        
        # Update response time (moving average)
        perf["response_time"] = (perf["response_time"] * 0.8) + (response_time * 0.2)
        
        # Update success rate (moving average)
        current_success_rate = 1.0 if success else 0.0
        perf["success_rate"] = (perf["success_rate"] * 0.9) + (current_success_rate * 0.1)
        
        # Update usage count
        perf["usage_count"] += 1
    
    def get_server_status(self) -> Dict[str, Any]:
        """Get comprehensive server registry status."""
        available_servers = self.connection_manager.get_available_servers()
        
        status = {
            "total_servers": len(self.server_metadata),
            "available_servers": len(available_servers),
            "total_capabilities": len(self.capability_index),
            "servers": {}
        }
        
        for name, metadata in self.server_metadata.items():
            server_status = {
                "available": name in available_servers,
                "capabilities": metadata["capabilities"],
                "priority": metadata["priority"],
                "enabled": metadata["enabled"],
                "performance": self.server_performance.get(name, {})
            }
            status["servers"][name] = server_status
        
        return status
    
    def get_capabilities_summary(self) -> Dict[str, List[str]]:
        """Get summary of all capabilities and providing servers."""
        return {cap: list(servers) for cap, servers in self.capability_index.items()}
    
    def _initialize_default_routing(self):
        """Initialize default routing rules."""
        
        # Rule 1: Documentation and search requests
        def documentation_rule(request: str, context: Dict) -> List[CapabilityMatch]:
            doc_keywords = ["documentation", "docs", "example", "tutorial", "guide", "reference"]
            request_lower = request.lower()
            
            if any(keyword in request_lower for keyword in doc_keywords):
                matches = []
                for server in self.find_servers_by_capability("documentation"):
                    matches.append(CapabilityMatch(
                        server_name=server,
                        confidence=0.8,
                        capabilities=["documentation", "search"],
                        metadata={"rule": "documentation"}
                    ))
                return matches
            return []
        
        # Rule 2: Code analysis and reasoning
        def analysis_rule(request: str, context: Dict) -> List[CapabilityMatch]:
            analysis_keywords = ["analyze", "debug", "explain", "understand", "review", "investigate"]
            request_lower = request.lower()
            
            if any(keyword in request_lower for keyword in analysis_keywords):
                matches = []
                for server in self.find_servers_by_capability("analysis"):
                    matches.append(CapabilityMatch(
                        server_name=server,
                        confidence=0.7,
                        capabilities=["analysis", "reasoning"],
                        metadata={"rule": "analysis"}
                    ))
                return matches
            return []
        
        # Rule 3: UI and component generation
        def ui_generation_rule(request: str, context: Dict) -> List[CapabilityMatch]:
            ui_keywords = ["component", "ui", "interface", "form", "button", "layout", "design"]
            request_lower = request.lower()
            
            if any(keyword in request_lower for keyword in ui_keywords):
                matches = []
                for server in self.find_servers_by_capability("generation"):
                    if "ui" in self.server_metadata.get(server, {}).get("capabilities", []):
                        matches.append(CapabilityMatch(
                            server_name=server,
                            confidence=0.9,
                            capabilities=["generation", "ui"],
                            metadata={"rule": "ui_generation"}
                        ))
                return matches
            return []
        
        # Rule 4: Testing and validation  
        def testing_rule(request: str, context: Dict) -> List[CapabilityMatch]:
            test_keywords = ["test", "testing", "validation", "verify", "check", "qa"]
            request_lower = request.lower()
            
            if any(keyword in request_lower for keyword in test_keywords):
                matches = []
                for server in self.find_servers_by_capability("testing"):
                    matches.append(CapabilityMatch(
                        server_name=server,
                        confidence=0.8,
                        capabilities=["testing", "validation"],
                        metadata={"rule": "testing"}
                    ))
                return matches
            return []
        
        # Add default rules
        self.routing_rules.extend([
            documentation_rule,
            analysis_rule,
            ui_generation_rule,
            testing_rule
        ])
    
    def diagnose_routing(self, request: str, 
                        context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Diagnose routing for a request (debug utility)."""
        context = context or {}
        
        diagnosis = {
            "request": request,
            "context": context,
            "available_servers": self.connection_manager.get_available_servers(),
            "rule_matches": [],
            "final_matches": [],
            "recommended_server": None
        }
        
        # Test each routing rule
        for i, rule in enumerate(self.routing_rules):
            try:
                matches = rule(request, context)
                diagnosis["rule_matches"].append({
                    "rule_index": i,
                    "matches": [
                        {
                            "server": m.server_name,
                            "confidence": m.confidence,
                            "capabilities": m.capabilities
                        } for m in matches
                    ]
                })
            except Exception as e:
                diagnosis["rule_matches"].append({
                    "rule_index": i,
                    "error": str(e)
                })
        
        # Get final matches
        final_matches = self.find_matches(request, [], context)
        diagnosis["final_matches"] = [
            {
                "server": m.server_name,
                "confidence": m.confidence,
                "capabilities": m.capabilities,
                "metadata": m.metadata
            } for m in final_matches
        ]
        
        # Get recommended server
        best_match = self.find_best_server(request, context=context)
        if best_match:
            diagnosis["recommended_server"] = {
                "server": best_match.server_name,
                "confidence": best_match.confidence,
                "capabilities": best_match.capabilities
            }
        
        return diagnosis