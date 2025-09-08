"""
AI Analysis Dashboard for SmartArb Engine
Real-time monitoring and control of AI analysis system
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import asdict
import json
from pathlib import Path
import structlog

from .claude_integration import ClaudeAnalysisEngine, ClaudeRecommendation
from .analysis_scheduler import AIAnalysisScheduler
from .code_updater import CodeUpdateManager
from ..utils.notifications import NotificationManager

logger = structlog.get_logger(__name__)


logger = structlog.get_logger(__name__)


class AIDashboard:
    """
    AI Analysis Dashboard and Control Center
    
    Features:
    - Real-time AI analysis monitoring
    - Recommendation management
    - Performance tracking
    - Manual analysis requests
    - Code update oversight
    """
    
    def __init__(self, claude_engine: ClaudeAnalysisEngine,
                 scheduler: AIAnalysisScheduler,
                 code_updater: CodeUpdateManager,
                 notification_manager: NotificationManager):
        
        self.claude_engine = claude_engine
        self.scheduler = scheduler
        self.code_updater = code_updater
        self.notification_manager = notification_manager
        
        # Dashboard state
        self.dashboard_data: Dict[str, Any] = {}
        self.last_update = datetime.now()
        self.update_interval = 30  # seconds
        
        # Performance tracking
        self.performance_history: List[Dict[str, Any]] = []
        self.recommendation_stats: Dict[str, int] = {
            'total': 0,
            'implemented': 0,
            'pending': 0,
            'rejected': 0
        }
        
        logger.info("ai_dashboard_initialized")
    
    async def start_monitoring(self):
        """Start dashboard monitoring loop"""
        
        while True:
            try:
                await self.update_dashboard_data()
                await asyncio.sleep(self.update_interval)
            except Exception as e:
                logger.error("dashboard_update_failed", error=str(e))
                await asyncio.sleep(self.update_interval)
    
    async def update_dashboard_data(self):
        """Update dashboard with latest data"""
        
        self.dashboard_data = {
            'timestamp': datetime.now().isoformat(),
            'system_status': await self._get_system_status(),
            'analysis_stats': await self._get_analysis_stats(),
            'recommendation_overview': await self._get_recommendation_overview(),
            'performance_metrics': await self._get_performance_metrics(),
            'recent_activities': await self._get_recent_activities(),
            'code_update_status': await self._get_code_update_status(),
            'alerts': await self._get_current_alerts()
        }
        
        self.last_update = datetime.now()
        
        # Save dashboard snapshot
        await self._save_dashboard_snapshot()
    
    async def _get_system_status(self) -> Dict[str, Any]:
        """Get current system status"""
        
        scheduler_status = await self.scheduler.get_analysis_status()
        
        return {
            'ai_scheduler': {
                'running': scheduler_status['is_running'],
                'next_analysis': scheduler_status.get('next_scheduled'),
                'queue_size': scheduler_status.get('queue_size', 0),
                'last_analysis': scheduler_status.get('last_analysis')
            },
            'claude_engine': {
                'configured': self.claude_engine.claude_api_key is not None,
                'model': self.claude_engine.model,
                'last_analysis': self.claude_engine.last_analysis_time
            },
            'code_updater': {
                'git_available': self.code_updater.repo is not None,
                'backups_available': len(self.code_updater.get_available_rollbacks()),
                'pending_updates': len(self.code_updater.pending_updates)
            }
        }
    
    async def _get_analysis_stats(self) -> Dict[str, Any]:
        """Get analysis statistics"""
        
        scheduler_status = await self.scheduler.get_analysis_status()
        
        return {
            'total_analyses': scheduler_status['total_analyses'],
            'successful_analyses': scheduler_status['successful_analyses'],
            'success_rate': scheduler_status['success_rate'],
            'recommendations_implemented': scheduler_status['recommendations_implemented'],
            'avg_recommendations_per_analysis': self._calculate_avg_recommendations(),
            'analysis_frequency': self._calculate_analysis_frequency()
        }
    
    async def _get_recommendation_overview(self) -> Dict[str, Any]:
        """Get overview of recommendations"""
        
        latest_recommendations = self.claude_engine.get_latest_recommendations()
        
        if not latest_recommendations:
            return {
                'total': 0,
                'by_priority': {},
                'by_category': {},
                'implementation_status': {}
            }
        
        # Categorize recommendations
        by_priority = {}
        by_category = {}
        
        for rec in latest_recommendations:
            # By priority
            priority = rec.priority
            by_priority[priority] = by_priority.get(priority, 0) + 1
            
            # By category
            category = rec.category
            by_category[category] = by_category.get(category, 0) + 1
        
        return {
            'total': len(latest_recommendations),
            'by_priority': by_priority,
            'by_category': by_category,
            'implementation_status': self.recommendation_stats.copy(),
            'latest_recommendations': [
                {
                    'title': rec.title,
                    'priority': rec.priority,
                    'category': rec.category,
                    'has_code_changes': bool(rec.code_changes),
                    'has_config_changes': bool(rec.config_changes)
                }
                for rec in latest_recommendations[:5]  # Show latest 5
            ]
        }
    
    async def _get_performance_metrics(self) -> Dict[str, Any]:
        """Get AI system performance metrics"""
        
        # Calculate performance over last 24 hours
        now = datetime.now()
        last_24h = now - timedelta(hours=24)
        
        recent_performance = [
            p for p in self.performance_history
            if datetime.fromisoformat(p['timestamp']) > last_24h
        ]
        
        if not recent_performance:
            return {
                'analysis_count_24h': 0,
                'avg_analysis_duration': 0,
                'recommendation_accuracy': 0,
                'implementation_success_rate': 0
            }
        
        return {
            'analysis_count_24h': len(recent_performance),
            'avg_analysis_duration': sum(p.get('duration', 0) for p in recent_performance) / len(recent_performance),
            'recommendation_accuracy': self._calculate_recommendation_accuracy(recent_performance),
            'implementation_success_rate': self._calculate_implementation_success_rate(recent_performance),
            'performance_trend': self._calculate_performance_trend()
        }
    
    async def _get_recent_activities(self) -> List[Dict[str, Any]]:
        """Get recent AI activities"""
        
        activities = []
        
        # Get recent analyses
        analysis_history = self.claude_engine.get_analysis_history()
        for analysis in analysis_history[-5:]:  # Last 5 analyses
            activities.append({
                'type': 'analysis',
                'timestamp': analysis['timestamp'],
                'description': f"Analysis completed: {analysis['recommendations_count']} recommendations",
                'status': 'completed'
            })
        
        # Get recent code updates
        update_history = self.code_updater.get_update_history()
        for update in update_history[-5:]:  # Last 5 updates
            activities.append({
                'type': 'code_update',
                'timestamp': update.get('timestamp', ''),
                'description': f"Code update: {update['recommendation_title']}",
                'status': update['status']
            })
        
        # Sort by timestamp (most recent first)
        activities.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return activities[:10]  # Return last 10 activities
    
    async def _get_code_update_status(self) -> Dict[str, Any]:
        """Get code update system status"""
        
        update_history = self.code_updater.get_update_history()
        rollback_points = self.code_updater.get_available_rollbacks()
        
        # Calculate update statistics
        total_updates = len(update_history)
        successful_updates = len([u for u in update_history if u['status'] == 'applied'])
        failed_updates = len([u for u in update_history if u['status'] == 'failed'])
        
        return {
            'total_updates': total_updates,
            'successful_updates': successful_updates,
            'failed_updates': failed_updates,
            'success_rate': (successful_updates / max(total_updates, 1)) * 100,
            'rollback_points_available': len(rollback_points),
            'latest_update': update_history[-1] if update_history else None,
            'git_status': self._get_git_status()
        }
    
    async def _get_current_alerts(self) -> List[Dict[str, Any]]:
        """Get current system alerts"""
        
        alerts = []
        
        # Check for system issues
        system_status = await self._get_system_status()
        
        # AI Scheduler alerts
        if not system_status['ai_scheduler']['running']:
            alerts.append({
                'level': 'error',
                'message': 'AI Analysis Scheduler is not running',
                'timestamp': datetime.now().isoformat(),
                'category': 'system'
            })
        
        # Claude API alerts
        if not system_status['claude_engine']['configured']:
            alerts.append({
                'level': 'warning',
                'message': 'Claude API not configured',
                'timestamp': datetime.now().isoformat(),
                'category': 'configuration'
            })
        
        # Performance alerts
        performance = await self._get_performance_metrics()
        if performance['recommendation_accuracy'] < 70:
            alerts.append({
                'level': 'warning',
                'message': f'Low recommendation accuracy: {performance["recommendation_accuracy"]:.1f}%',
                'timestamp': datetime.now().isoformat(),
                'category': 'performance'
            })
        
        return alerts
    
    def _calculate_avg_recommendations(self) -> float:
        """Calculate average recommendations per analysis"""
        
        analysis_history = self.claude_engine.get_analysis_history()
        if not analysis_history:
            return 0
        
        total_recommendations = sum(a.get('recommendations_count', 0) for a in analysis_history)
        return total_recommendations / len(analysis_history)
    
    def _calculate_analysis_frequency(self) -> str:
        """Calculate analysis frequency"""
        
        analysis_history = self.claude_engine.get_analysis_history()
        if len(analysis_history) < 2:
            return "Insufficient data"
        
        # Calculate average time between analyses
        timestamps = [datetime.fromisoformat(a['timestamp']) for a in analysis_history[-10:]]
        intervals = [(timestamps[i] - timestamps[i-1]).total_seconds() for i in range(1, len(timestamps))]
        
        if intervals:
            avg_interval = sum(intervals) / len(intervals)
            hours = avg_interval / 3600
            
            if hours < 1:
                return f"Every {avg_interval/60:.0f} minutes"
            elif hours < 24:
                return f"Every {hours:.1f} hours"
            else:
                return f"Every {hours/24:.1f} days"
        
        return "Unknown"
    
    def _calculate_recommendation_accuracy(self, performance_data: List[Dict[str, Any]]) -> float:
        """Calculate recommendation accuracy based on performance"""
        
        # This would be implemented based on actual performance tracking
        # For now, return a placeholder calculation
        if not performance_data:
            return 0
        
        # Simplified accuracy calculation
        successful_implementations = sum(1 for p in performance_data if p.get('implementation_success', False))
        return (successful_implementations / len(performance_data)) * 100
    
    def _calculate_implementation_success_rate(self, performance_data: List[Dict[str, Any]]) -> float:
        """Calculate implementation success rate"""
        
        update_history = self.code_updater.get_update_history()
        if not update_history:
            return 0
        
        successful = len([u for u in update_history if u['status'] == 'applied'])
        return (successful / len(update_history)) * 100
    
    def _calculate_performance_trend(self) -> str:
        """Calculate performance trend over time"""
        
        # Simplified trend calculation
        recent_analyses = self.claude_engine.get_analysis_history()[-10:]
        
        if len(recent_analyses) < 5:
            return "insufficient_data"
        
        # Calculate success rate trend
        recent_success = len([a for a in recent_analyses[-5:] if a.get('success', True)])
        older_success = len([a for a in recent_analyses[-10:-5] if a.get('success', True)])
        
        if recent_success > older_success:
            return "improving"
        elif recent_success < older_success:
            return "declining"
        else:
            return "stable"
    
    def _get_git_status(self) -> Dict[str, Any]:
        """Get git repository status"""
        
        if not self.code_updater.repo:
            return {'available': False}
        
        try:
            repo = self.code_updater.repo
            
            return {
                'available': True,
                'current_branch': repo.active_branch.name,
                'latest_commit': repo.head.commit.hexsha[:8],
                'commit_message': repo.head.commit.message.strip(),
                'commit_time': repo.head.commit.committed_datetime.isoformat(),
                'is_dirty': repo.is_dirty(),
                'untracked_files': len(repo.untracked_files)
            }
        except Exception as e:
            logger.warning("git_status_failed", error=str(e))
            return {'available': True, 'error': str(e)}
    
    async def _save_dashboard_snapshot(self):
        """Save dashboard snapshot for historical tracking"""
        
        try:
            snapshot_dir = Path('data/dashboard_snapshots')
            snapshot_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            snapshot_file = snapshot_dir / f'dashboard_{timestamp}.json'
            
            with open(snapshot_file, 'w') as f:
                json.dump(self.dashboard_data, f, indent=2, default=str)
            
            # Keep only last 100 snapshots
            snapshots = sorted(snapshot_dir.glob('dashboard_*.json'))
            if len(snapshots) > 100:
                for old_snapshot in snapshots[:-100]:
                    old_snapshot.unlink()
            
        except Exception as e:
            logger.warning("dashboard_snapshot_save_failed", error=str(e))
    
    async def request_manual_analysis(self, focus_area: str, 
                                    custom_prompt: Optional[str] = None) -> str:
        """Request manual analysis through dashboard"""
        
        logger.info("manual_analysis_requested_via_dashboard", 
                   focus_area=focus_area)
        
        result = await self.scheduler.request_manual_analysis(focus_area, custom_prompt)
        
        # Update dashboard activity
        await self._log_dashboard_activity('manual_analysis', {
            'focus_area': focus_area,
            'custom_prompt': bool(custom_prompt),
            'timestamp': datetime.now().isoformat()
        })
        
        return result
    
    async def force_analysis(self) -> Dict[str, Any]:
        """Force immediate analysis through dashboard"""
        
        await self.scheduler.force_analysis('dashboard_manual')
        
        await self._log_dashboard_activity('forced_analysis', {
            'trigger': 'dashboard',
            'timestamp': datetime.now().isoformat()
        })
        
        return {'status': 'queued', 'message': 'Analysis has been queued for immediate execution'}
    
    async def approve_recommendation(self, recommendation_id: str) -> Dict[str, Any]:
        """Approve a recommendation for implementation"""
        
        # This would implement recommendation approval workflow
        # For now, return placeholder
        
        await self._log_dashboard_activity('recommendation_approved', {
            'recommendation_id': recommendation_id,
            'timestamp': datetime.now().isoformat()
        })
        
        return {'status': 'approved', 'recommendation_id': recommendation_id}
    
    async def reject_recommendation(self, recommendation_id: str, reason: str) -> Dict[str, Any]:
        """Reject a recommendation"""
        
        await self._log_dashboard_activity('recommendation_rejected', {
            'recommendation_id': recommendation_id,
            'reason': reason,
            'timestamp': datetime.now().isoformat()
        })
        
        return {'status': 'rejected', 'recommendation_id': recommendation_id}
    
    async def rollback_update(self, update_id: str) -> Dict[str, Any]:
        """Rollback a code update through dashboard"""
        
        success = await self.code_updater.manual_rollback(update_id)
        
        await self._log_dashboard_activity('manual_rollback', {
            'update_id': update_id,
            'success': success,
            'timestamp': datetime.now().isoformat()
        })
        
        return {'status': 'success' if success else 'failed', 'update_id': update_id}
    
    async def _log_dashboard_activity(self, activity_type: str, data: Dict[str, Any]):
        """Log dashboard activity for tracking"""
        
        activity = {
            'type': activity_type,
            'data': data,
            'timestamp': datetime.now().isoformat()
        }
        
        # Add to recent activities
        if not hasattr(self, 'dashboard_activities'):
            self.dashboard_activities = []
        
        self.dashboard_activities.append(activity)
        
        # Keep only last 100 activities
        self.dashboard_activities = self.dashboard_activities[-100:]
        
        logger.info("dashboard_activity_logged", 
                   type=activity_type,
                   timestamp=data.get('timestamp'))
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get current dashboard data"""
        return self.dashboard_data.copy()
    
    def get_real_time_stats(self) -> Dict[str, Any]:
        """Get real-time statistics for live updates"""
        
        return {
            'timestamp': datetime.now().isoformat(),
            'scheduler_queue_size': self.scheduler.analysis_queue.qsize() if hasattr(self.scheduler, 'analysis_queue') else 0,
            'last_analysis': self.claude_engine.last_analysis_time,
            'system_uptime': (datetime.now() - self.last_update).total_seconds(),
            'recent_alerts_count': len(self.dashboard_data.get('alerts', [])),
            'recommendations_pending': self.recommendation_stats.get('pending', 0)
        }