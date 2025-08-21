"""
AI Analysis Scheduler for SmartArb Engine
Automated scheduling and execution of Claude AI analysis
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import structlog
from croniter import croniter

from .claude_integration import ClaudeAnalysisEngine, ClaudeRecommendation
from ..utils.notifications import NotificationManager, NotificationLevel
from ..utils.config import ConfigManager
from ..db.connection import DatabaseManager

logger = structlog.get_logger(__name__)


class AIAnalysisScheduler:
    """
    Automated AI Analysis Scheduler
    
    Features:
    - Scheduled performance analysis
    - Adaptive scheduling based on performance
    - Emergency analysis triggers
    - Recommendation tracking and implementation
    - Performance feedback loop
    """
    
    def __init__(self, config: ConfigManager, db_manager: DatabaseManager, 
                 notification_manager: NotificationManager):
        self.config = config
        self.db_manager = db_manager
        self.notification_manager = notification_manager
        
        # Initialize Claude integration
        self.claude_engine = ClaudeAnalysisEngine(config, db_manager)
        
        # Scheduling configuration
        self.schedule_config = config.get('ai.scheduling', {})
        self.default_schedule = self.schedule_config.get('default', '0 */6 * * *')  # Every 6 hours
        self.emergency_triggers = self.schedule_config.get('emergency_triggers', {})
        
        # Analysis state
        self.is_running = False
        self.scheduler_task = None
        self.last_analysis = None
        self.analysis_queue = asyncio.Queue()
        
        # Performance tracking
        self.total_analyses = 0
        self.successful_analyses = 0
        self.recommendations_implemented = 0
        
        # Emergency analysis triggers
        self.performance_thresholds = {
            'low_success_rate': 60.0,  # Below 60% success rate
            'high_drawdown': -100.0,   # More than $100 loss
            'execution_latency': 5000, # Over 5 seconds avg latency
            'failed_trades_streak': 5   # 5 consecutive failed trades
        }
        
        logger.info("ai_analysis_scheduler_initialized",
                   default_schedule=self.default_schedule)
    
    async def start(self):
        """Start the analysis scheduler"""
        if self.is_running:
            logger.warning("scheduler_already_running")
            return
        
        self.is_running = True
        
        # Start scheduler task
        self.scheduler_task = asyncio.create_task(self._scheduler_loop())
        
        # Start analysis processor
        self.processor_task = asyncio.create_task(self._analysis_processor())
        
        logger.info("ai_analysis_scheduler_started")
        
        # Send initial notification
        await self.notification_manager.send_notification(
            "🧠 AI Analysis Scheduler Started",
            f"Automated analysis will run: {self.default_schedule}",
            NotificationLevel.INFO
        )
    
    async def stop(self):
        """Stop the analysis scheduler"""
        if not self.is_running:
            return
        
        self.is_running = False
        
        # Cancel tasks
        if self.scheduler_task:
            self.scheduler_task.cancel()
            try:
                await self.scheduler_task
            except asyncio.CancelledError:
                pass
        
        if self.processor_task:
            self.processor_task.cancel()
            try:
                await self.processor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("ai_analysis_scheduler_stopped")
    
    async def _scheduler_loop(self):
        """Main scheduler loop"""
        cron = croniter(self.default_schedule, datetime.now())
        
        while self.is_running:
            try:
                # Calculate next run time
                next_run = cron.get_next(datetime)
                sleep_duration = (next_run - datetime.now()).total_seconds()
                
                if sleep_duration > 0:
                    logger.debug("scheduler_waiting", 
                               next_run=next_run.isoformat(),
                               sleep_duration=sleep_duration)
                    
                    # Sleep until next scheduled time, but check for emergency triggers
                    await self._sleep_with_emergency_check(sleep_duration)
                
                # Queue scheduled analysis
                if self.is_running:
                    await self.queue_analysis('scheduled')
                
            except Exception as e:
                logger.error("scheduler_loop_error", error=str(e))
                await asyncio.sleep(60)  # Wait 1 minute before retrying
    
    async def _sleep_with_emergency_check(self, duration: float):
        """Sleep with periodic emergency trigger checks"""
        check_interval = min(300, duration / 10)  # Check every 5 minutes or 10% of duration
        elapsed = 0
        
        while elapsed < duration and self.is_running:
            sleep_time = min(check_interval, duration - elapsed)
            await asyncio.sleep(sleep_time)
            elapsed += sleep_time
            
            # Check for emergency triggers
            if await self._check_emergency_triggers():
                logger.info("emergency_analysis_triggered")
                await self.queue_analysis('emergency')
                break
    
    async def _check_emergency_triggers(self) -> bool:
        """Check if emergency analysis should be triggered"""
        try:
            # Get recent performance data
            recent_data = await self._get_recent_performance_data()
            
            # Check each trigger condition
            triggers_activated = []
            
            # Low success rate
            if recent_data.get('success_rate', 100) < self.performance_thresholds['low_success_rate']:
                triggers_activated.append('low_success_rate')
            
            # High drawdown
            if recent_data.get('drawdown', 0) < self.performance_thresholds['high_drawdown']:
                triggers_activated.append('high_drawdown')
            
            # High execution latency
            if recent_data.get('avg_latency', 0) > self.performance_thresholds['execution_latency']:
                triggers_activated.append('execution_latency')
            
            # Consecutive failed trades
            if recent_data.get('consecutive_failures', 0) >= self.performance_thresholds['failed_trades_streak']:
                triggers_activated.append('failed_trades_streak')
            
            if triggers_activated:
                logger.warning("emergency_triggers_activated", triggers=triggers_activated)
                
                # Send emergency notification
                await self.notification_manager.send_notification(
                    "🚨 Emergency AI Analysis Triggered",
                    f"Triggers: {', '.join(triggers_activated)}",
                    NotificationLevel.ERROR
                )
                
                return True
            
            return False
            
        except Exception as e:
            logger.error("emergency_trigger_check_failed", error=str(e))
            return False
    
    async def _get_recent_performance_data(self) -> Dict[str, Any]:
        """Get recent performance data for trigger checking"""
        # This would integrate with the actual portfolio and risk managers
        # For now, return mock data structure
        return {
            'success_rate': 75.0,
            'drawdown': -25.0,
            'avg_latency': 1200,
            'consecutive_failures': 2
        }
    
    async def queue_analysis(self, analysis_type: str = 'scheduled', 
                           priority: str = 'normal', 
                           custom_focus: Optional[str] = None):
        """Queue an analysis request"""
        analysis_request = {
            'type': analysis_type,
            'priority': priority,
            'custom_focus': custom_focus,
            'timestamp': datetime.now(),
            'id': f"{analysis_type}_{int(datetime.now().timestamp())}"
        }
        
        await self.analysis_queue.put(analysis_request)
        
        logger.info("analysis_queued", 
                   type=analysis_type,
                   priority=priority,
                   queue_size=self.analysis_queue.qsize())
    
    async def _analysis_processor(self):
        """Process queued analysis requests"""
        while self.is_running:
            try:
                # Get next analysis request
                analysis_request = await asyncio.wait_for(
                    self.analysis_queue.get(), timeout=1.0
                )
                
                # Execute analysis
                await self._execute_analysis(analysis_request)
                
                # Mark task done
                self.analysis_queue.task_done()
                
            except asyncio.TimeoutError:
                continue  # Normal timeout, continue loop
            except Exception as e:
                logger.error("analysis_processor_error", error=str(e))
                await asyncio.sleep(5)
    
    async def _execute_analysis(self, request: Dict[str, Any]):
        """Execute a single analysis request"""
        analysis_id = request['id']
        analysis_type = request['type']
        
        logger.info("executing_analysis", 
                   id=analysis_id,
                   type=analysis_type)
        
        try:
            start_time = datetime.now()
            
            # Run Claude analysis
            recommendations = await self.claude_engine.run_automated_analysis()
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            if recommendations:
                self.successful_analyses += 1
                
                # Process recommendations
                await self._process_recommendations(recommendations, analysis_id)
                
                # Send success notification
                await self.notification_manager.send_notification(
                    f"🧠 AI Analysis Complete - {analysis_type.title()}",
                    f"Found {len(recommendations)} recommendations\n"
                    f"Execution time: {execution_time:.1f}s",
                    NotificationLevel.INFO
                )
                
                logger.info("analysis_completed_successfully",
                           id=analysis_id,
                           recommendations_count=len(recommendations),
                           execution_time=execution_time)
            else:
                logger.warning("analysis_completed_no_recommendations", id=analysis_id)
            
            self.total_analyses += 1
            self.last_analysis = datetime.now()
            
        except Exception as e:
            logger.error("analysis_execution_failed", 
                        id=analysis_id,
                        error=str(e))
            
            # Send failure notification
            await self.notification_manager.send_notification(
                f"❌ AI Analysis Failed - {analysis_type.title()}",
                f"Error: {str(e)}",
                NotificationLevel.ERROR
            )
    
    async def _process_recommendations(self, recommendations: List[ClaudeRecommendation], 
                                     analysis_id: str):
        """Process and categorize recommendations"""
        
        high_priority = [r for r in recommendations if r.priority == 'high']
        critical_priority = [r for r in recommendations if r.priority == 'critical']
        auto_applicable = [r for r in recommendations 
                          if r.priority in ['low', 'medium'] and r.config_changes]
        
        # Send summary notification
        summary = f"""
