#!/usr/bin/env python3
"""
SmartArb Engine - Automatic Import Fix Script
Automatically detects and fixes missing import issues across the entire project
"""

import ast
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict
import argparse
import logging
from dataclasses import dataclass

logger = structlog.get_logger(__name__)


# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class ImportIssue:
    """Represents an import issue found in a file"""
    file_path: str
    line_number: int
    issue_type: str
    missing_import: str
    suggested_fix: str
    context: str

@dataclass
class FixResult:
    """Result of applying a fix"""
    file_path: str
    fixes_applied: int
    backup_created: bool
    success: bool
    error_message: Optional[str] = None

class ImportAnalyzer:
    """Analyzes Python files for missing imports"""
    
    def __init__(self):
        # Common missing imports and their fixes
        self.COMMON_IMPORTS = {
            # Standard library
            'time': 'import time',
            'sys': 'import sys',
            'os': 'import os',
            'json': 'import json',
            'logging': 'import logging',
            'datetime': 'from datetime import datetime, timedelta',
            'asyncio': 'import asyncio',
            'traceback': 'import traceback',
            'signal': 'import signal',
            'pathlib': 'from pathlib import Path',
            'typing': 'from typing import Dict, Any, List, Optional, Tuple',
            'dataclasses': 'from dataclasses import dataclass',
            'enum': 'from enum import Enum',
            'decimal': 'from decimal import Decimal',
            'collections': 'from collections import defaultdict, deque',
            
            # Third-party common
            'structlog': 'import structlog',
            'psutil': 'import psutil',
            'aiohttp': 'import aiohttp',
            'asyncpg': 'import asyncpg',
            'redis': 'import redis.asyncio as redis',
            'pandas': 'import pandas as pd',
            'numpy': 'import numpy as np',
            'ccxt': 'import ccxt',
            'pydantic': 'from pydantic import BaseModel, validator',
            'fastapi': 'from fastapi import FastAPI, HTTPException',
            'pytest': 'import pytest',
            
            # SmartArb specific patterns
            'logger': 'logger = structlog.get_logger(__name__)',
        }
        
        # Patterns for detecting missing imports
        self.USAGE_PATTERNS = {
            r'\btime\.': 'time',
            r'\bsys\.': 'sys',
            r'\bos\.': 'os',
            r'\bjson\.': 'json',
            r'\blogging\.': 'logging',
            r'\bdatetime\.': 'datetime',
            r'\basyncio\.': 'asyncio',
            r'\btraceback\.': 'traceback',
            r'\bsignal\.': 'signal',
            r'\bPath\(': 'pathlib',
            r'\bDecimal\(': 'decimal',
            r'\bdefaultdict\(': 'collections',
            r'\b@dataclass': 'dataclasses',
            r'\bEnum\b': 'enum',
            r'\bstructlog\.': 'structlog',
            r'\bpsutil\.': 'psutil',
            r'\baiohttp\.': 'aiohttp',
            r'\basyncpg\.': 'asyncpg',
            r'\bredis\.': 'redis',
            r'\bpd\.': 'pandas',
            r'\bnp\.': 'numpy',
            r'\bccxt\.': 'ccxt',
            r'\bBaseModel\b': 'pydantic',
            r'\bFastAPI\b': 'fastapi',
            r'\bpytest\.': 'pytest',
            r'\blogger\.': 'logger',
        }
    
    def analyze_file(self, file_path: str) -> List[ImportIssue]:
        """Analyze a single Python file for missing imports"""
        issues = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.splitlines()
            
            # Parse the AST to get existing imports
            try:
                tree = ast.parse(content, filename=file_path)
                existing_imports = self._extract_imports(tree)
            except SyntaxError as e:
                logger.warning(f"Syntax error in {file_path}: {e}")
                return issues
            
            # Check for missing imports based on usage patterns
            for line_num, line in enumerate(lines, 1):
                for pattern, module in self.USAGE_PATTERNS.items():
                    if re.search(pattern, line) and module not in existing_imports:
                        # Check if this usage is within a string or comment
                        if self._is_in_string_or_comment(line, pattern):
                            continue
                        
                        issue = ImportIssue(
                            file_path=file_path,
                            line_number=line_num,
                            issue_type='missing_import',
                            missing_import=module,
                            suggested_fix=self.COMMON_IMPORTS.get(module, f'import {module}'),
                            context=line.strip()
                        )
                        
                        # Avoid duplicate issues
                        if not any(i.missing_import == module for i in issues):
                            issues.append(issue)
            
            # Check for common SmartArb patterns
            issues.extend(self._check_smartarb_patterns(file_path, lines, existing_imports))
            
        except Exception as e:
            logger.error(f"Error analyzing {file_path}: {e}")
        
        return issues
    
    def _extract_imports(self, tree: ast.AST) -> Set[str]:
        """Extract all imports from an AST"""
        imports = set()
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name)
                    # Also add the base module name
                    imports.add(alias.name.split('.')[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module)
                    imports.add(node.module.split('.')[0])
                for alias in node.names:
                    imports.add(alias.name)
        
        return imports
    
    def _is_in_string_or_comment(self, line: str, pattern: str) -> bool:
        """Check if a pattern match is within a string or comment"""
        # Simple heuristic - check if the match is after # or within quotes
        match = re.search(pattern, line)
        if not match:
            return False
        
        match_pos = match.start()
        
        # Check if it's in a comment
        comment_pos = line.find('#')
        if comment_pos != -1 and match_pos > comment_pos:
            return True
        
        # Check if it's in a string (basic check)
        before_match = line[:match_pos]
        single_quotes = before_match.count("'")
        double_quotes = before_match.count('"')
        
        # If odd number of quotes before match, likely in string
        if (single_quotes % 2 == 1) or (double_quotes % 2 == 1):
            return True
        
        return False
    
    def _check_smartarb_patterns(self, file_path: str, lines: List[str], existing_imports: Set[str]) -> List[ImportIssue]:
        """Check for SmartArb-specific import patterns"""
        issues = []
        
        # Check for logger usage without proper import
        for line_num, line in enumerate(lines, 1):
            if 'logger.' in line and 'structlog' not in existing_imports and 'logging' not in existing_imports:
                if not any(i.missing_import == 'logger' for i in issues):
                    issues.append(ImportIssue(
                        file_path=file_path,
                        line_number=line_num,
                        issue_type='missing_logger',
                        missing_import='logger',
                        suggested_fix='import structlog\nlogger = structlog.get_logger(__name__)',
                        context=line.strip()
                    ))
        
        # Check for SmartArb internal imports
        if 'src/' in file_path:
            for line_num, line in enumerate(lines, 1):
                # Check for missing SmartArb module imports
                if 'from src.' in line or 'import src.' in line:
                    continue
                
                # Look for usage of SmartArb classes without imports
                smartarb_patterns = [
                    (r'\bEngineState\b', 'from src.core.engine import EngineState'),
                    (r'\bBaseExchange\b', 'from src.exchanges.base import BaseExchange'),
                    (r'\bRiskManager\b', 'from src.risk.manager import RiskManager'),
                    (r'\bConfigManager\b', 'from src.utils.config import ConfigManager'),
                    (r'\bArbitrageStrategy\b', 'from src.strategies.arbitrage import ArbitrageStrategy'),
                ]
                
                for pattern, suggested_import in smartarb_patterns:
                    if re.search(pattern, line) and suggested_import not in existing_imports:
                        issues.append(ImportIssue(
                            file_path=file_path,
                            line_number=line_num,
                            issue_type='missing_smartarb_import',
                            missing_import=pattern.strip('\\b'),
                            suggested_fix=suggested_import,
                            context=line.strip()
                        ))
        
        return issues

class ImportFixer:
    """Fixes import issues in Python files"""
    
    def __init__(self, dry_run: bool = False, create_backup: bool = True):
        self.dry_run = dry_run
        self.create_backup = create_backup
    
    def fix_file(self, file_path: str, issues: List[ImportIssue]) -> FixResult:
        """Fix import issues in a single file"""
        if not issues:
            return FixResult(file_path, 0, False, True)
        
        try:
            # Read the file
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.splitlines()
            
            # Create backup if requested
            backup_created = False
            if self.create_backup and not self.dry_run:
                backup_path = f"{file_path}.backup"
                with open(backup_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                backup_created = True
                logger.info(f"Created backup: {backup_path}")
            
            # Group issues by import type
            imports_to_add = {}
            for issue in issues:
                imports_to_add[issue.missing_import] = issue.suggested_fix
            
            # Find the best place to insert imports
            insert_line = self._find_import_insertion_point(lines)
            
            # Add missing imports
            new_imports = []
            for import_name, import_statement in imports_to_add.items():
                # Handle multi-line imports
                if '\n' in import_statement:
                    new_imports.extend(import_statement.split('\n'))
                else:
                    new_imports.append(import_statement)
            
            # Insert the new imports
            if new_imports:
                # Remove duplicates while preserving order
                seen = set()
                unique_imports = []
                for imp in new_imports:
                    if imp not in seen and imp.strip():
                        unique_imports.append(imp)
                        seen.add(imp)
                
                # Add empty line before imports if needed
                if insert_line > 0 and lines[insert_line - 1].strip():
                    unique_imports.insert(0, '')
                
                # Add empty line after imports
                unique_imports.append('')
                
                # Insert imports
                lines[insert_line:insert_line] = unique_imports
            
            # Write the fixed content
            if not self.dry_run:
                new_content = '\n'.join(lines)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                
                logger.info(f"Fixed {len(issues)} import issues in {file_path}")
            else:
                logger.info(f"[DRY RUN] Would fix {len(issues)} import issues in {file_path}")
            
            return FixResult(
                file_path=file_path,
                fixes_applied=len(issues),
                backup_created=backup_created,
                success=True
            )
            
        except Exception as e:
            logger.error(f"Error fixing {file_path}: {e}")
            return FixResult(
                file_path=file_path,
                fixes_applied=0,
                backup_created=False,
                success=False,
                error_message=str(e)
            )
    
    def _find_import_insertion_point(self, lines: List[str]) -> int:
        """Find the best line to insert imports"""
        # Look for existing imports and docstrings
        in_docstring = False
        docstring_quotes = None
        last_import_line = -1
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # Handle docstrings
            if not in_docstring:
                if stripped.startswith('"""') or stripped.startswith("'''"):
                    docstring_quotes = stripped[:3]
                    if stripped.count(docstring_quotes) == 1:  # Opening docstring
                        in_docstring = True
                    continue
            else:
                if docstring_quotes in line:
                    in_docstring = False
                    docstring_quotes = None
                    continue
            
            if in_docstring:
                continue
            
            # Skip comments and empty lines at the top
            if stripped.startswith('#') or not stripped:
                continue
            
            # Skip shebang
            if stripped.startswith('#!'):
                continue
            
            # Check for imports
            if (stripped.startswith('import ') or 
                stripped.startswith('from ') or
                stripped.startswith('try:') or  # Handle try/except imports
                stripped.startswith('except')):
                last_import_line = i
                continue
            
            # If we hit non-import code, stop
            if stripped and not stripped.startswith('#'):
                break
        
        # Insert after the last import, or at the beginning if no imports
        return last_import_line + 1 if last_import_line >= 0 else 0

def scan_project(project_path: str, extensions: List[str] = None) -> Dict[str, List[ImportIssue]]:
    """Scan entire project for import issues"""
    if extensions is None:
        extensions = ['.py']
    
    analyzer = ImportAnalyzer()
    all_issues = {}
    
    project_root = Path(project_path)
    
    # Find all Python files
    python_files = []
    for ext in extensions:
        python_files.extend(project_root.rglob(f'*{ext}'))
    
    # Filter out unwanted directories
    excluded_dirs = {'.git', '__pycache__', '.pytest_cache', 'venv', '.venv', 'node_modules'}
    python_files = [
        f for f in python_files 
        if not any(part in excluded_dirs for part in f.parts)
    ]
    
    logger.info(f"Scanning {len(python_files)} Python files...")
    
    for file_path in python_files:
        logger.info(f"Analyzing: {file_path}")
        issues = analyzer.analyze_file(str(file_path))
        if issues:
            all_issues[str(file_path)] = issues
    
    return all_issues

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Fix import issues in SmartArb Engine')
    parser.add_argument('path', nargs='?', default='.', help='Path to scan (default: current directory)')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be fixed without making changes')
    parser.add_argument('--no-backup', action='store_true', help='Don\'t create backup files')
    parser.add_argument('--file', help='Fix only specific file')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Scan for issues
    if args.file:
        if not os.path.exists(args.file):
            logger.error(f"File not found: {args.file}")
            return 1
        
        analyzer = ImportAnalyzer()
        issues = analyzer.analyze_file(args.file)
        all_issues = {args.file: issues} if issues else {}
    else:
        all_issues = scan_project(args.path)
    
    if not all_issues:
        logger.info("No import issues found!")
        return 0
    
    # Report issues
    total_issues = sum(len(issues) for issues in all_issues.values())
    logger.info(f"Found {total_issues} import issues in {len(all_issues)} files")
    
    # Show detailed issues
    for file_path, issues in all_issues.items():
        print(f"\n📁 {file_path}:")
        for issue in issues:
            print(f"  ⚠️  Line {issue.line_number}: Missing '{issue.missing_import}'")
            print(f"     Context: {issue.context}")
            print(f"     Fix: {issue.suggested_fix}")
    
    # Apply fixes
    if args.dry_run:
        logger.info("Dry run mode - no files will be modified")
        return 0
    
    # Ask for confirmation unless it's a single file
    if not args.file and total_issues > 0:
        response = input(f"\nFix {total_issues} issues? (y/N): ")
        if response.lower() != 'y':
            logger.info("Aborted by user")
            return 0
    
    # Fix the issues
    fixer = ImportFixer(dry_run=args.dry_run, create_backup=not args.no_backup)
    
    success_count = 0
    error_count = 0
    
    for file_path, issues in all_issues.items():
        result = fixer.fix_file(file_path, issues)
        if result.success:
            success_count += 1
        else:
            error_count += 1
            logger.error(f"Failed to fix {file_path}: {result.error_message}")
    
    logger.info(f"Fixed imports in {success_count} files ({error_count} errors)")
    
    return 0 if error_count == 0 else 1

if __name__ == '__main__':
    sys.exit(main())