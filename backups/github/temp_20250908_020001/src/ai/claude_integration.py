#!/usr/bin/env python3
“””
Claude AI Integration for SmartArb Engine
Advanced AI analysis and optimization using Anthropic’s Claude API
“””

import asyncio
import json
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timedelta
import structlog
import httpx
from anthropic import AsyncAnthropic

logger = structlog.get_logger(**name**)

class AnalysisType(Enum):
“”“Types of AI analysis”””
PERFORMANCE_REVIEW = “performance_review”
STRATEGY_OPTIMIZATION = “strategy_optimization”
RISK_ASSESSMENT = “risk_assessment”
MARKET_ANALYSIS = “market_analysis”
CODE_REVIEW = “code_review”
PORTFOLIO_ANALYSIS = “portfolio_analysis”
EMERGENCY_ANALYSIS = “emergency_analysis”

class RecommendationType(Enum):
“”“Types of AI recommendations”””
PARAMETER_ADJUSTMENT = “parameter_adjustment”
STRATEGY_CHANGE = “strategy_change”
RISK_MODIFICATION = “risk_modification”
CODE_UPDATE = “code_update”
PORTFOLIO_REBALANCE = “portfolio_rebalance”
EMERGENCY_ACTION = “emergency_action”
OPTIMIZATION = “optimization”

@dataclass
class AIRecommendation:
“”“AI recommendation structure”””
id: str
type: RecommendationType
title: str
description: str
confidence: float  # 0-1
impact: str  # “low”, “medium”, “high”, “critical”
urgency: str  # “low”, “medium”, “high”, “urgent”
implementation: Dict[str, Any]
reasoning: str
risks: List[str]
benefits: List[str]
estimated_improvement: Optional[float] = None
created_time: float = 0

```
def __post_init__(self):
    if self.created_time == 0:
        self.created_time = time.time()

def to_dict(self) -> Dict[str, Any]:
    return asdict(self)
```

@dataclass
class AnalysisRequest:
“”“AI analysis request structure”””
id: str
type: AnalysisType
focus: str
data: Dict[str, Any]
context: Dict[str, Any]
requested_time: float
priority: str = “normal”  # “low”, “normal”, “high”, “urgent”

```
def to_dict(self) -> Dict[str, Any]:
    return asdict(self)
```

@dataclass
class AnalysisResult:
“”“AI analysis result structure”””
request_id: str
analysis_type: AnalysisType
summary: str
key_findings: List[str]
recommendations: List[AIRecommendation]
metrics: Dict[str, Any]
confidence_score: float
processing_time: float
completed_time: float

```
def to_dict(self) -> Dict[str, Any]:
    result = asdict(self)
    result['analysis_type'] = self.analysis_type.value
    result['recommendations'] = [rec.to_dict() for rec in self.recommendations]
    return result
```

class ClaudeAnalysisEngine:
“”“Main Claude AI analysis engine”””