📊 Analysis Results ({analysis_id}):

🔴 Critical: {len(critical_priority)}
🟡 High Priority: {len(high_priority)}
🟢 Auto-Applied: {len(auto_applicable)}
📝 Total: {len(recommendations)}

Top Recommendations:
"""
        
        # Add top 3 recommendations to summary
        for i, rec in enumerate(recommendations[:3]):
            summary += f"\n{i+1}. [{rec.priority.upper()}] {rec.title}"
        
        await self.notification_manager.send_notification(
            "📋 AI Analysis Summary",
            summary,
            NotificationLevel.INFO
        )
        
        # Send critical alerts immediately
        for rec in critical_priority:
            await self.notification_manager.send_notification(
                f"🚨 CRITICAL: {rec.title}",
                f"{rec.description}\n\nRisks: {', '.join(rec.risks or [])}",
                NotificationLevel.CRITICAL
            )
    
    async def request_manual_analysis(self, focus_area: str, 
                                    custom_prompt: Optional[str] = None) -> str:
        """Request manual analysis with specific focus"""
        
        logger.info("manual_analysis_requested", focus_area=focus_area)
        
        if custom_prompt:
            prompt = f"Focus on {focus_area}: {custom_prompt}"
        else:
            prompt = f"Please provide detailed analysis focusing on: {focus_area}"
        
        try:
            result = await self.claude_engine.get_manual_analysis(prompt)
            
            # Send result via notification
            await self.notification_manager.send_notification(
                f"🧠 Manual Analysis: {focus_area}",
                result[:500] + "..." if len(result) > 500 else result,
                NotificationLevel.INFO
            )
            
            return result
            
        except Exception as e:
            logger.error("manual_analysis_failed", error=str(e))
            return f"Analysis failed: {str(e)}"
    
    async def get_analysis_status(self) -> Dict[str, Any]:
        """Get current analysis status and statistics"""
        
        success_rate = (self.successful_analyses / max(self.total_analyses, 1)) * 100
        
        return {
            'is_running': self.is_running,
            'total_analyses': self.total_analyses,
            'successful_analyses': self.successful_analyses,
            'success_rate': success_rate,
            'recommendations_implemented': self.recommendations_implemented,
            'last_analysis': self.last_analysis.isoformat() if self.last_analysis else None,
            'queue_size': self.analysis_queue.qsize(),
            'next_scheduled': self._get_next_scheduled_time(),
            'emergency_triggers': self.performance_thresholds
        }
    
    def _get_next_scheduled_time(self) -> Optional[str]:
        """Get next scheduled analysis time"""
        try:
            cron = croniter(self.default_schedule, datetime.now())
            next_run = cron.get_next(datetime)
            return next_run.isoformat()
        except:
            return None
    
    async def update_schedule(self, new_schedule: str):
        """Update analysis schedule"""
        try:
            # Validate cron expression
            croniter(new_schedule)
            
            self.default_schedule = new_schedule
            self.config.set('ai.scheduling.default', new_schedule)
            
            logger.info("analysis_schedule_updated", schedule=new_schedule)
            
            await self.notification_manager.send_notification(
                "⏰ Analysis Schedule Updated",
                f"New schedule: {new_schedule}",
                NotificationLevel.INFO
            )
            
        except Exception as e:
            logger.error("schedule_update_failed", error=str(e))
            raise ValueError(f"Invalid cron expression: {new_schedule}")
    
    async def force_analysis(self, analysis_type: str = 'manual'):
        """Force immediate analysis execution"""
        await self.queue_analysis(analysis_type, priority='high')
        
        logger.info("forced_analysis_queued", type=analysis_type)
        
        await self.notification_manager.send_notification(
            "🔄 Manual Analysis Triggered",
            f"Analysis type: {analysis_type}",
            NotificationLevel.INFO
        )
