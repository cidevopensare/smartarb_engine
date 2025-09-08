“””
AI Analysis Scheduler for SmartArb Engine
Automated scheduling and execution of Claude AI analysis tasks
“””

import asyncio
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from enum import Enum
import time
from datetime import datetime, timedelta
import structlog
from croniter import croniter

from .claude_integration import ClaudeAnalysisEngine, AnalysisType, AnalysisContext

logger = structlog.get_logger(**name**)

class TriggerType(Enum):
“”“Types of analysis triggers”””
SCHEDULED = “scheduled”
PERFORMANCE_THRESHOLD = “performance_threshold”
RISK_THRESHOLD = “risk_threshold”
ERROR_THRESHOLD = “error_threshold”
MANUAL = “manual”
EMERGENCY = “emergency”

@dataclass
class AnalysisTrigger:
“”“Analysis trigger configuration”””
id: str
name: str
trigger_type: TriggerType
analysis_type: AnalysisType
enabled: bool
schedule: Optional[str] = None  # Cron expression for scheduled triggers
threshold_value: Optional[float] = None  # For threshold-based triggers
threshold_metric: Optional[str] = None  # Metric to check for threshold triggers
cooldown_minutes: int = 60  # Minimum time between triggers
priority: str = “medium”  # low, medium, high, critical
last_triggered: float = 0
trigger_count: int = 0

```
def should_trigger(self, current_metrics: Dict[str, Any] = None) -> bool:
    """Check if trigger should fire"""
    now = time.time()
    
    # Check cooldown
    if now - self.last_triggered < (self.cooldown_minutes * 60):
        return False
    
    if self.trigger_type == TriggerType.SCHEDULED:
        return self._check_schedule_trigger()
    elif self.trigger_type in [TriggerType.PERFORMANCE_THRESHOLD, 
                              TriggerType.RISK_THRESHOLD, 
                              TriggerType.ERROR_THRESHOLD]:
        return self._check_threshold_trigger(current_metrics)
    
    return False

def _check_schedule_trigger(self) -> bool:
    """Check if scheduled trigger should fire"""
    if not self.schedule:
        return False
    
    try:
        cron = croniter(self.schedule, datetime.fromtimestamp(self.last_triggered))
        next_run = cron.get_next()
        return time.time() >= next_run
    except Exception as e:
        logger.error("schedule_trigger_check_failed", 
                    trigger_id=self.id, 
                    schedule=self.schedule,
                    error=str(e))
        return False

def _check_threshold_trigger(self, metrics: Dict[str, Any]) -> bool:
    """Check if threshold trigger should fire"""
    if not metrics or not self.threshold_metric or self.threshold_value is None:
        return False
    
    current_value = metrics.get(self.threshold_metric)
    if current_value is None:
        return False
    
    try:
        current_value = float(current_value)
        
        if self.trigger_type == TriggerType.PERFORMANCE_THRESHOLD:
            # Performance degrades (value goes below threshold)
            return current_value < self.threshold_value
        elif self.trigger_type == TriggerType.RISK_THRESHOLD:
            # Risk increases (value goes above threshold)
            return current_value > self.threshold_value
        elif self.trigger_type == TriggerType.ERROR_THRESHOLD:
            # Error rate increases (value goes above threshold)
            return current_value > self.threshold_value
            
    except (ValueError, TypeError):
        logger.warning("threshold_value_conversion_failed",
                     trigger_id=self.id,
                     metric=self.threshold_metric,
                     value=current_value)
    
    return False
```

class AIAnalysisScheduler:
“””
AI Analysis Scheduler