```
def __init__(self, config: Dict[str, Any], db_manager=None):
    self.config = config
    self.ai_config = config.get('ai', {})
    self.db_manager = db_manager
    
    # Initialize Claude client
    api_key = self.ai_config.get('claude_api_key', '')
    if not api_key:
        raise ValueError("Claude API key not provided in configuration")
    
    self.claude_client = AsyncAnthropic(api_key=api_key)
    
    # Analysis settings
    self.model = self.ai_config.get('model', 'claude-3-sonnet-20240229')
    self.max_tokens = self.ai_config.get('max_tokens', 4000)
    self.temperature = self.ai_config.get('temperature', 0.3)
    
    # Rate limiting
    self.rate_limit = self.ai_config.get('rate_limit_per_minute', 50)
    self.request_timestamps = []
    
    # Analysis tracking
    self.active_analyses = {}
    self.analysis_history = []
    self.max_history_size = 1000
    
    # Performance metrics
    self.total_analyses = 0
    self.successful_analyses = 0
    self.failed_analyses = 0
    
    self.logger = structlog.get_logger("ai.claude")

async def test_connection(self) -> Dict[str, Any]:
    """Test Claude API connection"""
    
    try:
        # Simple test message
        response = await self.claude_client.messages.create(
            model=self.model,
            max_tokens=100,
            temperature=0,
            messages=[{
                "role": "user",
                "content": "Please respond with 'Connection successful' to test the API."
            }]
        )
        
        if response.content and len(response.content) > 0:
            content = response.content[0].text
            if "Connection successful" in content:
                self.logger.info("claude_connection_test_successful")
                return {
                    'success': True,
                    'model': self.model,
                    'response': content
                }
        
        return {
            'success': False,
            'error': 'Unexpected response format'
        }
        
    except Exception as e:
        self.logger.error("claude_connection_test_failed", error=str(e))
        return {
            'success': False,
            'error': str(e)
        }

async def analyze_performance(self, performance_data: Dict[str, Any], 
                             focus: str = "overall") -> AnalysisResult:
    """Analyze trading performance using Claude AI"""
    
    request = AnalysisRequest(
        id=f"perf_{int(time.time())}",
        type=AnalysisType.PERFORMANCE_REVIEW,
        focus=focus,
        data=performance_data,
        context=self._get_system_context(),
        requested_time=time.time(),
        priority="normal"
    )
    
    return await self._process_analysis_request(request)

async def optimize_strategy(self, strategy_data: Dict[str, Any],
                           performance_metrics: Dict[str, Any]) -> AnalysisResult:
    """Get strategy optimization recommendations"""
    
    request = AnalysisRequest(
        id=f"opt_{int(time.time())}",
        type=AnalysisType.STRATEGY_OPTIMIZATION,
        focus="parameter_optimization",
        data={
            'strategy_config': strategy_data,
            'performance_metrics': performance_metrics,
            'market_conditions': self._get_market_context()
        },
        context=self._get_system_context(),
        requested_time=time.time(),
        priority="normal"
    )
    
    return await self._process_analysis_request(request)

async def assess_risk(self, portfolio_data: Dict[str, Any],
                     market_data: Dict[str, Any]) -> AnalysisResult:
    """Perform AI-powered risk assessment"""
    
    request = AnalysisRequest(
        id=f"risk_{int(time.time())}",
        type=AnalysisType.RISK_ASSESSMENT,
        focus="portfolio_risk",
        data={
            'portfolio': portfolio_data,
            'market_data': market_data,
            'risk_metrics': self._get_risk_metrics()
        },
        context=self._get_system_context(),
        requested_time=time.time(),
        priority="high"
    )
    
    return await self._process_analysis_request(request)

async def emergency_analysis(self, incident_data: Dict[str, Any]) -> AnalysisResult:
    """Perform emergency analysis for critical situations"""
    
    request = AnalysisRequest(
        id=f"emerg_{int(time.time())}",
        type=AnalysisType.EMERGENCY_ANALYSIS,
        focus="incident_response",
        data=incident_data,
        context=self._get_system_context(),
        requested_time=time.time(),
        priority="urgent"
    )
    
    return await self._process_analysis_request(request)

async def _process_analysis_request(self, request: AnalysisRequest) -> AnalysisResult:
    """Process analysis request with Claude AI"""
    
    start_time = time.time()
    self.total_analyses += 1
    
    try:
        # Check rate limits
        await self._check_rate_limits()
        
        # Store active analysis
        self.active_analyses[request.id] = request
        
        # Generate prompt based on analysis type
        prompt = self._generate_analysis_prompt(request)
        
        # Call Claude API
        response = await self._call_claude_api(prompt)
        
        # Parse response
        analysis_result = self._parse_claude_response(
            request, response, time.time() - start_time
        )
        
        # Store result
        self._store_analysis_result(analysis_result)
        
        self.successful_analyses += 1
        
        self.logger.info("analysis_completed",
                       request_id=request.id,
                       type=request.type.value,
                       processing_time=analysis_result.processing_time,
                       recommendations_count=len(analysis_result.recommendations))
        
        return analysis_result
        
    except Exception as e:
        self.failed_analyses += 1
        self.logger.error("analysis_failed",
                        request_id=request.id,
                        error=str(e))
        
        # Return error result
        return AnalysisResult(
            request_id=request.id,
            analysis_type=request.type,
            summary=f"Analysis failed: {str(e)}",
            key_findings=[],
            recommendations=[],
            metrics={},
            confidence_score=0.0,
            processing_time=time.time() - start_time,
            completed_time=time.time()
        )
    
    finally:
        # Remove from active analyses
        self.active_analyses.pop(request.id, None)

def _generate_analysis_prompt(self, request: AnalysisRequest) -> str:
    """Generate analysis prompt for Claude"""
    
    base_context = f"""
```

