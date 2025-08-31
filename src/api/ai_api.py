"""
SmartArb Engine AI REST API
Web API for interacting with the AI analysis system
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
import sys

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Query
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn
import structlog

logger = structlog.get_logger(__name__)
from src.utils.config import ConfigManager


# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.ai.claude_integration import ClaudeAnalysisEngine, ClaudeRecommendation
from src.ai.analysis_scheduler import AIAnalysisScheduler
from src.ai.code_updater import CodeUpdateManager
from src.ai.dashboard import AIDashboard
from src.utils.config import ConfigManager
from src.utils.notifications import NotificationManager
from src.db.connection import DatabaseManager, initialize_database

logger = structlog.get_logger(__name__)

# Pydantic Models for API requests/responses
class AnalysisRequest(BaseModel):
    focus_area: Optional[str] = Field(None, description="Specific area to focus analysis on")
    custom_prompt: Optional[str] = Field(None, description="Custom analysis prompt")
    priority: str = Field("normal", description="Analysis priority")


class RecommendationResponse(BaseModel):
    recommendation_id: str
    title: str
    category: str
    priority: str
    description: str
    has_code_changes: bool
    has_config_changes: bool
    expected_impact: Optional[str]
    risks: List[str]


class SystemStatusResponse(BaseModel):
    ai_enabled: bool
    scheduler_running: bool
    claude_configured: bool
    queue_size: int
    last_analysis: Optional[datetime]
    total_analyses: int
    success_rate: float


class CodeUpdateRequest(BaseModel):
    recommendation_ids: List[str] = Field(description="List of recommendation IDs to apply")
    auto_approve_safe: bool = Field(False, description="Auto-approve safe changes")


class ScheduleUpdateRequest(BaseModel):
    cron_expression: str = Field(description="Cron expression for scheduling")


# Global AI system manager
class AIAPIManager:
    def __init__(self):
        self.config = None
        self.claude_engine = None
        self.scheduler = None
        self.code_updater = None
        self.dashboard = None
        self.notification_manager = None
        self.db_manager = None
        self.initialized = False
    
    async def initialize(self):
        """Initialize AI system components"""
        if self.initialized:
            return
        
        try:
            self.config = ConfigManager()
            self.db_manager = await initialize_database(self.config.to_dict())
            
            self.notification_manager = NotificationManager(
                self.config.get('monitoring', {})
            )
            
            self.claude_engine = ClaudeAnalysisEngine(self.config, self.db_manager)
            self.code_updater = CodeUpdateManager(self.notification_manager)
            self.scheduler = AIAnalysisScheduler(
                self.config, self.db_manager, self.notification_manager
            )
            self.dashboard = AIDashboard(
                self.claude_engine, self.scheduler, 
                self.code_updater, self.notification_manager
            )
            
            # Start scheduler
            await self.scheduler.start()
            
            self.initialized = True
            logger.info("ai_api_manager_initialized")
            
        except Exception as e:
            logger.error("ai_api_initialization_failed", error=str(e))
            raise


ai_manager = AIAPIManager()

# FastAPI app
app = FastAPI(
    title="SmartArb Engine AI API",
    description="REST API for SmartArb Engine AI Analysis System",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def get_ai_manager():
    """Dependency to get initialized AI manager"""
    if not ai_manager.initialized:
        await ai_manager.initialize()
    return ai_manager


@app.on_event("startup")
async def startup_event():
    """Initialize AI system on startup"""
    await ai_manager.initialize()


@app.on_event("shutdown") 
async def shutdown_event():
    """Cleanup on shutdown"""
    if ai_manager.scheduler:
        await ai_manager.scheduler.stop()
    if ai_manager.db_manager:
        await ai_manager.db_manager.close()


# Health and Status Endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.get("/api/v1/status", response_model=SystemStatusResponse)
async def get_system_status(manager: AIAPIManager = Depends(get_ai_manager)):
    """Get AI system status"""
    try:
        scheduler_status = await manager.scheduler.get_analysis_status()
        
        return SystemStatusResponse(
            ai_enabled=manager.config.get('ai.enabled', False),
            scheduler_running=scheduler_status['is_running'],
            claude_configured=bool(manager.claude_engine.claude_api_key),
            queue_size=scheduler_status.get('queue_size', 0),
            last_analysis=datetime.fromisoformat(scheduler_status['last_analysis']) if scheduler_status.get('last_analysis') else None,
            total_analyses=scheduler_status['total_analyses'],
            success_rate=scheduler_status['success_rate']
        )
    except Exception as e:
        logger.error("status_retrieval_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# Analysis Endpoints
@app.post("/api/v1/analysis/run")
async def run_analysis(
    request: AnalysisRequest,
    background_tasks: BackgroundTasks,
    manager: AIAPIManager = Depends(get_ai_manager)
):
    """Trigger AI analysis"""
    try:
        # Queue analysis
        await manager.scheduler.queue_analysis(
            analysis_type='api_request',
            priority=request.priority,
            custom_focus=request.focus_area
        )
        
        return {
            "status": "queued",
            "message": "Analysis has been queued for execution",
            "queue_position": manager.scheduler.analysis_queue.qsize()
        }
    except Exception as e:
        logger.error("analysis_request_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/analysis/manual")
async def manual_analysis(
    prompt: str = Query(..., description="Analysis prompt"),
    manager: AIAPIManager = Depends(get_ai_manager)
):
    """Get manual analysis from Claude"""
    try:
        result = await manager.claude_engine.get_manual_analysis(prompt)
        
        return {
            "prompt": prompt,
            "analysis": result,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error("manual_analysis_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/analysis/history")
async def get_analysis_history(
    limit: int = Query(10, ge=1, le=100),
    manager: AIAPIManager = Depends(get_ai_manager)
):
    """Get analysis history"""
    try:
        history = manager.claude_engine.get_analysis_history()
        return {
            "analyses": history[-limit:],
            "total_count": len(history)
        }
    except Exception as e:
        logger.error("analysis_history_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# Recommendations Endpoints
@app.get("/api/v1/recommendations", response_model=List[RecommendationResponse])
async def get_recommendations(
    priority: Optional[str] = Query(None, description="Filter by priority"),
    category: Optional[str] = Query(None, description="Filter by category"),
    limit: int = Query(20, ge=1, le=100),
    manager: AIAPIManager = Depends(get_ai_manager)
):
    """Get AI recommendations"""
    try:
        recommendations = manager.claude_engine.get_latest_recommendations()
        
        if not recommendations:
            return []
        
        # Apply filters
        if priority:
            recommendations = [r for r in recommendations if r.priority == priority]
        
        if category:
            recommendations = [r for r in recommendations if r.category == category]
        
        # Limit results
        recommendations = recommendations[:limit]
        
        # Convert to response format
        return [
            RecommendationResponse(
                recommendation_id=rec.opportunity_id if hasattr(rec, 'opportunity_id') else f"rec_{i}",
                title=rec.title,
                category=rec.category,
                priority=rec.priority,
                description=rec.description,
                has_code_changes=bool(rec.code_changes),
                has_config_changes=bool(rec.config_changes),
                expected_impact=rec.expected_impact,
                risks=rec.risks or []
            )
            for i, rec in enumerate(recommendations)
        ]
    except Exception as e:
        logger.error("recommendations_retrieval_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/recommendations/{recommendation_id}/approve")
async def approve_recommendation(
    recommendation_id: str,
    manager: AIAPIManager = Depends(get_ai_manager)
):
    """Approve a recommendation"""
    try:
        result = await manager.dashboard.approve_recommendation(recommendation_id)
        return result
    except Exception as e:
        logger.error("recommendation_approval_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/recommendations/{recommendation_id}/reject")
async def reject_recommendation(
    recommendation_id: str,
    reason: str = Query(..., description="Rejection reason"),
    manager: AIAPIManager = Depends(get_ai_manager)
):
    """Reject a recommendation"""
    try:
        result = await manager.dashboard.reject_recommendation(recommendation_id, reason)
        return result
    except Exception as e:
        logger.error("recommendation_rejection_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# Code Updates Endpoints
@app.post("/api/v1/code/apply")
async def apply_code_updates(
    request: CodeUpdateRequest,
    manager: AIAPIManager = Depends(get_ai_manager)
):
    """Apply code updates from recommendations"""
    try:
        recommendations = manager.claude_engine.get_latest_recommendations()
        
        if not recommendations:
            raise HTTPException(status_code=404, detail="No recommendations available")
        
        # Filter to requested recommendations (for now, apply all)
        results = await manager.code_updater.process_recommendations(recommendations)
        
        return {
            "status": "completed",
            "results": results,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error("code_update_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/code/updates")
async def get_code_updates(
    limit: int = Query(20, ge=1, le=100),
    manager: AIAPIManager = Depends(get_ai_manager)
):
    """Get code update history"""
    try:
        updates = manager.code_updater.get_update_history()
        rollbacks = manager.code_updater.get_available_rollbacks()
        
        return {
            "updates": updates[-limit:],
            "rollback_points": rollbacks[:limit],
            "total_updates": len(updates),
            "total_rollbacks": len(rollbacks)
        }
    except Exception as e:
        logger.error("code_updates_retrieval_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/code/rollback/{update_id}")
async def rollback_update(
    update_id: str,
    manager: AIAPIManager = Depends(get_ai_manager)
):
    """Rollback a specific code update"""
    try:
        result = await manager.dashboard.rollback_update(update_id)
        return result
    except Exception as e:
        logger.error("rollback_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# Scheduler Endpoints
@app.get("/api/v1/scheduler/status")
async def get_scheduler_status(manager: AIAPIManager = Depends(get_ai_manager)):
    """Get scheduler status"""
    try:
        status = await manager.scheduler.get_analysis_status()
        return status
    except Exception as e:
        logger.error("scheduler_status_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/scheduler/start")
async def start_scheduler(manager: AIAPIManager = Depends(get_ai_manager)):
    """Start the analysis scheduler"""
    try:
        await manager.scheduler.start()
        return {"status": "started", "message": "Analysis scheduler started"}
    except Exception as e:
        logger.error("scheduler_start_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/scheduler/stop")
async def stop_scheduler(manager: AIAPIManager = Depends(get_ai_manager)):
    """Stop the analysis scheduler"""
    try:
        await manager.scheduler.stop()
        return {"status": "stopped", "message": "Analysis scheduler stopped"}
    except Exception as e:
        logger.error("scheduler_stop_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/scheduler/schedule")
async def update_schedule(
    request: ScheduleUpdateRequest,
    manager: AIAPIManager = Depends(get_ai_manager)
):
    """Update analysis schedule"""
    try:
        await manager.scheduler.update_schedule(request.cron_expression)
        return {
            "status": "updated",
            "schedule": request.cron_expression,
            "message": "Analysis schedule updated"
        }
    except Exception as e:
        logger.error("schedule_update_failed", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))


# Dashboard Endpoints
@app.get("/api/v1/dashboard")
async def get_dashboard_data(manager: AIAPIManager = Depends(get_ai_manager)):
    """Get complete dashboard data"""
    try:
        await manager.dashboard.update_dashboard_data()
        dashboard_data = manager.dashboard.get_dashboard_data()
        return dashboard_data
    except Exception as e:
        logger.error("dashboard_data_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/dashboard/realtime")
async def get_realtime_stats(manager: AIAPIManager = Depends(get_ai_manager)):
    """Get real-time dashboard statistics"""
    try:
        stats = manager.dashboard.get_real_time_stats()
        return stats
    except Exception as e:
        logger.error("realtime_stats_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/dashboard/export")
async def export_dashboard_data(
    format: str = Query("json", description="Export format: json or csv"),
    manager: AIAPIManager = Depends(get_ai_manager)
):
    """Export dashboard data"""
    try:
        await manager.dashboard.update_dashboard_data()
        dashboard_data = manager.dashboard.get_dashboard_data()
        
        if format == "json":
            import json
            import tempfile
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(dashboard_data, f, indent=2, default=str)
                temp_path = f.name
            
            return FileResponse(
                temp_path,
                filename=f"smartarb_dashboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                media_type="application/json"
            )
        
        else:
            raise HTTPException(status_code=400, detail="Unsupported export format")
    
    except Exception as e:
        logger.error("dashboard_export_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# WebSocket endpoint for real-time updates (future enhancement)
@app.websocket("/ws/realtime")
async def websocket_endpoint(websocket):
    """WebSocket endpoint for real-time updates"""
    await websocket.accept()
    try:
        while True:
            # Send real-time updates every 10 seconds
            await asyncio.sleep(10)
            if ai_manager.initialized:
                stats = ai_manager.dashboard.get_real_time_stats()
                await websocket.send_json(stats)
    except Exception as e:
        logger.error("websocket_error", error=str(e))
    finally:
        await websocket.close()


# Utility function to run the API server
def run_api_server(host: str = "0.0.0.0", port: int = 8000, reload: bool = False):
    """Run the AI API server"""
    uvicorn.run(
        "src.api.ai_api:app",
        host=host,
        port=port,
        reload=reload,
        log_config=None  # Use our logging configuration
    )


if __name__ == "__main__":
    run_api_server(reload=True)