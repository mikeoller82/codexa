"""
WebSearch tool - Allows Claude to search the web and use results to inform responses.
"""

import asyncio
import aiohttp
import json
from typing import Set, List, Optional
from urllib.parse import quote_plus
from ..base.tool_interface import Tool, ToolContext, ToolResult


class WebSearchTool(Tool):
    """Allows Claude to search the web and use results to inform responses."""
    
    @property
    def name(self) -> str:
        return "WebSearch"
    
    @property
    def description(self) -> str:
        return "Allows Claude to search the web and use results to inform responses"
    
    @property
    def category(self) -> str:
        return "claude_code"
    
    @property
    def required_context(self) -> Set[str]:
        return {"query"}
    
    def can_handle_request(self, request: str, context: ToolContext) -> float:
        """Determine if this tool can handle the request."""
        request_lower = request.lower()
        
        # High confidence for explicit search requests
        if any(phrase in request_lower for phrase in [
            "search web", "web search", "search online", "search for", "find online"
        ]):
            return 0.9
        
        # Medium confidence for information requests
        if any(phrase in request_lower for phrase in [
            "search", "find", "look up", "what is", "who is", "latest"
        ]):
            return 0.6
        
        # Lower confidence for general information needs
        if any(phrase in request_lower for phrase in [
            "current", "recent", "today", "news", "information about"
        ]):
            return 0.4
        
        return 0.0
    
    async def execute(self, context: ToolContext) -> ToolResult:
        """Execute the WebSearch tool."""
        try:
            # Extract parameters
            query = context.get_state("query")
            allowed_domains = context.get_state("allowed_domains", [])
            blocked_domains = context.get_state("blocked_domains", [])
            
            if not query:
                return ToolResult.error_result(
                    error="Missing required parameter: query",
                    tool_name=self.name
                )
            
            if len(query) < 2:
                return ToolResult.error_result(
                    error="Search query must be at least 2 characters long",
                    tool_name=self.name
                )
            
            # Perform web search
            search_results = await self._perform_search(query, allowed_domains, blocked_domains)
            
            if not search_results["success"]:
                return ToolResult.error_result(
                    error=search_results["error"],
                    tool_name=self.name
                )
            
            results = search_results["results"]
            
            return ToolResult.success_result(
                data={
                    "query": query,
                    "results": results,
                    "result_count": len(results),
                    "allowed_domains": allowed_domains,
                    "blocked_domains": blocked_domains,
                    "search_metadata": search_results.get("metadata", {})
                },
                tool_name=self.name,
                output=self._format_search_results(results, query)
            )
            
        except Exception as e:
            return ToolResult.error_result(
                error=f"WebSearch tool execution failed: {str(e)}",
                tool_name=self.name
            )
    
    async def _perform_search(self, query: str, allowed_domains: List[str], 
                             blocked_domains: List[str]) -> dict:
        """Perform web search using available search API."""
        try:
            # Try DuckDuckGo search first (free and doesn't require API key)
            results = await self._duckduckgo_search(query)
            
            if results["success"]:
                # Filter results by domain restrictions
                filtered_results = self._filter_results_by_domain(
                    results["results"], allowed_domains, blocked_domains
                )
                
                return {
                    "success": True,
                    "results": filtered_results,
                    "metadata": {
                        "search_engine": "duckduckgo",
                        "original_count": len(results["results"]),
                        "filtered_count": len(filtered_results)
                    }
                }
            
            # Fallback to simulated search if no real search is available
            return await self._fallback_search(query)
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Search failed: {str(e)}"
            }
    
    async def _duckduckgo_search(self, query: str) -> dict:
        """Search using DuckDuckGo Instant Answer API."""
        try:
            # Use DuckDuckGo's instant answer API (limited but free)
            encoded_query = quote_plus(query)
            url = f"https://api.duckduckgo.com/?q={encoded_query}&format=json&no_redirect=1&skip_disambig=1"
            
            timeout = aiohttp.ClientTimeout(total=10)
            headers = {
                'User-Agent': 'Codexa/1.0 (https://github.com/codexa)'
            }
            
            async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        return {"success": False, "error": f"API returned status {response.status}"}
                    
                    data = await response.json()
                    
                    results = []
                    
                    # Parse DuckDuckGo instant answer
                    if data.get("AbstractText"):
                        results.append({
                            "title": data.get("Heading", query),
                            "url": data.get("AbstractURL", ""),
                            "snippet": data.get("AbstractText", ""),
                            "source": data.get("AbstractSource", "DuckDuckGo")
                        })
                    
                    # Parse related topics
                    for topic in data.get("RelatedTopics", [])[:5]:
                        if isinstance(topic, dict) and topic.get("Text"):
                            results.append({
                                "title": topic.get("Text", "").split(" - ")[0] if " - " in topic.get("Text", "") else topic.get("Text", "")[:100],
                                "url": topic.get("FirstURL", ""),
                                "snippet": topic.get("Text", ""),
                                "source": "DuckDuckGo Related"
                            })
                    
                    # Parse definition if available
                    if data.get("Definition"):
                        results.append({
                            "title": f"Definition: {query}",
                            "url": data.get("DefinitionURL", ""),
                            "snippet": data.get("Definition", ""),
                            "source": data.get("DefinitionSource", "")
                        })
                    
                    return {
                        "success": True,
                        "results": results
                    }
                    
        except Exception as e:
            return {
                "success": False,
                "error": f"DuckDuckGo search failed: {str(e)}"
            }
    
    async def _fallback_search(self, query: str) -> dict:
        """Fallback search when no real search API is available."""
        # This provides a simulated search response for demonstration
        # In a real implementation, you might want to integrate with other search APIs
        
        fallback_results = [
            {
                "title": f"Search results for: {query}",
                "url": "https://example.com/search",
                "snippet": f"This is a simulated search result for '{query}'. In a real implementation, this would connect to a search API like Google Custom Search, Bing Search API, or other search services.",
                "source": "Simulated Search"
            },
            {
                "title": f"Information about {query}",
                "url": "https://example.com/info",
                "snippet": f"Web search functionality requires configuration of search API credentials. Common options include Google Custom Search API, Bing Search API, or other search services.",
                "source": "System Information"
            }
        ]
        
        return {
            "success": True,
            "results": fallback_results,
            "metadata": {
                "search_engine": "fallback",
                "note": "This is a simulated search result. Configure search API for real results."
            }
        }
    
    def _filter_results_by_domain(self, results: List[dict], allowed_domains: List[str], 
                                 blocked_domains: List[str]) -> List[dict]:
        """Filter search results by domain restrictions."""
        if not allowed_domains and not blocked_domains:
            return results
        
        filtered_results = []
        
        for result in results:
            url = result.get("url", "")
            if not url:
                continue
            
            # Extract domain from URL
            try:
                from urllib.parse import urlparse
                domain = urlparse(url).netloc.lower()
            except Exception:
                continue
            
            # Check blocked domains
            if blocked_domains:
                if any(blocked in domain for blocked in blocked_domains):
                    continue
            
            # Check allowed domains
            if allowed_domains:
                if not any(allowed in domain for allowed in allowed_domains):
                    continue
            
            filtered_results.append(result)
        
        return filtered_results
    
    def _format_search_results(self, results: List[dict], query: str) -> str:
        """Format search results for display."""
        if not results:
            return f"No search results found for: {query}"
        
        output_lines = [f"Search results for: {query}\n"]
        
        for i, result in enumerate(results[:10], 1):  # Limit to 10 results
            title = result.get("title", "No title")
            url = result.get("url", "")
            snippet = result.get("snippet", "")
            source = result.get("source", "")
            
            output_lines.append(f"{i}. **{title}**")
            if url:
                output_lines.append(f"   URL: {url}")
            if snippet:
                # Truncate long snippets
                if len(snippet) > 200:
                    snippet = snippet[:200] + "..."
                output_lines.append(f"   {snippet}")
            if source:
                output_lines.append(f"   Source: {source}")
            output_lines.append("")
        
        if len(results) > 10:
            output_lines.append(f"... and {len(results) - 10} more results")
        
        return "\n".join(output_lines)


# Claude Code schema compatibility
CLAUDE_CODE_SCHEMA = {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "minLength": 2,
            "description": "The search query to use"
        },
        "allowed_domains": {
            "type": "array",
            "items": {
                "type": "string"
            },
            "description": "Only include search results from these domains"
        },
        "blocked_domains": {
            "type": "array",
            "items": {
                "type": "string"
            },
            "description": "Never include search results from these domains"
        }
    },
    "required": ["query"],
    "additionalProperties": False
}