```
Features:
- Scheduled analysis execution
- Threshold-based trigger system
- Emergency analysis triggers
- Priority-based execution queue
- Cooldown management
- Performance monitoring
"""

def __init__(self, config: Dict[str, Any], db_manager=None, notification_manager=None):
    self.config = config
    self.db_manager = db_manager
    self.notification_manager = notification_manager
    
    # Initialize Claude Analysis Engine
    self.claude_engine = ClaudeAnalysisEngine(config, db_manager)
    
    # Scheduler configuration
    ai_config = config.get('ai', {})
    scheduling_config = ai_config.get('scheduling', {})
    
    self.enabled = ai_config.get('enabled', True)
    self.default_schedule = scheduling_config.get('default', '0 6 * * *')  # Daily at 6 AM
    self.max_concurrent_analyses = scheduling_config.get('max_concurrent', 2)
    
    # Emergency triggers
    emergency_config = scheduling_config.get('emergency_triggers', {})
    self.emergency_triggers = self._setup_emergency_triggers(emergency_config)
    
    # Trigger management
    self.triggers: Dict[str, AnalysisTrigger] = {}
    self.execution_queue: List[str] = []  # List of trigger IDs to execute
    self.running_analyses: Dict[str, asyncio.Task] = {}
    
    # Performance tracking
    self.total_executions = 0
    self.successful_executions = 0
    self.failed_executions = 0
    self.avg_execution_time = 0.0
    
    # Data collection callbacks
    self.metric_collectors: Dict[str, Callable[[], Dict[str, Any]]] = {}
    
    # Setup default triggers
    self._setup_default_triggers()
    
    # Scheduler state
    self.running = False
    self.scheduler_task = None
    
    logger.info("ai_analysis_scheduler_initialized",
               enabled=self.enabled,
               triggers=len(self.triggers),
               emergency_triggers=len(self.emergency_triggers))

def _setup_emergency_triggers(self, emergency_config: Dict[str, Any]) -> Dict[str, AnalysisTrigger]:
    """Setup emergency analysis triggers"""
    triggers = {}
    
    # Low success rate trigger
    if 'low_success_rate' in emergency_config:
        triggers['emergency_low_success_rate'] = AnalysisTrigger(
            id='emergency_low_success_rate',
            name='Emergency: Low Success Rate',
            trigger_type=TriggerType.PERFORMANCE_THRESHOLD,
            analysis_type=AnalysisType.EMERGENCY_ANALYSIS,
            enabled=True,
            threshold_value=emergency_config['low_success_rate'],
            threshold_metric='success_rate',
            cooldown_minutes=30,
            priority='critical'
        )
    
    # High drawdown trigger
    if 'high_drawdown' in emergency_config:
        triggers['emergency_high_drawdown'] = AnalysisTrigger(
            id='emergency_high_drawdown',
            name='Emergency: High Drawdown',
            trigger_type=TriggerType.RISK_THRESHOLD,
            analysis_type=AnalysisType.EMERGENCY_ANALYSIS,
            enabled=True,
            threshold_value=emergency_config['high_drawdown'],
            threshold_metric='daily_pnl',
            cooldown_minutes=15,
            priority='critical'
        )
    
    # High error rate trigger
    if 'high_error_rate' in emergency_config:
        triggers['emergency_high_error_rate'] = AnalysisTrigger(
            id='emergency_high_error_rate',
            name='Emergency: High Error Rate',
            trigger_type=TriggerType.ERROR_THRESHOLD,
            analysis_type=AnalysisType.ERROR_ANALYSIS,
            enabled=True,
            threshold_value=emergency_config['high_error_rate'],
            threshold_metric='error_rate',
            cooldown_minutes=30,
            priority='critical'
        )
    
    return triggers

def _setup_default_triggers(self) -> None:
    """Setup default analysis triggers"""
    
    # Daily performance analysis
    self.add_trigger(AnalysisTrigger(
        id='daily_performance',
        name='Daily Performance Analysis',
        trigger_type=TriggerType.SCHEDULED,
        analysis_type=AnalysisType.PERFORMANCE_ANALYSIS,
        enabled=True,
        schedule=self.default_schedule,
        cooldown_minutes=1440,  # Once per day
        priority='medium'
    ))
    
    # Daily summary
    self.add_trigger(AnalysisTrigger(
        id='daily_summary',
        name='Daily Summary Report',
        trigger_type=TriggerType.SCHEDULED,
        analysis_type=AnalysisType.DAILY_SUMMARY,
        enabled=True,
        schedule='0 23 * * *',  # 11 PM daily
        cooldown_minutes=1440,
        priority='medium'
    ))
    
    # Risk assessment (every 6 hours)
    self.add_trigger(AnalysisTrigger(
        id='risk_assessment',
        name='Risk Assessment',
        trigger_type=TriggerType.SCHEDULED,
        analysis_type=AnalysisType.RISK_ASSESSMENT,
        enabled=True,
        schedule='0 */6 * * *',  # Every 6 hours
        cooldown_minutes=360,
        priority='high'
    ))
    
    # Strategy optimization (weekly)
    self.add_trigger(AnalysisTrigger(
        id='strategy_optimization',
        name='Weekly Strategy Optimization',
        trigger_type=TriggerType.SCHEDULED,
        analysis_type=AnalysisType.STRATEGY_OPTIMIZATION,
        enabled=True,
        schedule='0 2 * * 0',  # 2 AM every Sunday
        cooldown_minutes=10080,  # Once per week
        priority='medium'
    ))
    
    # Add emergency triggers
    for trigger in self.emergency_triggers.values():
        self.add_trigger(trigger)

def add_trigger(self, trigger: AnalysisTrigger) -> None:
    """Add a new analysis trigger"""
    self.triggers[trigger.id] = trigger
    logger.info("analysis_trigger_added",
               trigger_id=trigger.id,
               name=trigger.name,
               type=trigger.trigger_type.value)

def remove_trigger(self, trigger_id: str) -> bool:
    """Remove an analysis trigger"""
    if trigger_id in self.triggers:
        del self.triggers[trigger_id]
        logger.info("analysis_trigger_removed", trigger_id=trigger_id)
        return True
    return False

def register_metric_collector(self, name: str, collector_func: Callable[[], Dict[str, Any]]) -> None:
    """Register a function that collects metrics for trigger evaluation"""
    self.metric_collectors[name] = collector_func
    logger.info("metric_collector_registered", name=name)

async def start(self) -> None:
    """Start the analysis scheduler"""
    if self.running:
        logger.warning("analysis_scheduler_already_running")
        return
    
    if not self.enabled:
        logger.info("analysis_scheduler_disabled")
        return
    
    self.running = True
    self.scheduler_task = asyncio.create_task(self._scheduler_loop())
    logger.info("analysis_scheduler_started")

async def stop(self) -> None:
    """Stop the analysis scheduler"""
    if not self.running:
        return
    
    self.running = False
    
    # Cancel scheduler task
    if self.scheduler_task:
        self.scheduler_task.cancel()
        try:
            await self.scheduler_task
        except asyncio.CancelledError:
            pass
    
    # Cancel running analyses
    for task in self.running_analyses.values():
        task.cancel()
    
    if self.running_analyses:
        await asyncio.gather(*self.running_analyses.values(), return_exceptions=True)
    
    self.running_analyses.clear()
    logger.info("analysis_scheduler_stopped")

async def _scheduler_loop(self) -> None:
    """Main scheduler loop"""
    while self.running:
        try:
            # Collect current metrics
            current_metrics = await self._collect_metrics()
            
            # Check triggers
            triggered_analyses = self._check_triggers(current_metrics)
            
            # Add to execution queue
            for trigger_id in triggered_analyses:
                if trigger_id not in self.execution_queue:
                    self.execution_queue.append(trigger_id)
            
            # Execute queued analyses
            await self._execute_queued_analyses()
            
            # Clean up completed analyses
            self._cleanup_completed_analyses()
            
            # Sleep for 60 seconds before next check
            await asyncio.sleep(60)
            
        except Exception as e:
            logger.error("scheduler_loop_error", error=str(e))
            await asyncio.sleep(60)  # Continue after error

async def _collect_metrics(self) -> Dict[str, Any]:
    """Collect metrics from registered collectors"""
    metrics = {}
    
    for name, collector in self.metric_collectors.items():
        try:
            collector_metrics = collector()
            if isinstance(collector_metrics, dict):
                metrics.update(collector_metrics)
        except Exception as e:
            logger.error("metric_collection_failed",
                       collector=name,
                       error=str(e))
    
    return metrics

def _check_triggers(self, current_metrics: Dict[str, Any]) -> List[str]:
    """Check all triggers and return list of triggered analysis IDs"""
    triggered = []
    
    for trigger_id, trigger in self.triggers.items():
        if not trigger.enabled:
            continue
        
        try:
            if trigger.should_trigger(current_metrics):
                triggered.append(trigger_id)
                trigger.last_triggered = time.time()
                trigger.trigger_count += 1
                
                logger.info("analysis_trigger_fired",
                           trigger_id=trigger_id,
                           name=trigger.name,
                           type=trigger.trigger_type.value,
                           priority=trigger.priority)
                
        except Exception as e:
            logger.error("trigger_check_failed",
                       trigger_id=trigger_id,
                       error=str(e))
    
    return triggered

async def _execute_queued_analyses(self) -> None:
    """Execute analyses from the queue"""
    while (self.execution_queue and 
           len(self.running_analyses) < self.max_concurrent_analyses):
        
        # Sort queue by priority
        self.execution_queue.sort(key=lambda tid: self._get_trigger_priority_value(tid), reverse=True)
        
        trigger_id = self.execution_queue.pop(0)
        
        # Start analysis task
        task = asyncio.create_task(self._execute_analysis(trigger_id))
        self.running_analyses[trigger_id] = task

def _get_trigger_priority_value(self, trigger_id: str) -> int:
    """Get numeric priority value for sorting"""
    priority_values = {'critical': 4, 'high': 3, 'medium': 2, 'low': 1}
    trigger = self.triggers.get(trigger_id)
    if trigger:
        return priority_values.get(trigger.priority, 1)
    return 1

async def _execute_analysis(self, trigger_id: str) -> None:
    """Execute a single analysis"""
    trigger = self.triggers.get(trigger_id)
    if not trigger:
        logger.error("trigger_not_found", trigger_id=trigger_id)
        return
    
    start_time = time.time()
    self.total_executions += 1
    
    try:
        logger.info("analysis_execution_started",
                   trigger_id=trigger_id,
                   analysis_type=trigger.analysis_type.value)
        
        # Collect data for analysis
        analysis_context = await self._prepare_analysis_context(trigger)
        
        # Perform analysis
        result = await self.claude_engine.analyze(analysis_context)
        
        # Handle result
        await self._handle_analysis_result(trigger, result)
        
        execution_time = time.time() - start_time
        self.successful_executions += 1
        self._update_avg_execution_time(execution_time)
        
        logger.info("analysis_execution_completed",
                   trigger_id=trigger_id,
                   success=result.success,
                   execution_time=execution_time,
                   recommendations=len(result.recommendations))
        
    except Exception as e:
        execution_time = time.time() - start_time
        self.failed_executions += 1
        
        logger.error("analysis_execution_failed",
                    trigger_id=trigger_id,
                    error=str(e),
                    execution_time=execution_time)

async def _prepare_analysis_context(self, trigger: AnalysisTrigger) -> AnalysisContext:
    """Prepare analysis context based on trigger type"""
    # Collect comprehensive data
    metrics = await self._collect_metrics()
    
    # Determine time range based on analysis type
    time_ranges = {
        AnalysisType.PERFORMANCE_ANALYSIS: "24h",
        AnalysisType.RISK_ASSESSMENT: "current",
        AnalysisType.STRATEGY_OPTIMIZATION: "7d",
        AnalysisType.MARKET_ANALYSIS: "24h",
        AnalysisType.ERROR_ANALYSIS: "24h",
        AnalysisType.PORTFOLIO_OPTIMIZATION: "current",
        AnalysisType.EMERGENCY_ANALYSIS: "1h",
        AnalysisType.DAILY_SUMMARY: "24h"
    }
    
    time_range = time_ranges.get(trigger.analysis_type, "24h")
    
    # Determine focus areas based on trigger
    focus_areas = []
    if trigger.trigger_type == TriggerType.PERFORMANCE_THRESHOLD:
        focus_areas = ["performance_issues", "optimization_opportunities"]
    elif trigger.trigger_type == TriggerType.RISK_THRESHOLD:
        focus_areas = ["risk_mitigation", "portfolio_protection"]
    elif trigger.trigger_type == TriggerType.ERROR_THRESHOLD:
        focus_areas = ["error_analysis", "system_reliability"]
    else:
        focus_areas = ["general_optimization", "performance_monitoring"]
    
    return AnalysisContext(
        analysis_type=trigger.analysis_type,
        time_range=time_range,
        focus_areas=focus_areas,
        performance_data=metrics.get('performance', {}),
        risk_metrics=metrics.get('risk', {}),
        market_data=metrics.get('market', {}),
        system_state=metrics.get('system', {}),
        recent_events=metrics.get('events', [])
    )

async def _handle_analysis_result(self, trigger: AnalysisTrigger, result) -> None:
    """Handle analysis result (notifications, storage, etc.)"""
    try:
        # Send notification if configured
        if self.notification_manager and result.success:
            priority_mapping = {
                'critical': 'HIGH',
                'high': 'HIGH', 
                'medium': 'MEDIUM',
                'low': 'LOW'
            }
            
            await self.notification_manager.notify_ai_analysis(
                analysis_type=trigger.analysis_type.value,
                recommendations_count=len(result.recommendations),
                summary=result.summary,
                confidence=result.confidence_score,
                priority=priority_mapping.get(trigger.priority, 'MEDIUM')
            )
        
        # Store result in database if available
        if self.db_manager:
            await self._store_analysis_result(result)
            
    except Exception as e:
        logger.error("analysis_result_handling_failed",
                    trigger_id=trigger.id,
                    error=str(e))

async def _store_analysis_result(self, result) -> None:
    """Store analysis result in database"""
    # This would be implemented based on the database schema
    # For now, just log that we would store it
    logger.debug("analysis_result_stored",
                analysis_id=result.analysis_id,
                type=result.analysis_type.value)

def _cleanup_completed_analyses(self) -> None:
    """Clean up completed analysis tasks"""
    completed = []
    for trigger_id, task in self.running_analyses.items():
        if task.done():
            completed.append(trigger_id)
    
    for trigger_id in completed:
        del self.running_analyses[trigger_id]

def _update_avg_execution_time(self, execution_time: float) -> None:
    """Update average execution time"""
    if self.successful_executions == 1:
        self.avg_execution_time = execution_time
    else:
        self.avg_execution_time = (
            (self.avg_execution_time * (self.successful_executions - 1) + execution_time) 
            / self.successful_executions
        )

# Manual trigger methods
async def trigger_analysis(self, analysis_type: AnalysisType, 
                         priority: str = "medium") -> str:
    """Manually trigger an analysis"""
    trigger_id = f"manual_{analysis_type.value}_{int(time.time())}"
    
    manual_trigger = AnalysisTrigger(
        id=trigger_id,
        name=f"Manual {analysis_type.value}",
        trigger_type=TriggerType.MANUAL,
        analysis_type=analysis_type,
        enabled=True,
        cooldown_minutes=0,  # No cooldown for manual triggers
        priority=priority
    )
    
    # Add to execution queue immediately
    self.execution_queue.append(trigger_id)
    self.triggers[trigger_id] = manual_trigger
    
    logger.info("manual_analysis_triggered",
               trigger_id=trigger_id,
               analysis_type=analysis_type.value,
               priority=priority)
    
    return trigger_id

async def emergency_trigger(self, reason: str, system_state: Dict[str, Any]) -> str:
    """Trigger emergency analysis"""
    return await self.trigger_analysis(AnalysisType.EMERGENCY_ANALYSIS, "critical")

# Status and management
def get_scheduler_status(self) -> Dict[str, Any]:
    """Get scheduler status"""
    success_rate = 0.0
    if self.total_executions > 0:
        success_rate = (self.successful_executions / self.total_executions) * 100
    
    return {
        'enabled': self.enabled,
        'running': self.running,
        'total_triggers': len(self.triggers),
        'enabled_triggers': len([t for t in self.triggers.values() if t.enabled]),
        'queued_analyses': len(self.execution_queue),
        'running_analyses': len(self.running_analyses),
        'total_executions': self.total_executions,
        'successful_executions': self.successful_executions,
        'failed_executions': self.failed_executions,
        'success_rate': success_rate,
        'avg_execution_time': self.avg_execution_time,
        'max_concurrent': self.max_concurrent_analyses
    }

def get_trigger_status(self) -> List[Dict[str, Any]]:
    """Get status of all triggers"""
    return [
        {
            'id': trigger.id,
            'name': trigger.name,
            'type': trigger.trigger_type.value,
            'analysis_type': trigger.analysis_type.value,
            'enabled': trigger.enabled,
            'priority': trigger.priority,
            'trigger_count': trigger.trigger_count,
            'last_triggered': trigger.last_triggered,
            'cooldown_minutes': trigger.cooldown_minutes,
            'schedule': trigger.schedule,
            'threshold_metric': trigger.threshold_metric,
            'threshold_value': trigger.threshold_value
        }
        for trigger in self.triggers.values()
    ]

def enable_trigger(self, trigger_id: str) -> bool:
    """Enable a trigger"""
    if trigger_id in self.triggers:
        self.triggers[trigger_id].enabled = True
        logger.info("trigger_enabled", trigger_id=trigger_id)
        return True
    return False

def disable_trigger(self, trigger_id: str) -> bool:
    """Disable a trigger"""
    if trigger_id in self.triggers:
        self.triggers[trigger_id].enabled = False
        logger.info("trigger_disabled", trigger_id=trigger_id)
        return True
    return False

def update_trigger_schedule(self, trigger_id: str, new_schedule: str) -> bool:
    """Update trigger schedule"""
    if trigger_id in self.triggers:
        try:
            # Validate cron expression
            croniter(new_schedule)
            self.triggers[trigger_id].schedule = new_schedule
            logger.info("trigger_schedule_updated",
                       trigger_id=trigger_id,
                       new_schedule=new_schedule)
            return True
        except Exception as e:
            logger.error("invalid_cron_expression",
                       trigger_id=trigger_id,
                       schedule=new_schedule,
                       error=str(e))
    return False
```