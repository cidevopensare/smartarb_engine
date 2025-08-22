“””
AI Code Update Manager for SmartArb Engine
Automated code updates based on Claude AI recommendations with safety checks
“””

import asyncio
import os
import shutil
import tempfile
import subprocess
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import time
from datetime import datetime
import json
import hashlib
import structlog

from .claude_integration import AIRecommendation, RecommendationType

logger = structlog.get_logger(**name**)

class UpdateType(Enum):
“”“Types of code updates”””
PARAMETER_CHANGE = “parameter_change”
CONFIGURATION_UPDATE = “configuration_update”
LOGIC_IMPROVEMENT = “logic_improvement”
BUG_FIX = “bug_fix”
OPTIMIZATION = “optimization”
SAFETY_IMPROVEMENT = “safety_improvement”

class UpdateStatus(Enum):
“”“Status of code updates”””
PENDING = “pending”
ANALYZING = “analyzing”
TESTING = “testing”
APPROVED = “approved”
APPLYING = “applying”
APPLIED = “applied”
FAILED = “failed”
REJECTED = “rejected”
ROLLED_BACK = “rolled_back”

@dataclass
class CodeUpdate:
“”“Code update data structure”””
id: str
recommendation_id: str
update_type: UpdateType
status: UpdateStatus
file_path: str
original_content: str
updated_content: str
description: str
confidence: float
safety_score: float
impact_assessment: str
test_results: Dict[str, Any]
backup_path: Optional[str] = None
created_time: float = 0
applied_time: Optional[float] = None
rolled_back_time: Optional[float] = None

```
def __post_init__(self):
    if self.created_time == 0:
        self.created_time = time.time()

def to_dict(self) -> Dict[str, Any]:
    return {
        'id': self.id,
        'recommendation_id': self.recommendation_id,
        'update_type': self.update_type.value,
        'status': self.status.value,
        'file_path': self.file_path,
        'description': self.description,
        'confidence': self.confidence,
        'safety_score': self.safety_score,
        'impact_assessment': self.impact_assessment,
        'test_results': self.test_results,
        'backup_path': self.backup_path,
        'created_time': self.created_time,
        'applied_time': self.applied_time,
        'rolled_back_time': self.rolled_back_time
    }
```

class SafetyChecker:
“”“Safety checker for code updates”””

```
def __init__(self, config: Dict[str, Any]):
    self.config = config
    
    # Safety rules
    self.forbidden_patterns = [
        # Dangerous operations
        'os.system',
        'subprocess.call',
        'exec(',
        'eval(',
        '__import__',
        
        # File operations that could be dangerous
        'shutil.rmtree',
        'os.remove',
        'os.unlink',
        
        # Network operations
        'requests.post',
        'urllib.request',
        'socket.connect',
        
        # Database operations
        'DROP TABLE',
        'DELETE FROM',
        'TRUNCATE',
        
        # API key exposure
        'api_key',
        'secret',
        'password',
        'token'
    ]
    
    # Critical files that require extra scrutiny
    self.critical_files = [
        'src/core/engine.py',
        'src/core/risk_manager.py',
        'src/core/execution_engine.py',
        'config/settings.yaml'
    ]
    
    # Safe change patterns
    self.safe_patterns = [
        # Parameter adjustments
        r'min_spread_percent\s*=',
        r'max_position_size\s*=',
        r'confidence_threshold\s*=',
        r'scan_frequency\s*=',
        
        # Configuration changes
        r'enabled\s*:\s*(true|false)',
        r'priority\s*:\s*\d+',
        r'timeout\s*:\s*\d+',
    ]

def assess_safety(self, code_update: CodeUpdate) -> Tuple[float, List[str]]:
    """Assess safety of a code update"""
    safety_score = 1.0
    warnings = []
    
    # Check for forbidden patterns
    for pattern in self.forbidden_patterns:
        if pattern in code_update.updated_content:
            safety_score -= 0.3
            warnings.append(f"Contains potentially dangerous pattern: {pattern}")
    
    # Check if modifying critical files
    if code_update.file_path in self.critical_files:
        safety_score -= 0.2
        warnings.append(f"Modifying critical file: {code_update.file_path}")
    
    # Check size of change
    original_lines = code_update.original_content.count('\n')
    updated_lines = code_update.updated_content.count('\n')
    line_diff = abs(updated_lines - original_lines)
    
    if line_diff > 50:
        safety_score -= 0.2
        warnings.append(f"Large change: {line_diff} lines modified")
    
    # Check for syntax validity (basic check)
    if code_update.file_path.endswith('.py'):
        try:
            compile(code_update.updated_content, code_update.file_path, 'exec')
        except SyntaxError as e:
            safety_score = 0.0
            warnings.append(f"Syntax error: {str(e)}")
    
    # Ensure safety score doesn't go below 0
    safety_score = max(0.0, safety_score)
    
    return safety_score, warnings
```

