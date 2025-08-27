#!/usr/bin/env python3
"""
Test script for MCP Filesystem Server integration in Codexa.

This script validates that the MCP filesystem server is properly integrated
and can perform secure file operations.
"""

import asyncio
import sys
import tempfile
import os
from pathlib import Path

# Add codexa to path
sys.path.insert(0, str(Path(__file__).parent))

from codexa.enhanced_core import EnhancedCodexaAgent
from codexa.filesystem import MCPFileSystem


async def test_mcp_filesystem():
    """Test MCP filesystem operations."""
    print("🧪 TESTING MCP FILESYSTEM SERVER OPERATIONS")
    print("=" * 50)
    
    # Set dummy API key for testing
    os.environ['OPENAI_API_KEY'] = 'test-key-for-mcp-testing'
    
    # Create enhanced agent
    try:
        agent = EnhancedCodexaAgent()
        print("✅ Enhanced Codexa Agent initialized")
    except Exception as e:
        print(f"❌ Failed to initialize agent: {e}")
        return False
    
    # Check if MCP service is running
    if not agent.mcp_service or not agent.mcp_service.is_running:
        print("⚠️  Starting MCP service...")
        try:
            if agent.mcp_service:
                await agent.mcp_service.start()
                print("✅ MCP service started")
            else:
                print("❌ MCP service not available")
                return False
        except Exception as e:
            print(f"❌ Failed to start MCP service: {e}")
            return False
    
    # Test MCP filesystem operations
    if not agent.mcp_filesystem:
        print("❌ MCP filesystem not available")
        return False
    
    print("\n🔍 Testing MCP filesystem operations...")
    
    # Test 1: Check server availability
    try:
        if agent.mcp_filesystem.is_server_available():
            print("✅ MCP filesystem server is available")
        else:
            print("❌ MCP filesystem server is not available")
            return False
    except Exception as e:
        print(f"❌ Error checking server availability: {e}")
        return False
    
    # Test 2: List allowed directories
    try:
        allowed_dirs = await agent.mcp_filesystem.list_allowed_directories()
        print(f"✅ Allowed directories: {len(allowed_dirs)} paths")
        for dir_path in allowed_dirs:
            print(f"   - {dir_path}")
    except Exception as e:
        print(f"❌ Failed to list allowed directories: {e}")
        return False
    
    # Test 3: Test basic file operations with temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp_file:
        tmp_path = tmp_file.name
        test_content = "Hello from MCP Filesystem Test!"
        tmp_file.write(test_content)
    
    try:
        # Test read_file
        content = await agent.mcp_filesystem.read_file(tmp_path)
        if content.strip() == test_content:
            print("✅ File read operation successful")
        else:
            print(f"❌ File read mismatch: expected '{test_content}', got '{content.strip()}'")
            return False
            
        # Test get_file_info
        file_info = await agent.mcp_filesystem.get_file_info(tmp_path)
        print(f"✅ File info retrieved: {file_info.get('size', 'unknown')} bytes")
        
        # Test modify_file
        modification_result = await agent.mcp_filesystem.modify_file(
            tmp_path, "Hello", "Greetings"
        )
        print(f"✅ File modification: {modification_result.get('changes_made', 0)} changes made")
        
        # Verify modification
        modified_content = await agent.mcp_filesystem.read_file(tmp_path)
        if "Greetings" in modified_content:
            print("✅ File modification verified")
        else:
            print("❌ File modification verification failed")
            return False
            
    except Exception as e:
        print(f"❌ File operations failed: {e}")
        return False
    finally:
        # Cleanup
        try:
            os.unlink(tmp_path)
        except:
            pass
    
    # Test 4: Directory operations
    try:
        # List current directory
        entries = await agent.mcp_filesystem.list_directory(Path.cwd())
        print(f"✅ Directory listing: {len(entries)} entries")
        
        # Get directory tree (limited depth)
        tree = await agent.mcp_filesystem.get_directory_tree(Path.cwd(), depth=1)
        print(f"✅ Directory tree: {len(tree)} items")
        
    except Exception as e:
        print(f"❌ Directory operations failed: {e}")
        return False
    
    # Test 5: Search operations
    try:
        # Search for Python files
        py_files = await agent.mcp_filesystem.search_files(Path.cwd(), "*.py")
        print(f"✅ File search: found {len(py_files)} Python files")
        
        # Search within files (limited results)
        content_matches = await agent.mcp_filesystem.search_within_files(
            Path.cwd(), "import", max_results=5
        )
        print(f"✅ Content search: found {len(content_matches)} files with 'import'")
        
    except Exception as e:
        print(f"❌ Search operations failed: {e}")
        return False
    
    # Test 6: Multiple file operations
    try:
        # Create test files
        test_files = []
        test_dir = Path(tempfile.mkdtemp())
        
        for i in range(3):
            test_file = test_dir / f"test_{i}.txt"
            test_file.write_text(f"Test file {i} content")
            test_files.append(str(test_file))
        
        # Read multiple files
        multi_content = await agent.mcp_filesystem.read_multiple_files(test_files)
        if len(multi_content) == 3:
            print("✅ Multiple file read operation successful")
        else:
            print(f"❌ Multiple file read failed: got {len(multi_content)} files, expected 3")
            return False
            
    except Exception as e:
        print(f"❌ Multiple file operations failed: {e}")
        return False
    finally:
        # Cleanup test directory
        try:
            import shutil
            shutil.rmtree(test_dir, ignore_errors=True)
        except:
            pass
    
    # Test 7: Validate server health
    try:
        server_healthy = await agent.mcp_filesystem.validate_server()
        if server_healthy:
            print("✅ MCP filesystem server health validation passed")
        else:
            print("❌ MCP filesystem server health validation failed")
            return False
    except Exception as e:
        print(f"❌ Server health validation error: {e}")
        return False
    
    print("\n🎉 All MCP filesystem tests passed!")
    return True


async def main():
    """Main test function."""
    try:
        success = await test_mcp_filesystem()
        if success:
            print("\n✅ MCP Filesystem integration is working correctly!")
            sys.exit(0)
        else:
            print("\n❌ MCP Filesystem integration has issues.")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n⚠️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error during testing: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    print("MCP Filesystem Server Integration Test")
    print("Note: This test requires the mcp-filesystem-server to be installed")
    print("Install with: go install github.com/mark3labs/mcp-filesystem-server@latest")
    print("-" * 60)
    
    asyncio.run(main())