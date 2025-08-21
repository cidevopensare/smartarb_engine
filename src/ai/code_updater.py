"""
Intelligent Code Updater for SmartArb Engine
Safely applies Claude's code recommendations with rollback capability
"""

import asyncio
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import json
import ast
import git
import structlog

from .claude_integration import ClaudeRecommendation
from ..utils.notifications import NotificationManager, NotificationLevel

logger = structlog.get_logger(__name__)


class CodeUpdateManager:
    """
    Intelligent Code Update System
    
    Features:
    - Safe code modifications with backup
    - Automated testing before deployment
    - Rollback capabilities
    - Version control integration
    - Performance impact tracking
    """
    
    def __init__(self, notification_manager: NotificationManager):
        self.notification_manager = notification_manager
        
        # Paths and directories
        self.project_root = Path.cwd()
        self.backup_dir = self.project_root / 'backups' / 'code_updates'
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Git repository
        try:
            self.repo = git.Repo(self.project_root)
        except:
            self.repo = None
            logger.warning("git_repository_not_found")
        
        # Update tracking
        self.update_history: List[Dict[str, Any]] = []
        self.pending_updates: List[Dict[str, Any]] = []
        
        # Safety configuration
        self.safety_config = {
            'require_tests': True,
            'require_backup': True,
            'max_changes_per_update': 5,
            'protected_files': [
                'src/core/engine.py',  # Main engine - critical
                'src/utils/security.py',  # Security functions
                'src/db/models.py'  # Database models
            ],
            'protected_functions': [
                'place_order',  # Trading functions
                'cancel_order', 
                'get_balance',
                'validate_opportunity'
            ]
        }
        
        logger.info("code_update_manager_initialized",
                   backup_dir=str(self.backup_dir))
    
    async def process_recommendations(self, recommendations: List[ClaudeRecommendation]) -> Dict[str, Any]:
        """
        Process and apply safe code recommendations
        
        Returns:
            Dict with update results and statistics
        """
        results = {
            'total_recommendations': len(recommendations),
            'processed': 0,
            'applied': 0,
            'skipped': 0,
            'failed': 0,
            'updates': []
        }
        
        logger.info("processing_code_recommendations", count=len(recommendations))
        
        for rec in recommendations:
            if not rec.code_changes:
                continue
            
            try:
                update_result = await self._process_single_recommendation(rec)
                results['updates'].append(update_result)
                results['processed'] += 1
                
                if update_result['status'] == 'applied':
                    results['applied'] += 1
                elif update_result['status'] == 'skipped':
                    results['skipped'] += 1
                else:
                    results['failed'] += 1
                    
            except Exception as e:
                logger.error("recommendation_processing_failed",
                           title=rec.title,
                           error=str(e))
                results['failed'] += 1
        
        # Send summary notification
        await self._send_update_summary(results)
        
        return results
    
    async def _process_single_recommendation(self, rec: ClaudeRecommendation) -> Dict[str, Any]:
        """Process a single recommendation with code changes"""
        
        update_id = f"update_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        update_result = {
            'update_id': update_id,
            'recommendation_title': rec.title,
            'priority': rec.priority,
            'status': 'pending',
            'changes_applied': 0,
            'backup_created': False,
            'tests_passed': False,
            'rollback_available': False,
            'error_message': None
        }
        
        try:
            # Safety checks
            safety_check = await self._safety_check(rec)
            if not safety_check['safe']:
                update_result['status'] = 'skipped'
                update_result['error_message'] = safety_check['reason']
                return update_result
            
            # Create backup
            backup_path = await self._create_backup(update_id, rec.code_changes)
            update_result['backup_created'] = backup_path is not None
            update_result['rollback_available'] = backup_path is not None
            
            # Apply code changes
            changes_applied = 0
            for change in rec.code_changes:
                if await self._apply_code_change(change, update_id):
                    changes_applied += 1
            
            update_result['changes_applied'] = changes_applied
            
            if changes_applied == 0:
                update_result['status'] = 'failed'
                update_result['error_message'] = 'No changes could be applied'
                return update_result
            
            # Run tests
            if self.safety_config['require_tests']:
                test_result = await self._run_tests()
                update_result['tests_passed'] = test_result
                
                if not test_result:
                    # Rollback on test failure
                    await self._rollback_update(update_id)
                    update_result['status'] = 'failed'
                    update_result['error_message'] = 'Tests failed, changes rolled back'
                    return update_result
            
            # Commit to git if available
            if self.repo:
                try:
                    self.repo.index.add_all()
                    self.repo.index.commit(f"AI Update: {rec.title} ({update_id})")
                    logger.info("changes_committed_to_git", update_id=update_id)
                except Exception as e:
                    logger.warning("git_commit_failed", error=str(e))
            
            # Success
            update_result['status'] = 'applied'
            self.update_history.append(update_result.copy())
            
            logger.info("code_update_applied_successfully",
                       update_id=update_id,
                       title=rec.title,
                       changes=changes_applied)
            
            return update_result
            
        except Exception as e:
            update_result['status'] = 'failed'
            update_result['error_message'] = str(e)
            
            # Attempt rollback
            try:
                await self._rollback_update(update_id)
            except:
                pass
            
            logger.error("code_update_failed",
                        update_id=update_id,
                        error=str(e))
            
            return update_result
    
    async def _safety_check(self, rec: ClaudeRecommendation) -> Dict[str, Any]:
        """Comprehensive safety check for code changes"""
        
        safety_result = {'safe': True, 'reason': None, 'warnings': []}
        
        # Check priority level
        if rec.priority == 'critical' and not rec.risks:
            safety_result['safe'] = False
            safety_result['reason'] = 'Critical changes require explicit risk assessment'
            return safety_result
        
        # Check number of changes
        if len(rec.code_changes) > self.safety_config['max_changes_per_update']:
            safety_result['safe'] = False
            safety_result['reason'] = f'Too many changes in single update: {len(rec.code_changes)}'
            return safety_result
        
        # Check protected files and functions
        for change in rec.code_changes:
            file_path = change.get('file', '')
            function_name = change.get('function', '')
            
            # Protected file check
            if any(protected in file_path for protected in self.safety_config['protected_files']):
                safety_result['warnings'].append(f'Modifying protected file: {file_path}')
                if rec.priority != 'low':
                    safety_result['safe'] = False
                    safety_result['reason'] = f'Cannot modify protected file: {file_path}'
                    return safety_result
            
            # Protected function check
            if function_name in self.safety_config['protected_functions']:
                safety_result['warnings'].append(f'Modifying protected function: {function_name}')
                if rec.priority not in ['low', 'medium']:
                    safety_result['safe'] = False
                    safety_result['reason'] = f'Cannot modify protected function: {function_name}'
                    return safety_result
            
            # Code content safety check
            suggested_code = change.get('suggested_value', '')
            if not self._is_code_safe(suggested_code):
                safety_result['safe'] = False
                safety_result['reason'] = 'Unsafe code detected in suggested changes'
                return safety_result
        
        return safety_result
    
    def _is_code_safe(self, code: str) -> bool:
        """Check if code contains potentially dangerous operations"""
        
        dangerous_patterns = [
            # System operations
            'os.system', 'subprocess.call', 'subprocess.run', 'eval', 'exec',
            '__import__', 'globals()', 'locals()',
            
            # File operations
            'open(', 'file(', 'shutil.rmtree', 'os.remove', 'os.unlink',
            
            # Network operations
            'urllib.request', 'requests.get', 'socket.socket',
            
            # Database operations
            'DROP TABLE', 'DELETE FROM', 'TRUNCATE',
            
            # Code injection
            'eval(', 'exec(', 'compile(',
        ]
        
        code_lower = code.lower()
        for pattern in dangerous_patterns:
            if pattern.lower() in code_lower:
                logger.warning("dangerous_code_pattern_detected", pattern=pattern)
                return False
        
        # Try to parse as valid Python
        try:
            ast.parse(code)
        except SyntaxError:
            logger.warning("invalid_python_syntax", code=code[:100])
            return False
        
        return True
    
    async def _create_backup(self, update_id: str, changes: List[Dict[str, str]]) -> Optional[Path]:
        """Create backup of files that will be modified"""
        
        try:
            backup_path = self.backup_dir / update_id
            backup_path.mkdir(parents=True, exist_ok=True)
            
            # Backup each file that will be modified
            for change in changes:
                file_path = Path(change.get('file', ''))
                if file_path.exists():
                    backup_file_path = backup_path / file_path.name
                    shutil.copy2(file_path, backup_file_path)
                    logger.debug("file_backed_up", 
                               original=str(file_path),
                               backup=str(backup_file_path))
            
            # Create backup metadata
            metadata = {
                'update_id': update_id,
                'timestamp': datetime.now().isoformat(),
                'files': [change.get('file') for change in changes],
                'git_commit': self._get_current_git_commit()
            }
            
            metadata_file = backup_path / 'metadata.json'
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            logger.info("backup_created", backup_path=str(backup_path))
            return backup_path
            
        except Exception as e:
            logger.error("backup_creation_failed", error=str(e))
            return None
    
    async def _apply_code_change(self, change: Dict[str, str], update_id: str) -> bool:
        """Apply a single code change"""
        
        try:
            file_path = Path(change.get('file', ''))
            function_name = change.get('function', '')
            change_type = change.get('change_type', 'modify_parameter')
            current_value = change.get('current_value', '')
            suggested_value = change.get('suggested_value', '')
            
            if not file_path.exists():
                logger.warning("file_not_found", file=str(file_path))
                return False
            
            # Read current file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Apply change based on type
            if change_type == 'modify_parameter':
                new_content = self._modify_parameter(content, current_value, suggested_value)
            elif change_type == 'add_logic':
                new_content = self._add_logic(content, function_name, suggested_value)
            elif change_type == 'optimize':
                new_content = self._optimize_code(content, function_name, suggested_value)
            else:
                logger.warning("unknown_change_type", type=change_type)
                return False
            
            if new_content != content:
                # Write modified content
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                
                logger.info("code_change_applied",
                           file=str(file_path),
                           function=function_name,
                           type=change_type)
                return True
            else:
                logger.info("no_changes_needed", file=str(file_path))
                return False
                
        except Exception as e:
            logger.error("code_change_failed",
                        file=change.get('file'),
                        error=str(e))
            return False
    
    def _modify_parameter(self, content: str, current_value: str, new_value: str) -> str:
        """Modify parameter values in code"""
        
        # Simple string replacement for now
        # In production, would use AST manipulation for safer changes
        if current_value in content:
            return content.replace(current_value, new_value)
        
        return content
    
    def _add_logic(self, content: str, function_name: str, new_logic: str) -> str:
        """Add logic to a function"""
        
        # Simple implementation - would need more sophisticated AST manipulation
        # for production use
        function_pattern = f"def {function_name}("
        
        if function_pattern in content:
            # Find function and add logic before return statement
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if function_pattern in line:
                    # Find the end of the function and add logic
                    # This is a simplified implementation
                    lines.insert(i + 2, f"        {new_logic}")
                    break
            
            return '\n'.join(lines)
        
        return content
    
    def _optimize_code(self, content: str, function_name: str, optimization: str) -> str:
        """Apply code optimization"""
        
        # Placeholder for code optimization logic
        # Would implement specific optimizations based on the suggestion
        return content
    
    async def _run_tests(self) -> bool:
        """Run test suite to verify changes don't break functionality"""
        
        try:
            # Run pytest on the test suite
            result = subprocess.run([
                'python', '-m', 'pytest', 'tests/', '-v', '--tb=short'
            ], capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                logger.info("tests_passed")
                return True
            else:
                logger.warning("tests_failed", 
                             stdout=result.stdout[:500],
                             stderr=result.stderr[:500])
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("tests_timeout")
            return False
        except Exception as e:
            logger.error("test_execution_failed", error=str(e))
            return False
    
    async def _rollback_update(self, update_id: str) -> bool:
        """Rollback changes from a specific update"""
        
        try:
            backup_path = self.backup_dir / update_id
            
            if not backup_path.exists():
                logger.error("backup_not_found", update_id=update_id)
                return False
            
            # Read backup metadata
            metadata_file = backup_path / 'metadata.json'
            if metadata_file.exists():
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                
                # Restore each file
                for file_name in metadata.get('files', []):
                    original_path = Path(file_name)
                    backup_file_path = backup_path / original_path.name
                    
                    if backup_file_path.exists():
                        shutil.copy2(backup_file_path, original_path)
                        logger.debug("file_restored", file=str(original_path))
            
            logger.info("update_rolled_back", update_id=update_id)
            return True
            
        except Exception as e:
            logger.error("rollback_failed", update_id=update_id, error=str(e))
            return False
    
    def _get_current_git_commit(self) -> Optional[str]:
        """Get current git commit hash"""
        
        if self.repo:
            try:
                return self.repo.head.commit.hexsha
            except:
                pass
        
        return None
    
    async def _send_update_summary(self, results: Dict[str, Any]):
        """Send update summary notification"""
        
        summary = f"""
🔧 Code Update Summary:

📊 Results:
• Processed: {results['processed']}/{results['total_recommendations']}
• Applied: {results['applied']}
• Skipped: {results['skipped']}
• Failed: {results['failed']}

💡 Successfully applied updates:
"""
        
        successful_updates = [u for u in results['updates'] if u['status'] == 'applied']
        for update in successful_updates[:3]:  # Show first 3
            summary += f"\n• {update['recommendation_title']}"
        
        if len(successful_updates) > 3:
            summary += f"\n• ... and {len(successful_updates) - 3} more"
        
        level = NotificationLevel.INFO
        if results['failed'] > 0:
            level = NotificationLevel.WARNING
        if results['applied'] == 0 and results['total_recommendations'] > 0:
            level = NotificationLevel.ERROR
        
        await self.notification_manager.send_notification(
            "🔧 Code Updates Applied",
            summary,
            level
        )
    
    def get_update_history(self) -> List[Dict[str, Any]]:
        """Get history of applied updates"""
        return self.update_history.copy()
    
    def get_available_rollbacks(self) -> List[Dict[str, Any]]:
        """Get list of available rollback points"""
        
        rollbacks = []
        for backup_dir in self.backup_dir.iterdir():
            if backup_dir.is_dir():
                metadata_file = backup_dir / 'metadata.json'
                if metadata_file.exists():
                    try:
                        with open(metadata_file, 'r') as f:
                            metadata = json.load(f)
                        rollbacks.append(metadata)
                    except:
                        pass
        
        return sorted(rollbacks, key=lambda x: x.get('timestamp', ''), reverse=True)
    
    async def manual_rollback(self, update_id: str) -> bool:
        """Manually rollback a specific update"""
        
        success = await self._rollback_update(update_id)
        
        if success:
            await self.notification_manager.send_notification(
                "🔄 Manual Rollback Completed",
                f"Successfully rolled back update: {update_id}",
                NotificationLevel.INFO
            )
        else:
            await self.notification_manager.send_notification(
                "❌ Rollback Failed",
                f"Failed to rollback update: {update_id}",
                NotificationLevel.ERROR
            )
        
        return success
