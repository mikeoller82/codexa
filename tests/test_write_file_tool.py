import asyncio
import os
import unittest
from pathlib import Path

# Adjust import paths to be relative to the tests/ directory
from codexa.enhanced_core import EnhancedCodexaAgent
from codexa.tools.base.tool_interface import ToolContext

# --- Self-Contained Mock Provider ---
class MockProvider:
    """A mock AI provider for testing, kept within the test file."""
    def __init__(self, config=None):
        pass

    async def ask_async(self, prompt: str, history=None, context=None) -> str:
        # The mock's response is not critical for this direct tool test.
        return "This is a mock response."

    def __str__(self):
        return "mock"

# --- Test Case ---
class TestWriteFileTool(unittest.TestCase):
    """
    Integration test for the WriteFileTool.
    This test validates that the tool can be executed directly and correctly
    creates a file with the specified content.
    """

    def setUp(self):
        """Set up the test environment."""
        self.test_file_name = "test_write_file_tool_output.txt"
        self.test_file_content = "Hello from the integration test!"
        self.agent = None

    def tearDown(self):
        """Clean up after the test."""
        if os.path.exists(self.test_file_name):
            os.remove(self.test_file_name)
        # The agent shutdown is handled within the async test runner.

    def run_async_test(self, test_coro):
        """Helper to run an async test method."""
        loop = asyncio.get_event_loop()
        loop.run_until_complete(test_coro)

    def test_write_file_tool_execution(self):
        """
        Tests the direct execution of the 'write_file' tool.
        """
        self.run_async_test(self.async_test_write_file())

    async def async_test_write_file(self):
        """
        The core async logic for the test.
        """
        # 1. Initialize the agent with the mock provider
        mock_provider = MockProvider()
        self.agent = EnhancedCodexaAgent(provider=mock_provider)

        # 2. Prepare context with the correct arguments
        context = ToolContext(
            tool_manager=self.agent.tool_manager,
            mcp_service=self.agent.mcp_service,
            config=self.agent.config,
            current_path=str(self.agent.cwd),
            user_request="test_prompt",
            provider=self.agent.provider
        )
        context.update_state("file_path", self.test_file_name)
        context.update_state("content", self.test_file_content)

        # 3. Execute the tool directly
        result = await self.agent.tool_manager.execute_tool(
            tool_name='write_file',
            context=context
        )

        # 4. Assert the result of the tool execution
        self.assertTrue(result.success, f"Tool execution failed: {result.error}")
        self.assertIn(self.test_file_name, result.files_created)

        # 5. Verify the file was created with the correct content
        self.assertTrue(os.path.exists(self.test_file_name), "Test file was not created.")
        with open(self.test_file_name, "r") as f:
            content = f.read()
        self.assertEqual(content, self.test_file_content, "File content does not match expected content.")

        # 6. Gracefully shut down the agent
        if self.agent:
            await self.agent.shutdown()

if __name__ == '__main__':
    unittest.main()