You are an AI assistant specialized in cryptocurrency trading analysis and optimization for the SmartArb Engine arbitrage trading system.

Current system context:

- Trading engine: SmartArb Engine v1.0
- Supported exchanges: Kraken, Bybit, MEXC
- Strategy types: Spatial arbitrage (active), triangular arbitrage (planned), statistical arbitrage (planned)
- Risk management: Active with circuit breakers and position limits
- Portfolio management: Multi-exchange with automated rebalancing

Analysis Type: {request.type.value}
Focus Area: {request.focus}
Priority: {request.priority}

System Configuration:
{json.dumps(request.context, indent=2)}

Data for Analysis:
{json.dumps(request.data, indent=2)}
“””

```
    if request.type == AnalysisType.PERFORMANCE_REVIEW:
        specific_instructions = """
```

Please analyze the trading performance data and provide:

1. PERFORMANCE SUMMARY:
- Overall performance assessment
- Key performance indicators analysis
- Comparison to benchmarks
1. KEY FINDINGS:
- Most successful strategies/patterns
- Areas of concern or underperformance
- Market condition impacts
1. ACTIONABLE RECOMMENDATIONS:
- Specific parameter adjustments
- Strategy optimizations
- Risk management improvements

Format your response as JSON with the following structure:
{
“summary”: “Brief overall assessment”,
“key_findings”: [“finding1”, “finding2”, …],
“recommendations”: [
{
“type”: “parameter_adjustment|strategy_change|risk_modification|optimization”,
“title”: “Short recommendation title”,
“description”: “Detailed description”,
“confidence”: 0.0-1.0,
“impact”: “low|medium|high|critical”,
“urgency”: “low|medium|high|urgent”,
“implementation”: {“parameter”: “value”, …},
“reasoning”: “Why this recommendation”,
“risks”: [“risk1”, “risk2”],
“benefits”: [“benefit1”, “benefit2”],
“estimated_improvement”: 0.0-100.0
}
],
“metrics”: {
“confidence_score”: 0.0-1.0,
“analysis_depth”: “surface|moderate|deep”,
“data_quality”: “poor|fair|good|excellent”
}
}
“””

```
    elif request.type == AnalysisType.STRATEGY_OPTIMIZATION:
        specific_instructions = """
```

Please analyze the current strategy configuration and performance metrics to provide optimization recommendations:

1. STRATEGY ANALYSIS:
- Current parameter effectiveness
- Performance vs expected outcomes
- Market adaptation analysis
1. OPTIMIZATION OPPORTUNITIES:
- Parameter tuning suggestions
- Strategy modifications
- New strategy considerations
1. IMPLEMENTATION PLAN:
- Priority order of changes
- Risk assessment of modifications
- Expected performance improvements

Provide response in the same JSON format as above, focusing on strategy optimization recommendations.
“””

```
    elif request.type == AnalysisType.RISK_ASSESSMENT:
        specific_instructions = """
```

Please perform a comprehensive risk assessment:

1. RISK IDENTIFICATION:
- Current risk exposures
- Potential risk scenarios
- Market risk factors
1. RISK QUANTIFICATION:
- Risk level assessment
- Impact probability
- Mitigation effectiveness
1. RISK MANAGEMENT RECOMMENDATIONS:
- Risk reduction strategies
- Monitoring improvements
- Emergency procedures

