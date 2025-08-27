"""
File Validation Tool for Codexa.
"""

from pathlib import Path
from typing import Set, Dict, Any, List
import re
import hashlib
import mimetypes

from ..base.tool_interface import Tool, ToolResult, ToolContext


class FileValidationTool(Tool):
    """Tool for validating file integrity, format, and properties."""
    
    @property
    def name(self) -> str:
        return "file_validation"
    
    @property
    def description(self) -> str:
        return "Validate file integrity, format, and properties"
    
    @property
    def category(self) -> str:
        return "filesystem"
    
    @property
    def capabilities(self) -> Set[str]:
        return {"validate", "verify", "check", "integrity", "format_check"}
    
    @property
    def required_context(self) -> Set[str]:
        return {"file_path"}
    
    def can_handle_request(self, request: str, context: ToolContext) -> float:
        """Check if this tool can handle the request."""
        request_lower = request.lower()
        
        # High confidence for explicit validation requests
        if any(phrase in request_lower for phrase in [
            "validate file", "verify file", "check file", "file validation",
            "file integrity", "validate format", "check format"
        ]):
            return 0.9
        
        # Medium confidence for validation keywords
        if any(word in request_lower for word in ["validate", "verify", "check"]) and \
           any(word in request_lower for word in ["file", "format", "integrity"]):
            return 0.7
        
        return 0.0
    
    async def execute(self, context: ToolContext) -> ToolResult:
        """Execute file validation."""
        try:
            # Get parameters from context
            file_path = context.get_state("file_path")
            validation_types = context.get_state("validation_types", ["existence", "format", "integrity"])
            
            # Try to extract from request if not in context
            if not file_path:
                extracted = self._extract_validation_parameters(context.user_request)
                file_path = extracted.get("file_path")
                if extracted.get("validation_types"):
                    validation_types = extracted["validation_types"]
            
            if not file_path:
                return ToolResult.error_result(
                    error="No file path specified",
                    tool_name=self.name
                )
            
            # Run validations
            validation_results = await self._validate_file(file_path, validation_types)
            
            # Determine overall success
            overall_success = all(result["passed"] for result in validation_results.values())
            
            return ToolResult.success_result(
                data={
                    "file_path": file_path,
                    "overall_valid": overall_success,
                    "validations": validation_results,
                    "validation_count": len(validation_results)
                },
                tool_name=self.name,
                output=f"File validation: {'PASSED' if overall_success else 'FAILED'} ({file_path})"
            )
            
        except Exception as e:
            return ToolResult.error_result(
                error=f"Failed to validate file: {str(e)}",
                tool_name=self.name
            )
    
    async def _validate_file(self, file_path: str, validation_types: List[str]) -> Dict[str, Dict[str, Any]]:
        """Run specified validations on file."""
        path = Path(file_path)
        results = {}
        
        for validation_type in validation_types:
            if validation_type == "existence":
                results["existence"] = self._validate_existence(path)
            elif validation_type == "format":
                results["format"] = self._validate_format(path)
            elif validation_type == "integrity":
                results["integrity"] = self._validate_integrity(path)
            elif validation_type == "permissions":
                results["permissions"] = self._validate_permissions(path)
            elif validation_type == "size":
                results["size"] = self._validate_size(path)
            elif validation_type == "encoding":
                results["encoding"] = self._validate_encoding(path)
        
        return results
    
    def _validate_existence(self, path: Path) -> Dict[str, Any]:
        """Validate file existence and basic properties."""
        result = {
            "validation": "existence",
            "passed": False,
            "details": {},
            "errors": []
        }
        
        try:
            if not path.exists():
                result["errors"].append("File does not exist")
                return result
            
            result["details"]["exists"] = True
            result["details"]["is_file"] = path.is_file()
            result["details"]["is_directory"] = path.is_dir()
            result["details"]["is_symlink"] = path.is_symlink()
            
            if path.is_symlink():
                try:
                    result["details"]["symlink_target"] = str(path.readlink())
                    result["details"]["symlink_valid"] = path.exists()
                except OSError:
                    result["errors"].append("Cannot read symlink target")
            
            # Basic accessibility check
            try:
                path.stat()
                result["details"]["accessible"] = True
            except (PermissionError, OSError) as e:
                result["errors"].append(f"File not accessible: {e}")
                result["details"]["accessible"] = False
            
            result["passed"] = len(result["errors"]) == 0
            
        except Exception as e:
            result["errors"].append(f"Existence validation failed: {e}")
        
        return result
    
    def _validate_format(self, path: Path) -> Dict[str, Any]:
        """Validate file format and MIME type."""
        result = {
            "validation": "format",
            "passed": False,
            "details": {},
            "errors": []
        }
        
        try:
            if not path.exists() or not path.is_file():
                result["errors"].append("File does not exist or is not a file")
                return result
            
            # Get MIME type
            mime_type, encoding = mimetypes.guess_type(str(path))
            result["details"]["mime_type"] = mime_type
            result["details"]["encoding"] = encoding
            result["details"]["extension"] = path.suffix.lower()
            
            # Check file signature (magic bytes)
            try:
                with open(path, 'rb') as f:
                    header = f.read(16)
                    result["details"]["file_signature"] = self._identify_file_signature(header)
            except (OSError, PermissionError):
                result["errors"].append("Cannot read file header")
            
            # Validate extension matches content
            if mime_type and path.suffix:
                expected_extensions = mimetypes.guess_all_extensions(mime_type)
                if path.suffix.lower() not in expected_extensions:
                    result["errors"].append(f"Extension {path.suffix} doesn't match MIME type {mime_type}")
            
            result["passed"] = len(result["errors"]) == 0
            
        except Exception as e:
            result["errors"].append(f"Format validation failed: {e}")
        
        return result
    
    def _validate_integrity(self, path: Path) -> Dict[str, Any]:
        """Validate file integrity using checksums."""
        result = {
            "validation": "integrity",
            "passed": False,
            "details": {},
            "errors": []
        }
        
        try:
            if not path.exists() or not path.is_file():
                result["errors"].append("File does not exist or is not a file")
                return result
            
            # Calculate checksums
            try:
                with open(path, 'rb') as f:
                    content = f.read()
                    
                result["details"]["file_size"] = len(content)
                result["details"]["md5"] = hashlib.md5(content).hexdigest()
                result["details"]["sha256"] = hashlib.sha256(content).hexdigest()
                
                # Basic corruption checks
                if len(content) == 0:
                    result["errors"].append("File is empty")
                
                # Check for obvious corruption patterns
                if content == b'\x00' * len(content):
                    result["errors"].append("File appears to be zeroed (possible corruption)")
                
            except (OSError, PermissionError) as e:
                result["errors"].append(f"Cannot read file for integrity check: {e}")
            
            result["passed"] = len(result["errors"]) == 0
            
        except Exception as e:
            result["errors"].append(f"Integrity validation failed: {e}")
        
        return result
    
    def _validate_permissions(self, path: Path) -> Dict[str, Any]:
        """Validate file permissions."""
        result = {
            "validation": "permissions",
            "passed": False,
            "details": {},
            "errors": []
        }
        
        try:
            if not path.exists():
                result["errors"].append("File does not exist")
                return result
            
            stat = path.stat()
            mode = stat.st_mode
            
            result["details"]["mode_octal"] = oct(mode)[-3:]
            result["details"]["owner_read"] = bool(mode & 0o400)
            result["details"]["owner_write"] = bool(mode & 0o200)
            result["details"]["owner_execute"] = bool(mode & 0o100)
            result["details"]["group_read"] = bool(mode & 0o040)
            result["details"]["group_write"] = bool(mode & 0o020)
            result["details"]["group_execute"] = bool(mode & 0o010)
            result["details"]["other_read"] = bool(mode & 0o004)
            result["details"]["other_write"] = bool(mode & 0o002)
            result["details"]["other_execute"] = bool(mode & 0o001)
            
            # Check for potential security issues
            if result["details"]["other_write"]:
                result["errors"].append("File is world-writable (security risk)")
            
            result["passed"] = len(result["errors"]) == 0
            
        except Exception as e:
            result["errors"].append(f"Permission validation failed: {e}")
        
        return result
    
    def _validate_size(self, path: Path) -> Dict[str, Any]:
        """Validate file size constraints."""
        result = {
            "validation": "size",
            "passed": True,
            "details": {},
            "errors": []
        }
        
        try:
            if not path.exists() or not path.is_file():
                result["errors"].append("File does not exist or is not a file")
                result["passed"] = False
                return result
            
            size = path.stat().st_size
            result["details"]["size_bytes"] = size
            result["details"]["size_human"] = self._format_size(size)
            
            # Size-based warnings
            if size == 0:
                result["errors"].append("File is empty")
            elif size > 100 * 1024 * 1024:  # 100MB
                result["errors"].append("File is very large (>100MB)")
            
            result["passed"] = len(result["errors"]) == 0
            
        except Exception as e:
            result["errors"].append(f"Size validation failed: {e}")
            result["passed"] = False
        
        return result
    
    def _validate_encoding(self, path: Path) -> Dict[str, Any]:
        """Validate text file encoding."""
        result = {
            "validation": "encoding",
            "passed": False,
            "details": {},
            "errors": []
        }
        
        try:
            if not path.exists() or not path.is_file():
                result["errors"].append("File does not exist or is not a file")
                return result
            
            # Try different encodings
            encodings_to_try = ['utf-8', 'latin-1', 'cp1252', 'ascii']
            successful_encodings = []
            
            for encoding in encodings_to_try:
                try:
                    with open(path, 'r', encoding=encoding) as f:
                        content = f.read(8192)  # Read sample
                        successful_encodings.append(encoding)
                except UnicodeDecodeError:
                    continue
            
            result["details"]["valid_encodings"] = successful_encodings
            result["details"]["likely_encoding"] = successful_encodings[0] if successful_encodings else None
            
            if not successful_encodings:
                result["errors"].append("File cannot be decoded with common text encodings (likely binary)")
            
            result["passed"] = len(successful_encodings) > 0
            
        except Exception as e:
            result["errors"].append(f"Encoding validation failed: {e}")
        
        return result
    
    def _identify_file_signature(self, header: bytes) -> str:
        """Identify file type from magic bytes."""
        signatures = {
            b'\x89PNG\r\n\x1a\n': 'PNG',
            b'\xff\xd8\xff': 'JPEG',
            b'GIF87a': 'GIF87a',
            b'GIF89a': 'GIF89a',
            b'%PDF': 'PDF',
            b'\x50\x4b\x03\x04': 'ZIP/Office',
            b'\x50\x4b\x05\x06': 'ZIP/Office',
            b'\x50\x4b\x07\x08': 'ZIP/Office',
            b'\x1f\x8b\x08': 'GZIP',
            b'BZh': 'BZIP2',
            b'\x00\x00\x01\x00': 'ICO'
        }
        
        for signature, file_type in signatures.items():
            if header.startswith(signature):
                return file_type
        
        # Check for text files
        try:
            header.decode('utf-8')
            return 'Text'
        except UnicodeDecodeError:
            return 'Unknown'
    
    def _format_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format."""
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        size = float(size_bytes)
        
        while size >= 1024.0 and i < len(size_names) - 1:
            size /= 1024.0
            i += 1
        
        return f"{size:.1f} {size_names[i]}"
    
    def _extract_validation_parameters(self, request: str) -> Dict[str, Any]:
        """Extract validation parameters from request."""
        result = {
            "file_path": "",
            "validation_types": []
        }
        
        # Extract file path
        file_pattern = r'([a-zA-Z0-9_/.-]+\.[a-zA-Z0-9]+)'
        matches = re.findall(file_pattern, request)
        if matches:
            result["file_path"] = matches[0]
        
        # Extract validation types
        request_lower = request.lower()
        if "integrity" in request_lower:
            result["validation_types"].append("integrity")
        if "format" in request_lower:
            result["validation_types"].append("format")
        if "permission" in request_lower:
            result["validation_types"].append("permissions")
        if "size" in request_lower:
            result["validation_types"].append("size")
        if "encoding" in request_lower:
            result["validation_types"].append("encoding")
        
        # Default validations if none specified
        if not result["validation_types"]:
            result["validation_types"] = ["existence", "format", "integrity"]
        
        return result