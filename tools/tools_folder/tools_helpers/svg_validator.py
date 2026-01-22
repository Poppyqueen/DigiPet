

from lxml import etree
from pathlib import Path
from typing import Union, Dict, Any


class SVGValidator:
    """Simple SVG validator focusing on XML syntax validation"""
    
    def __init__(self, max_size_mb: int = 10):
        """
        Initialize validator
        
        Args:
            max_size_mb: Maximum file size in megabytes
        """
        self.max_size = max_size_mb * 1024 * 1024
    
    def validate_string(self, svg_string: str) -> Dict[str, Any]:
        """
        Validate SVG from string
        
        Args:
            svg_string: SVG content as string
            
        Returns:
            dict: {"valid": bool, "error": str, "line": int, "column": int}
        """
        if not svg_string:
            return {"valid": False, "error": "Empty string"}
        
        # Check size
        size = len(svg_string.encode('utf-8'))
        if size > self.max_size:
            return {
                "valid": False,
                "error": f"SVG too large: {size} bytes (max: {self.max_size})"
            }
        
        # Validate XML
        try:
            etree.fromstring(svg_string.encode('utf-8'))
            return {"valid": True}
        except etree.XMLSyntaxError as e:
            return {
                "valid": False,
                "error": str(e),
                "line": e.lineno,
                "column": e.offset
            }
        except Exception as e:
            return {
                "valid": False,
                "error": f"Parse error: {str(e)}"
            }
    
    def validate_file(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Validate SVG from file
        
        Args:
            file_path: Path to SVG file
            
        Returns:
            dict: {"valid": bool, "error": str, "line": int, "column": int}
        """
        path = Path(file_path)
        
        if not path.exists():
            return {"valid": False, "error": f"File not found: {file_path}"}
        
        if path.stat().st_size > self.max_size:
            return {
                "valid": False,
                "error": f"File too large (max: {self.max_size} bytes)"
            }
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return self.validate_string(f.read())
        except UnicodeDecodeError:
            return {"valid": False, "error": "File is not valid UTF-8"}
        except Exception as e:
            return {"valid": False, "error": f"Failed to read file: {str(e)}"}
    
    def validate_bytes(self, svg_bytes: bytes) -> Dict[str, Any]:
        """
        Validate SVG from bytes
        
        Args:
            svg_bytes: SVG content as bytes
            
        Returns:
            dict: {"valid": bool, "error": str, "line": int, "column": int}
        """
        if not svg_bytes:
            return {"valid": False, "error": "Empty bytes"}
        
        try:
            svg_string = svg_bytes.decode('utf-8')
            return self.validate_string(svg_string)
        except UnicodeDecodeError:
            return {"valid": False, "error": "Bytes are not valid UTF-8"}
    
    def is_valid(self, svg_input: Union[str, Path, bytes]) -> bool:
        """
        Quick boolean check if SVG is valid
        
        Args:
            svg_input: SVG content as string, file path, or bytes
            
        Returns:
            bool: True if valid, False otherwise
        """
        return self.validate(svg_input)["valid"]