Focus on actionable risk management recommendations in the JSON response format.
“””

```
    elif request.type == AnalysisType.EMERGENCY_ANALYSIS:
        specific_instructions = """
```

This is an EMERGENCY ANALYSIS. Please provide immediate, actionable recommendations:

1. IMMEDIATE SITUATION ASSESSMENT:
- Severity evaluation
- Root cause analysis
- Immediate risks
1. URGENT ACTIONS NEEDED:
- Immediate steps to take
- Risk mitigation actions
- System protection measures
1. RECOVERY RECOMMENDATIONS:
- Recovery strategies
- Prevention measures
- System improvements

Prioritize urgent, high-confidence recommendations in the JSON response.
“””

```
    else:
        specific_instructions = """
```

Please analyze the provided data and give appropriate recommendations based on the analysis type.
Use the JSON format specified above.
“””

```
    return base_context + "\n" + specific_instructions

async def _call_claude_api(self, prompt: str) -> Dict[str, Any]:
    """Call Claude API with the analysis prompt"""
    
    try:
        response = await self.claude_client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )
        
        if response.content and len(response.content) > 0:
            content = response.content[0].text
            
            # Track request timestamp for rate limiting
            self.request_timestamps.append(time.time())
            
            return {'content': content, 'usage': response.usage}
        
        raise Exception("Empty response from Claude API")
        
    except Exception as e:
        self.logger.error("claude_api_call_failed", error=str(e))
        raise

def _parse_claude_response(self, request: AnalysisRequest, 
                          response: Dict[str, Any], processing_time: float) -> AnalysisResult:
    """Parse Claude response into AnalysisResult"""
    
    try:
        content = response['content']
        
        # Try to extract JSON from the response
        json_start = content.find('{')
        json_end = content.rfind('}') + 1
        
        if json_start >= 0 and json_end > json_start:
            json_content = content[json_start:json_end]
            parsed_data = json.loads(json_content)
        else:
            # Fallback if no JSON found
            parsed_data = {
                'summary': content[:500] + "..." if len(content) > 500 else content,
                'key_findings': [],
                'recommendations': [],
                'metrics': {'confidence_score': 0.5}
            }
        
        # Convert recommendations to AIRecommendation objects
        recommendations = []
        for rec_data in parsed_data.get('recommendations', []):
            try:
                recommendation = AIRecommendation(
                    id=f"{request.id}_rec_{len(recommendations)}",
                    type=RecommendationType(rec_data.get('type', 'optimization')),
                    title=rec_data.get('title', 'AI Recommendation'),
                    description=rec_data.get('description', ''),
                    confidence=float(rec_data.get('confidence', 0.5)),
                    impact=rec_data.get('impact', 'medium'),
                    urgency=rec_data.get('urgency', 'normal'),
                    implementation=rec_data.get('implementation', {}),
                    reasoning=rec_data.get('reasoning', ''),
                    risks=rec_data.get('risks', []),
                    benefits=rec_data.get('benefits', []),
                    estimated_improvement=rec_data.get('estimated_improvement')
                )
                recommendations.append(recommendation)
            except Exception as e:
                self.logger.warning("recommendation_parsing_failed", error=str(e))
        
        return AnalysisResult(
            request_id=request.id,
            analysis_type=request.type,
            summary=parsed_data.get('summary', 'Analysis completed'),
            key_findings=parsed_data.get('key_findings', []),
            recommendations=recommendations,
            metrics=parsed_data.get('metrics', {}),
            confidence_score=float(parsed_data.get('metrics', {}).get('confidence_score', 0.5)),
            processing_time=processing_time,
            completed_time=time.time()
        )
        
    except Exception as e:
        self.logger.error("response_parsing_failed", error=str(e))
        
        # Return minimal result on parsing failure
        return AnalysisResult(
            request_id=request.id,
            analysis_type=request.type,
            summary=f"Analysis completed but response parsing failed: {str(e)}",
            key_findings=[],
            recommendations=[],
            metrics={},
            confidence_score=0.0,
            processing_time=processing_time,
            completed_time=time.time()
        )

def _get_system_context(self) -> Dict[str, Any]:
    """Get current system context for analysis"""
    
    return {
        'engine_version': '1.0.0',
        'active_exchanges': list(self.config.get('exchanges', {}).keys()),
        'enabled_strategies': [
            name for name, config in self.config.get('strategies', {}).items()
            if config.get('enabled', False)
        ],
        'risk_limits': self.config.get('risk_management', {}),
        'ai_config': {
            'model': self.model,
            'analysis_enabled': True,
            'auto_optimization': self.ai_config.get('auto_optimization', False)
        }
    }

def _get_market_context(self) -> Dict[str, Any]:
    """Get current market context"""
    
    # This would typically fetch real market data
    # For now, return placeholder
    return {
        'market_conditions': 'normal',
        'volatility_level': 'medium',
        'liquidity_conditions': 'good',
        'trend_analysis': 'mixed'
    }

def _get_risk_metrics(self) -> Dict[str, Any]:
    """Get current risk metrics"""
    
    # This would typically get real risk data from risk manager
    return {
        'current_exposure': 0.0,
        'daily_pnl': 0.0,
        'max_drawdown': 0.0,
        'risk_score': 0.5
    }

async def _check_rate_limits(self):
    """Check and enforce rate limits"""
    
    current_time = time.time()
    
    # Remove timestamps older than 1 minute
    self.request_timestamps = [
        ts for ts in self.request_timestamps 
        if current_time - ts < 60
    ]
    
    # Check if we're at the rate limit
    if len(self.request_timestamps) >= self.rate_limit:
        # Calculate wait time
        oldest_request = min(self.request_timestamps)
        wait_time = 60 - (current_time - oldest_request)
        
        if wait_time > 0:
            self.logger.info("rate_limit_reached", wait_time=wait_time)
            await asyncio.sleep(wait_time)

def _store_analysis_result(self, result: AnalysisResult):
    """Store analysis result in history"""
    
    self.analysis_history.append(result)
    
    # Manage history size
    if len(self.analysis_history) > self.max_history_size:
        self.analysis_history = self.analysis_history[-self.max_history_size:]
    
    # Store in database if available
    if self.db_manager:
        try:
            # This would store in database
            pass
        except Exception as e:
            self.logger.warning("database_storage_failed", error=str(e))

def get_analysis_history(self, limit: int = 50) -> List[Dict[str, Any]]:
    """Get recent analysis history"""
    
    recent_analyses = self.analysis_history[-limit:]
    return [analysis.to_dict() for analysis in recent_analyses]

def get_recommendations_by_type(self, rec_type: RecommendationType) -> List[AIRecommendation]:
    """Get recommendations filtered by type"""
    
    recommendations = []
    for analysis in self.analysis_history:
        for rec in analysis.recommendations:
            if rec.type == rec_type:
                recommendations.append(rec)
    
    return recommendations

def get_performance_metrics(self) -> Dict[str, Any]:
    """Get AI engine performance metrics"""
    
    success_rate = (self.successful_analyses / max(self.total_analyses, 1)) * 100
    
    # Calculate average processing time
    processing_times = [a.processing_time for a in self.analysis_history]
    avg_processing_time = sum(processing_times) / max(len(processing_times), 1)
    
    return {
        'total_analyses': self.total_analyses,
        'successful_analyses': self.successful_analyses,
        'failed_analyses': self.failed_analyses,
        'success_rate_percent': success_rate,
        'average_processing_time_seconds': avg_processing_time,
        'active_analyses': len(self.active_analyses),
        'history_size': len(self.analysis_history),
        'rate_limit_per_minute': self.rate_limit,
        'current_requests_in_window': len(self.request_timestamps)
    }
```