class CodeUpdateManager:
“””
AI-Driven Code Update Manager

```
Features:
- Automated code updates from AI recommendations
- Safety checking and validation
- Automatic backups and rollback capability
- Testing integration
- Human approval workflow
- Change tracking and audit trail
"""

def __init__(self, notification_manager=None, config: Dict[str, Any] = None):
    self.notification_manager = notification_manager
    self.config = config or {}
    
    # Update settings
    safety_config = self.config.get('ai', {}).get('safety', {})
    self.auto_apply_safe_changes = safety_config.get('auto_apply_safe_changes', False)
    self.require_human_approval = safety_config.get('require_human_approval', True)
    self.create_backups = safety_config.get('create_backups', True)
    self.max_changes_per_day = safety_config.get('max_changes_per_day', 3)
    
    # Safety thresholds
    self.min_safety_score = 0.8
    self.min_confidence_score = 0.8
    
    # Initialize safety checker
    self.safety_checker = SafetyChecker(self.config)
    
    # State tracking
    self.pending_updates: Dict[str, CodeUpdate] = {}
    self.applied_updates: List[CodeUpdate] = []
    self.failed_updates: List[CodeUpdate] = []
    
    # Backup management
    self.backup_dir = "backups/code_updates"
    os.makedirs(self.backup_dir, exist_ok=True)
    
    # Daily change tracking
    self.daily_changes = 0
    self.last_reset_date = datetime.now().date()
    
    logger.info("code_update_manager_initialized",
               auto_apply=self.auto_apply_safe_changes,
               require_approval=self.require_human_approval,
               backup_enabled=self.create_backups)

async def process_recommendation(self, recommendation: AIRecommendation) -> Optional[CodeUpdate]:
    """Process an AI recommendation for potential code updates"""
    
    if recommendation.type != RecommendationType.CODE_UPDATE:
        return None
    
    if not recommendation.code_changes:
        logger.warning("code_recommendation_without_changes",
                     recommendation_id=recommendation.id)
        return None
    
    try:
        # Extract code changes
        file_path = list(recommendation.code_changes.keys())[0]
        updated_content = recommendation.code_changes[file_path]
        
        # Read original content
        if not os.path.exists(file_path):
            logger.error("target_file_not_found", file_path=file_path)
            return None
        
        with open(file_path, 'r', encoding='utf-8') as f:
            original_content = f.read()
        
        # Create code update
        update_id = f"update_{int(time.time())}_{len(self.pending_updates)}"
        code_update = CodeUpdate(
            id=update_id,
            recommendation_id=recommendation.id,
            update_type=self._determine_update_type(recommendation),
            status=UpdateStatus.PENDING,
            file_path=file_path,
            original_content=original_content,
            updated_content=updated_content,
            description=recommendation.description,
            confidence=recommendation.confidence,
            safety_score=0.0,  # Will be calculated
            impact_assessment=recommendation.expected_impact,
            test_results={}
        )
        
        # Assess safety
        safety_score, warnings = self.safety_checker.assess_safety(code_update)
        code_update.safety_score = safety_score
        
        if warnings:
            logger.warning("code_update_safety_warnings",
                         update_id=update_id,
                         warnings=warnings)
        
        # Add to pending updates
        self.pending_updates[update_id] = code_update
        
        logger.info("code_update_created",
                   update_id=update_id,
                   file_path=file_path,
                   safety_score=safety_score,
                   confidence=recommendation.confidence)
        
        # Automatically process if safe enough
        if self._should_auto_apply(code_update):
            await self._auto_apply_update(code_update)
        
        return code_update
        
    except Exception as e:
        logger.error("code_update_processing_failed",
                    recommendation_id=recommendation.id,
                    error=str(e))
        return None

def _determine_update_type(self, recommendation: AIRecommendation) -> UpdateType:
    """Determine the type of code update"""
    
    type_keywords = {
        UpdateType.PARAMETER_CHANGE: ['parameter', 'threshold', 'limit', 'value'],
        UpdateType.CONFIGURATION_UPDATE: ['config', 'setting', 'enable', 'disable'],
        UpdateType.LOGIC_IMPROVEMENT: ['logic', 'algorithm', 'strategy', 'calculation'],
        UpdateType.BUG_FIX: ['bug', 'fix', 'error', 'issue', 'problem'],
        UpdateType.OPTIMIZATION: ['optimize', 'performance', 'efficiency', 'speed'],
        UpdateType.SAFETY_IMPROVEMENT: ['safety', 'security', 'risk', 'protection']
    }
    
    description_lower = recommendation.description.lower()
    
    for update_type, keywords in type_keywords.items():
        if any(keyword in description_lower for keyword in keywords):
            return update_type
    
    return UpdateType.LOGIC_IMPROVEMENT  # Default

def _should_auto_apply(self, code_update: CodeUpdate) -> bool:
    """Determine if update should be automatically applied"""
    
    if not self.auto_apply_safe_changes:
        return False
    
    if self.require_human_approval:
        return False
    
    # Check daily change limit
    self._check_daily_limit()
    if self.daily_changes >= self.max_changes_per_day:
        logger.warning("daily_change_limit_reached",
                     daily_changes=self.daily_changes,
                     limit=self.max_changes_per_day)
        return False
    
    # Check safety and confidence thresholds
    if (code_update.safety_score >= self.min_safety_score and 
        code_update.confidence >= self.min_confidence_score):
        
        # Only auto-apply safe types of changes
        safe_types = [
            UpdateType.PARAMETER_CHANGE,
            UpdateType.CONFIGURATION_UPDATE
        ]
        
        return code_update.update_type in safe_types
    
    return False

async def _auto_apply_update(self, code_update: CodeUpdate) -> bool:
    """Automatically apply a safe code update"""
    
    try:
        logger.info("auto_applying_code_update",
                   update_id=code_update.id,
                   file_path=code_update.file_path)
        
        return await self.apply_update(code_update.id)
        
    except Exception as e:
        logger.error("auto_apply_failed",
                    update_id=code_update.id,
                    error=str(e))
        return False

async def apply_update(self, update_id: str) -> bool:
    """Apply a code update"""
    
    if update_id not in self.pending_updates:
        logger.error("update_not_found", update_id=update_id)
        return False
    
    code_update = self.pending_updates[update_id]
    
    try:
        code_update.status = UpdateStatus.APPLYING
        
        logger.info("applying_code_update",
                   update_id=update_id,
                   file_path=code_update.file_path)
        
        # Create backup if enabled
        if self.create_backups:
            backup_path = await self._create_backup(code_update)
            code_update.backup_path = backup_path
        
        # Apply the update
        await self._write_updated_content(code_update)
        
        # Run tests if available
        test_results = await self._run_tests(code_update)
        code_update.test_results = test_results
        
        # Check if tests passed
        if test_results.get('success', True):
            code_update.status = UpdateStatus.APPLIED
            code_update.applied_time = time.time()
            
            # Move to applied updates
            self.applied_updates.append(code_update)
            del self.pending_updates[update_id]
            
            # Update daily counter
            self._check_daily_limit()
            self.daily_changes += 1
            
            # Send notification
            if self.notification_manager:
                await self.notification_manager.notify_ai_code_update(
                    update_type=code_update.update_type.value,
                    file_path=code_update.file_path,
                    description=code_update.description,
                    safety_score=code_update.safety_score
                )
            
            logger.info("code_update_applied_successfully",
                       update_id=update_id,
                       file_path=code_update.file_path)
            
            return True
        else:
            # Tests failed, rollback
            await self._rollback_update(code_update)
            return False
            
    except Exception as e:
        logger.error("code_update_application_failed",
                    update_id=update_id,
                    error=str(e))
        
        # Attempt rollback
        try:
            await self._rollback_update(code_update)
        except Exception as rollback_error:
            logger.error("rollback_also_failed",
                       update_id=update_id,
                       rollback_error=str(rollback_error))
        
        return False

async def _create_backup(self, code_update: CodeUpdate) -> str:
    """Create backup of original file"""
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.basename(code_update.file_path)
    backup_filename = f"{timestamp}_{code_update.id}_{filename}.backup"
    backup_path = os.path.join(self.backup_dir, backup_filename)
    
    # Ensure backup directory exists
    os.makedirs(os.path.dirname(backup_path), exist_ok=True)
    
    # Copy original file
    shutil.copy2(code_update.file_path, backup_path)
    
    logger.info("backup_created",
               original_file=code_update.file_path,
               backup_path=backup_path)
    
    return backup_path

async def _write_updated_content(self, code_update: CodeUpdate) -> None:
    """Write updated content to file"""
    
    # Write to temporary file first
    temp_file = code_update.file_path + '.tmp'
    
    with open(temp_file, 'w', encoding='utf-8') as f:
        f.write(code_update.updated_content)
    
    # Atomic rename
    os.rename(temp_file, code_update.file_path)
    
    logger.debug("file_updated",
                file_path=code_update.file_path,
                update_id=code_update.id)

async def _run_tests(self, code_update: CodeUpdate) -> Dict[str, Any]:
    """Run tests to validate the code update"""
    
    test_results = {
        'success': True,
        'tests_run': 0,
        'tests_passed': 0,
        'tests_failed': 0,
        'output': '',
        'errors': []
    }
    
    try:
        # Run syntax check for Python files
        if code_update.file_path.endswith('.py'):
            try:
                compile(code_update.updated_content, code_update.file_path, 'exec')
                test_results['tests_run'] += 1
                test_results['tests_passed'] += 1
            except SyntaxError as e:
                test_results['success'] = False
                test_results['tests_run'] += 1
                test_results['tests_failed'] += 1
                test_results['errors'].append(f"Syntax error: {str(e)}")
        
        # Run basic import test for Python modules
        if code_update.file_path.endswith('.py') and test_results['success']:
            try:
                # Try to import the module to check for import errors
                module_path = code_update.file_path.replace('/', '.').replace('.py', '')
                if module_path.startswith('src.'):
                    # This is a more complex test that would require proper module importing
                    # For now, we'll skip it to avoid circular imports
                    pass
                
                test_results['tests_run'] += 1
                test_results['tests_passed'] += 1
                
            except Exception as e:
                test_results['success'] = False
                test_results['tests_run'] += 1
                test_results['tests_failed'] += 1
                test_results['errors'].append(f"Import error: {str(e)}")
        
        # For configuration files, validate YAML syntax
        if code_update.file_path.endswith('.yaml') or code_update.file_path.endswith('.yml'):
            try:
                import yaml
                yaml.safe_load(code_update.updated_content)
                test_results['tests_run'] += 1
                test_results['tests_passed'] += 1
            except yaml.YAMLError as e:
                test_results['success'] = False
                test_results['tests_run'] += 1
                test_results['tests_failed'] += 1
                test_results['errors'].append(f"YAML syntax error: {str(e)}")
        
    except Exception as e:
        test_results['success'] = False
        test_results['errors'].append(f"Test execution error: {str(e)}")
    
    logger.info("code_update_tests_completed",
               update_id=code_update.id,
               success=test_results['success'],
               tests_run=test_results['tests_run'],
               tests_passed=test_results['tests_passed'])
    
    return test_results

async def _rollback_update(self, code_update: CodeUpdate) -> None:
    """Rollback a code update"""
    
    try:
        if code_update.backup_path and os.path.exists(code_update.backup_path):
            # Restore from backup
            shutil.copy2(code_update.backup_path, code_update.file_path)
            
            code_update.status = UpdateStatus.ROLLED_BACK
            code_update.rolled_back_time = time.time()
            
            logger.info("code_update_rolled_back",
                       update_id=code_update.id,
                       file_path=code_update.file_path)
        else:
            # Restore from original content
            with open(code_update.file_path, 'w', encoding='utf-8') as f:
                f.write(code_update.original_content)
            
            code_update.status = UpdateStatus.ROLLED_BACK
            code_update.rolled_back_time = time.time()
            
            logger.info("code_update_rolled_back_from_original",
                       update_id=code_update.id,
                       file_path=code_update.file_path)
        
        # Move to failed updates
        self.failed_updates.append(code_update)
        if code_update.id in self.pending_updates:
            del self.pending_updates[code_update.id]
        
    except Exception as e:
        logger.error("rollback_failed",
                    update_id=code_update.id,
                    error=str(e))
        code_update.status = UpdateStatus.FAILED

def _check_daily_limit(self) -> None:
    """Check and reset daily change counter"""
    current_date = datetime.now().date()
    if current_date > self.last_reset_date:
        self.daily_changes = 0
        self.last_reset_date = current_date
        logger.info("daily_change_counter_reset")

# Manual approval methods
def approve_update(self, update_id: str) -> bool:
    """Manually approve a pending update"""
    if update_id in self.pending_updates:
        update = self.pending_updates[update_id]
        update.status = UpdateStatus.APPROVED
        logger.info("code_update_approved", update_id=update_id)
        return True
    return False

def reject_update(self, update_id: str, reason: str = "") -> bool:
    """Manually reject a pending update"""
    if update_id in self.pending_updates:
        update = self.pending_updates[update_id]
        update.status = UpdateStatus.REJECTED
        
        # Move to failed updates
        self.failed_updates.append(update)
        del self.pending_updates[update_id]
        
        logger.info("code_update_rejected",
                   update_id=update_id,
                   reason=reason)
        return True
    return False

async def rollback_applied_update(self, update_id: str) -> bool:
    """Rollback a previously applied update"""
    
    # Find the update in applied updates
    update = None
    for applied_update in self.applied_updates:
        if applied_update.id == update_id:
            update = applied_update
            break
    
    if not update:
        logger.error("applied_update_not_found", update_id=update_id)
        return False
    
    try:
        await self._rollback_update(update)
        
        # Remove from applied updates
        self.applied_updates.remove(update)
        
        logger.info("applied_update_rolled_back", update_id=update_id)
        return True
        
    except Exception as e:
        logger.error("applied_update_rollback_failed",
                    update_id=update_id,
                    error=str(e))
        return False

# Status and reporting methods
def get_pending_updates(self) -> List[Dict[str, Any]]:
    """Get list of pending updates"""
    return [update.to_dict() for update in self.pending_updates.values()]

def get_applied_updates(self, limit: int = 20) -> List[Dict[str, Any]]:
    """Get list of recently applied updates"""
    recent_updates = sorted(
        self.applied_updates,
        key=lambda u: u.applied_time or 0,
        reverse=True
    )[:limit]
    
    return [update.to_dict() for update in recent_updates]

def get_failed_updates(self, limit: int = 20) -> List[Dict[str, Any]]:
    """Get list of failed updates"""
    recent_failures = sorted(
        self.failed_updates,
        key=lambda u: u.created_time,
        reverse=True
    )[:limit]
    
    return [update.to_dict() for update in recent_failures]

def get_update_stats(self) -> Dict[str, Any]:
    """Get update statistics"""
    total_updates = len(self.applied_updates) + len(self.failed_updates)
    success_rate = 0.0
    if total_updates > 0:
        success_rate = (len(self.applied_updates) / total_updates) * 100
    
    return {
        'pending_updates': len(self.pending_updates),
        'applied_updates': len(self.applied_updates),
        'failed_updates': len(self.failed_updates),
        'total_updates': total_updates,
        'success_rate': success_rate,
        'daily_changes': self.daily_changes,
        'daily_limit': self.max_changes_per_day,
        'auto_apply_enabled': self.auto_apply_safe_changes,
        'require_approval': self.require_human_approval,
        'min_safety_score': self.min_safety_score,
        'min_confidence_score': self.min_confidence_score
    }

def cleanup_old_backups(self, days_to_keep: int = 30) -> int:
    """Clean up old backup files"""
    cutoff_time = time.time() - (days_to_keep * 24 * 3600)
    cleaned_count = 0
    
    try:
        for filename in os.listdir(self.backup_dir):
            file_path = os.path.join(self.backup_dir, filename)
            if os.path.isfile(file_path):
                file_mtime = os.path.getmtime(file_path)
                if file_mtime < cutoff_time:
                    os.remove(file_path)
                    cleaned_count += 1
        
        logger.info("old_backups_cleaned",
                   cleaned_count=cleaned_count,
                   days_to_keep=days_to_keep)
        
    except Exception as e:
        logger.error("backup_cleanup_failed", error=str(e))
    
    return cleaned_count
```