"""
WebFetch tool - Fetches content from a specified URL and processes it.
"""

import asyncio
import aiohttp
from urllib.parse import urlparse
from typing import Set, Optional
from ..base.tool_interface import Tool, ToolContext, ToolResult


class WebFetchTool(Tool):
    """Fetches content from a specified URL and processes it using an AI model."""
    
    @property
    def name(self) -> str:
        return "WebFetch"
    
    @property
    def description(self) -> str:
        return "Fetches content from a specified URL and processes it using an AI model"
    
    @property
    def category(self) -> str:
        return "claude_code"
    
    @property
    def required_context(self) -> Set[str]:
        return {"url", "prompt"}
    
    def can_handle_request(self, request: str, context: ToolContext) -> float:
        """Determine if this tool can handle the request."""
        request_lower = request.lower()
        
        # High confidence for explicit URL fetching
        if any(phrase in request_lower for phrase in [
            "fetch url", "get webpage", "fetch content", "web fetch", "fetch from"
        ]):
            return 0.9
        
        # Medium confidence for URL-related requests
        if any(phrase in request_lower for phrase in [
            "http://", "https://", "www.", "fetch", "get content from"
        ]):
            return 0.7
        
        return 0.0
    
    async def execute(self, context: ToolContext) -> ToolResult:
        """Execute the WebFetch tool."""
        try:
            # Extract parameters
            url = context.get_state("url")
            prompt = context.get_state("prompt")
            
            if not url:
                return ToolResult.error_result(
                    error="Missing required parameter: url",
                    tool_name=self.name
                )
            
            if not prompt:
                return ToolResult.error_result(
                    error="Missing required parameter: prompt",
                    tool_name=self.name
                )
            
            # Validate and normalize URL
            normalized_url = self._normalize_url(url)
            if not normalized_url:
                return ToolResult.error_result(
                    error=f"Invalid URL: {url}",
                    tool_name=self.name
                )
            
            # Fetch content
            content_result = await self._fetch_content(normalized_url)
            
            if not content_result["success"]:
                return ToolResult.error_result(
                    error=content_result["error"],
                    tool_name=self.name
                )
            
            content = content_result["content"]
            content_type = content_result.get("content_type", "text/html")
            
            # Convert HTML to markdown if needed
            if "text/html" in content_type:
                markdown_content = self._html_to_markdown(content)
            else:
                markdown_content = content
            
            # Process with AI model using the prompt
            processed_result = await self._process_with_ai(markdown_content, prompt, context)
            
            return ToolResult.success_result(
                data={
                    "url": normalized_url,
                    "original_url": url,
                    "prompt": prompt,
                    "content_type": content_type,
                    "content_length": len(content),
                    "processed_response": processed_result,
                    "raw_content": content[:1000] + "..." if len(content) > 1000 else content
                },
                tool_name=self.name,
                output=processed_result
            )
            
        except Exception as e:
            return ToolResult.error_result(
                error=f"WebFetch tool execution failed: {str(e)}",
                tool_name=self.name
            )
    
    def _normalize_url(self, url: str) -> Optional[str]:
        """Normalize and validate URL."""
        try:
            # Auto-upgrade HTTP to HTTPS if specified
            if url.startswith("http://"):
                url = url.replace("http://", "https://", 1)
            
            # Add https:// if no protocol specified
            if not url.startswith(("http://", "https://")):
                url = "https://" + url
            
            # Parse and validate
            parsed = urlparse(url)
            if not parsed.netloc:
                return None
            
            return url
            
        except Exception:
            return None
    
    async def _fetch_content(self, url: str) -> dict:
        """Fetch content from URL."""
        try:
            timeout = aiohttp.ClientTimeout(total=30)
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
                async with session.get(url) as response:
                    # Check for redirects to different hosts
                    if str(response.url) != url:
                        final_host = urlparse(str(response.url)).netloc
                        original_host = urlparse(url).netloc
                        
                        if final_host != original_host:
                            return {
                                "success": False,
                                "error": f"Redirect to different host detected. Original: {original_host}, Redirect: {final_host}. Use the redirect URL: {response.url}"
                            }
                    
                    if response.status != 200:
                        return {
                            "success": False,
                            "error": f"HTTP {response.status}: {response.reason}"
                        }
                    
                    content_type = response.headers.get('content-type', 'text/html')
                    content = await response.text()
                    
                    return {
                        "success": True,
                        "content": content,
                        "content_type": content_type,
                        "final_url": str(response.url)
                    }
                    
        except asyncio.TimeoutError:
            return {
                "success": False,
                "error": "Request timeout (30 seconds)"
            }
        except aiohttp.ClientError as e:
            return {
                "success": False,
                "error": f"Network error: {str(e)}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Fetch error: {str(e)}"
            }
    
    def _html_to_markdown(self, html_content: str) -> str:
        """Convert HTML to markdown (simplified version)."""
        try:
            # Try to use markdownify if available
            try:
                from markdownify import markdownify
                return markdownify(html_content, heading_style="ATX")
            except ImportError:
                pass
            
            # Fallback: simple HTML tag removal and formatting
            import re
            
            # Remove script and style tags completely
            html_content = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
            html_content = re.sub(r'<style[^>]*>.*?</style>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
            
            # Convert common tags
            html_content = re.sub(r'<h1[^>]*>(.*?)</h1>', r'# \1', html_content, flags=re.IGNORECASE)
            html_content = re.sub(r'<h2[^>]*>(.*?)</h2>', r'## \1', html_content, flags=re.IGNORECASE)
            html_content = re.sub(r'<h3[^>]*>(.*?)</h3>', r'### \1', html_content, flags=re.IGNORECASE)
            html_content = re.sub(r'<p[^>]*>(.*?)</p>', r'\1\n\n', html_content, flags=re.IGNORECASE)
            html_content = re.sub(r'<br[^>]*>', '\n', html_content, flags=re.IGNORECASE)
            html_content = re.sub(r'<strong[^>]*>(.*?)</strong>', r'**\1**', html_content, flags=re.IGNORECASE)
            html_content = re.sub(r'<b[^>]*>(.*?)</b>', r'**\1**', html_content, flags=re.IGNORECASE)
            html_content = re.sub(r'<em[^>]*>(.*?)</em>', r'*\1*', html_content, flags=re.IGNORECASE)
            html_content = re.sub(r'<i[^>]*>(.*?)</i>', r'*\1*', html_content, flags=re.IGNORECASE)
            
            # Remove remaining HTML tags
            html_content = re.sub(r'<[^>]+>', '', html_content)
            
            # Clean up whitespace
            html_content = re.sub(r'\n\s*\n\s*\n', '\n\n', html_content)
            html_content = re.sub(r'^\s+|\s+$', '', html_content, flags=re.MULTILINE)
            
            return html_content.strip()
            
        except Exception:
            # If all else fails, just strip HTML tags
            import re
            return re.sub(r'<[^>]+>', '', html_content)
    
    async def _process_with_ai(self, content: str, prompt: str, context: ToolContext) -> str:
        """Process content with AI model using the provided prompt."""
        try:
            # Get AI provider from context
            if context.provider:
                # Construct the processing prompt
                processing_prompt = f"""
Content from web page:
{content}

User request: {prompt}

Please analyze the content and respond to the user request about this web page content.
"""
                
                # Use the provider to process the content
                response = await context.provider.generate_text(processing_prompt)
                return response.strip()
            else:
                # Fallback: return a summary of the content with the prompt context
                content_preview = content[:2000] + "..." if len(content) > 2000 else content
                return f"Content fetched successfully. Here's what was requested ({prompt}):\n\n{content_preview}"
                
        except Exception as e:
            # Fallback on AI processing failure
            content_preview = content[:1000] + "..." if len(content) > 1000 else content
            return f"Content fetched but AI processing failed. Raw content preview:\n\n{content_preview}"


# Claude Code schema compatibility
CLAUDE_CODE_SCHEMA = {
    "type": "object",
    "properties": {
        "url": {
            "type": "string",
            "format": "uri",
            "description": "The URL to fetch content from"
        },
        "prompt": {
            "type": "string",
            "description": "The prompt to run on the fetched content"
        }
    },
    "required": ["url", "prompt"],
    "additionalProperties": False
}