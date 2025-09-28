from typing import Optional
from enum import Enum


class ErrorType(Enum):
    LEXICAL = "lexical"
    SYNTAX = "syntax"
    SEMANTIC = "semantic"
    TYPE = "type"
    RUNTIME = "runtime"


class CompilerError:
    def __init__(self, message: str, line: int = 0, column: int = 0, 
                 error_type: ErrorType = ErrorType.SEMANTIC, filename: str = ""):
        self.message = message
        self.line = line
        self.column = column
        self.error_type = error_type
        self.filename = filename
    
    def __str__(self) -> str:
        location = ""
        if self.filename:
            location = f"{self.filename}:"
        if self.line > 0:
            location += f"{self.line}:"
        if self.column > 0:
            location += f"{self.column}:"
        
        if location:
            return f"{location} [{self.error_type.value}] {self.message}"
        else:
            return f"[{self.error_type.value}] {self.message}"
    
    def to_dict(self) -> dict:
        return {
            "message": self.message,
            "line": self.line,
            "column": self.column,
            "type": self.error_type.value,
            "filename": self.filename
        }


class ErrorCollector:
    def __init__(self):
        self.errors = []
        self.warnings = []
    
    def add_error(self, message: str, line: int = 0, column: int = 0, 
                  error_type: ErrorType = ErrorType.SEMANTIC, filename: str = ""):
        error = CompilerError(message, line, column, error_type, filename)
        self.errors.append(error)
    
    def add_warning(self, message: str, line: int = 0, column: int = 0, filename: str = ""):
        warning = CompilerError(message, line, column, ErrorType.SEMANTIC, filename)
        self.warnings.append(warning)
    
    def has_errors(self) -> bool:
        return len(self.errors) > 0
    
    def has_warnings(self) -> bool:
        return len(self.warnings) > 0
    
    def get_error_count(self) -> int:
        return len(self.errors)
    
    def get_warning_count(self) -> int:
        return len(self.warnings)
    
    def clear(self):
        self.errors.clear()
        self.warnings.clear()
    
    def to_dict(self) -> dict:
        return {
            "errors": [error.to_dict() for error in self.errors],
            "warnings": [warning.to_dict() for warning in self.warnings],
            "error_count": len(self.errors),
            "warning_count": len(self.warnings)
        }