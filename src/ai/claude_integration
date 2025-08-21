"""
Claude AI Integration for SmartArb Engine
Intelligent analysis, optimization, and code updates
"""

import asyncio
import aiohttp
import json
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from decimal import Decimal
import structlog
from pathlib import Path

from ..utils.config import ConfigManager
from ..db.connection import DatabaseManager
from ..core.risk_manager import RiskManager
from ..core.portfolio_manager import PortfolioManager

logger = structlog.get_logger(__name__)


@dataclass
class PerformanceReport:
    """Structured performance report for Claude analysis"""
    period: str
    total_trades: int
    successful_trades: int
    total_profit: float
    total_fees: float
    success_rate: float
    profit_per_trade: float
    max_drawdown: float
    sharpe_ratio: float
    exchange_performance: Dict[str, Dict[str, float]]
    strategy_performance: Dict[str, Dict[str, float]]
    risk_metrics: Dict[str, float]
    market_conditions: Dict[str, Any]
    issues_detected: List[str]
    opportunities_missed: int
    execution_latency_avg: float


@dataclass
class ClaudeRecommendation:
    """Claude's recommendation structure"""
    category: str  # 'risk', 'strategy', 'technical', 'market'
    priority: str  # 'low', 'medium', 'high', 'critical'
    title: str
    description: str
    code_changes: Optional[List[Dict[str, str]]] = None
    config_changes: Optional[Dict[str, Any]] = None
    implementation_plan: Optional[List[str]] = None
    expected_impact: Optional[str] = None
    risks: Optional[List[str]] = None


class ClaudeAnalysisEngine:
    """
    Claude AI Integration for SmartArb Engine
    
    Features:
    - Automated performance analysis
    - Intelligent optimization suggestions
    - Code update recommendations
    - Market analysis and insights
    - Risk assessment and alerts
    """
    
    def __init__(self, config: ConfigManager, db_manager: DatabaseManager):
        self.config = config
        self.db_manager = db_manager
        
        # Claude API configuration
        self.claude_api_key = config.get('ai.claude_api_key')
        self.claude_api_url = config.get('ai.claude_api_url', 'https://api.anthropic.com/v1/messages')
        self.model = config.get('ai.model', 'claude-3-sonnet-20240229')
        
        # Analysis settings
        self.analysis_frequency = config.get('ai.analysis_frequency', 'daily')  # hourly, daily, weekly
        self.auto_apply_safe_changes = config.get('ai.auto_apply_safe_changes', False)
        self.min_confidence_threshold = config.get('ai.min_confidence_threshold', 0.8)
        
        # Report storage
        self.reports_dir = Path('data/ai_reports')
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        
        # Performance tracking
        self.last_analysis_time = None
        self.analysis_history: List[Dict[str, Any]] = []
        
        logger.info("claude_integration_initialized",
                   model=self.model,
                   frequency=self.analysis_frequency)
    
    async def run_automated_analysis(self) -> Optional[List[ClaudeRecommendation]]:
        """
        Run automated performance analysis and get recommendations
        """
        try:
            logger.info("starting_automated_analysis")
            
            # Generate comprehensive performance report
            report = await self._generate_performance_report()
            
            # Analyze market conditions
            market_analysis = await self._analyze_market_conditions()
            
            # Get Claude's analysis and recommendations
            recommendations = await self._get_claude_recommendations(report, market_analysis)
            
            # Process and validate recommendations
            validated_recommendations = await self._validate_recommendations(recommendations)
            
            # Apply safe changes automatically (if enabled)
            if self.auto_apply_safe_changes:
                await self._apply_safe_recommendations(validated_recommendations)
            
            # Store analysis results
            await self._store_analysis_results(report, validated_recommendations)
            
            # Update tracking
            self.last_analysis_time = datetime.now()
            
            logger.info("automated_analysis_completed",
                       recommendations_count=len(validated_recommendations))
            
            return validated_recommendations
            
        except Exception as e:
            logger.error("automated_analysis_failed", error=str(e))
            return None
    
    async def _generate_performance_report(self) -> PerformanceReport:
        """Generate comprehensive performance report"""
        
        # Time period for analysis
        end_time = datetime.now()
        start_time = end_time - timedelta(days=7)  # Last 7 days
        
        async with self.db_manager.get_session() as session:
            # Get opportunities data
            opportunities = session.query(Opportunity).filter(
                Opportunity.detected_at >= start_time,
                Opportunity.detected_at <= end_time
            ).all()
            
            # Calculate basic metrics
            total_trades = len([opp for opp in opportunities if opp.status == 'completed'])
            successful_trades = len([opp for opp in opportunities 
                                   if opp.status == 'completed' and opp.actual_profit > 0])
            
            total_profit = sum(float(opp.actual_profit or 0) for opp in opportunities 
                             if opp.status == 'completed')
            total_fees = sum(float(opp.actual_fees or 0) for opp in opportunities 
                           if opp.status == 'completed')
            
            success_rate = (successful_trades / max(total_trades, 1)) * 100
            profit_per_trade = total_profit / max(total_trades, 1)
            
            # Exchange performance breakdown
            exchange_performance = {}
            for exchange in ['kraken', 'bybit', 'mexc']:
                exchange_opps = [opp for opp in opportunities 
                               if opp.buy_exchange.name == exchange or opp.sell_exchange.name == exchange]
                exchange_profit = sum(float(opp.actual_profit or 0) for opp in exchange_opps 
                                    if opp.status == 'completed')
                exchange_performance[exchange] = {
                    'trades': len(exchange_opps),
                    'profit': exchange_profit,
                    'success_rate': len([opp for opp in exchange_opps if opp.actual_profit > 0]) / max(len(exchange_opps), 1) * 100
                }
            
            # Strategy performance
            strategy_performance = {}
            strategies = set(opp.strategy_name for opp in opportunities)
            for strategy in strategies:
                strategy_opps = [opp for opp in opportunities if opp.strategy_name == strategy]
                strategy_profit = sum(float(opp.actual_profit or 0) for opp in strategy_opps 
                                    if opp.status == 'completed')
                strategy_performance[strategy] = {
                    'trades': len(strategy_opps),
                    'profit': strategy_profit,
                    'avg_profit_pct': sum(float(opp.expected_profit_percentage or 0) for opp in strategy_opps) / max(len(strategy_opps), 1)
                }
            
            # Risk metrics
            profits = [float(opp.actual_profit or 0) for opp in opportunities 
                      if opp.status == 'completed' and opp.actual_profit is not None]
            max_drawdown = min(profits) if profits else 0
            
            # Calculate Sharpe ratio (simplified)
            if profits:
                avg_return = sum(profits) / len(profits)
                volatility = (sum((p - avg_return) ** 2 for p in profits) / len(profits)) ** 0.5
                sharpe_ratio = avg_return / max(volatility, 0.01)  # Avoid division by zero
            else:
                sharpe_ratio = 0
            
            # Issues detection
            issues_detected = []
            if success_rate < 70:
                issues_detected.append(f"Low success rate: {success_rate:.1f}%")
            if profit_per_trade < 0.1:
                issues_detected.append(f"Low profit per trade: ${profit_per_trade:.4f}")
            if max_drawdown < -50:
                issues_detected.append(f"High drawdown detected: ${max_drawdown:.2f}")
            
            # Missed opportunities
            opportunities_missed = len([opp for opp in opportunities 
                                      if opp.status in ['failed', 'expired']])
            
            # Average execution latency
            execution_times = [opp.execution_time_ms for opp in opportunities 
                             if opp.execution_time_ms is not None]
            execution_latency_avg = sum(execution_times) / max(len(execution_times), 1) if execution_times else 0
            
            return PerformanceReport(
                period=f"{start_time.strftime('%Y-%m-%d')} to {end_time.strftime('%Y-%m-%d')}",
                total_trades=total_trades,
                successful_trades=successful_trades,
                total_profit=total_profit,
                total_fees=total_fees,
                success_rate=success_rate,
                profit_per_trade=profit_per_trade,
                max_drawdown=max_drawdown,
                sharpe_ratio=sharpe_ratio,
                exchange_performance=exchange_performance,
                strategy_performance=strategy_performance,
                risk_metrics={
                    'max_drawdown': max_drawdown,
                    'sharpe_ratio': sharpe_ratio,
                    'volatility': volatility if 'volatility' in locals() else 0
                },
                market_conditions={},  # Will be filled by market analysis
                issues_detected=issues_detected,
                opportunities_missed=opportunities_missed,
                execution_latency_avg=execution_latency_avg
            )
    
    async def _analyze_market_conditions(self) -> Dict[str, Any]:
        """Analyze current market conditions"""
        
        # This would integrate with market data APIs
        # For now, return basic structure
        return {
            'volatility_level': 'medium',
            'trend': 'sideways',
            'volume_24h': 'normal',
            'spread_opportunities': 'moderate',
            'risk_factors': ['exchange_latency', 'low_liquidity_periods']
        }
    
    async def _get_claude_recommendations(self, report: PerformanceReport, 
                                        market_analysis: Dict[str, Any]) -> List[ClaudeRecommendation]:
        """Get recommendations from Claude AI"""
        
        if not self.claude_api_key:
            logger.warning("claude_api_key_not_configured")
            return []
        
        # Prepare analysis prompt
        analysis_prompt = self._build_analysis_prompt(report, market_analysis)
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    'Authorization': f'Bearer {self.claude_api_key}',
                    'Content-Type': 'application/json',
                    'x-api-key': self.claude_api_key
                }
                
                payload = {
                    'model': self.model,
                    'max_tokens': 4000,
                    'messages': [
                        {
                            'role': 'user',
                            'content': analysis_prompt
                        }
                    ]
                }
                
                async with session.post(self.claude_api_url, 
                                      headers=headers, 
                                      json=payload) as response:
                    
                    if response.status == 200:
                        result = await response.json()
                        claude_response = result['content'][0]['text']
                        
                        # Parse Claude's response into structured recommendations
                        return self._parse_claude_response(claude_response)
                    else:
                        error_text = await response.text()
                        logger.error("claude_api_error", 
                                   status=response.status, 
                                   error=error_text)
                        return []
                        
        except Exception as e:
            logger.error("claude_api_request_failed", error=str(e))
            return []
    
    def _build_analysis_prompt(self, report: PerformanceReport, 
                             market_analysis: Dict[str, Any]) -> str:
        """Build comprehensive analysis prompt for Claude"""
        
        return f"""
You are an expert quantitative trading analyst for SmartArb Engine, a cryptocurrency arbitrage trading system. 

Analyze the following performance report and provide actionable recommendations for optimization:

## PERFORMANCE REPORT
Period: {report.period}
- Total Trades: {report.total_trades}
- Successful Trades: {report.successful_trades}
- Success Rate: {report.success_rate:.1f}%
- Total Profit: ${report.total_profit:.4f}
- Profit per Trade: ${report.profit_per_trade:.4f}
- Max Drawdown: ${report.max_drawdown:.4f}
- Sharpe Ratio: {report.sharpe_ratio:.2f}

## EXCHANGE PERFORMANCE
{json.dumps(report.exchange_performance, indent=2)}

## STRATEGY PERFORMANCE  
{json.dumps(report.strategy_performance, indent=2)}

## ISSUES DETECTED
{', '.join(report.issues_detected) if report.issues_detected else 'None'}

## MARKET CONDITIONS
{json.dumps(market_analysis, indent=2)}

## TECHNICAL METRICS
- Opportunities Missed: {report.opportunities_missed}
- Average Execution Latency: {report.execution_latency_avg:.1f}ms

Please provide your analysis in this EXACT JSON format:

```json
{{
  "recommendations": [
    {{
      "category": "risk|strategy|technical|market",
      "priority": "low|medium|high|critical", 
      "title": "Brief title",
      "description": "Detailed explanation",
      "code_changes": [
        {{
          "file": "path/to/file.py",
          "function": "function_name", 
          "change_type": "modify_parameter|add_logic|optimize",
          "current_value": "current setting",
          "suggested_value": "new setting",
          "reason": "why this change helps"
        }}
      ],
      "config_changes": {{
        "section.parameter": "new_value"
      }},
      "implementation_plan": ["step 1", "step 2"],
      "expected_impact": "Expected improvement description",
      "risks": ["potential risk 1", "potential risk 2"]
    }}
  ],
  "summary": "Overall assessment and key insights",
  "confidence_score": 0.85
}}
```

Focus on:
1. Performance optimization opportunities
2. Risk management improvements  
3. Strategy parameter tuning
4. Technical optimizations
5. Market-specific adaptations

Be specific with numeric recommendations and code changes.
"""
    
    def _parse_claude_response(self, response: str) -> List[ClaudeRecommendation]:
        """Parse Claude's JSON response into recommendation objects"""
        
        try:
            # Extract JSON from response
            start_idx = response.find('```json')
            end_idx = response.find('```', start_idx + 7)
            
            if start_idx != -1 and end_idx != -1:
                json_str = response[start_idx + 7:end_idx].strip()
                parsed = json.loads(json_str)
                
                recommendations = []
                for rec_data in parsed.get('recommendations', []):
                    recommendation = ClaudeRecommendation(
                        category=rec_data['category'],
                        priority=rec_data['priority'],
                        title=rec_data['title'],
                        description=rec_data['description'],
                        code_changes=rec_data.get('code_changes'),
                        config_changes=rec_data.get('config_changes'),
                        implementation_plan=rec_data.get('implementation_plan'),
                        expected_impact=rec_data.get('expected_impact'),
                        risks=rec_data.get('risks')
                    )
                    recommendations.append(recommendation)
                
                logger.info("claude_response_parsed", 
                          recommendations_count=len(recommendations))
                return recommendations
            else:
                logger.warning("no_json_found_in_claude_response")
                return []
                
        except Exception as e:
            logger.error("claude_response_parsing_failed", error=str(e))
            return []
    
    async def _validate_recommendations(self, recommendations: List[ClaudeRecommendation]) -> List[ClaudeRecommendation]:
        """Validate and filter recommendations based on safety and feasibility"""
        
        validated = []
        
        for rec in recommendations:
            # Safety checks
            if rec.priority == 'critical' and not rec.risks:
                logger.warning("critical_recommendation_without_risks", title=rec.title)
                continue
            
            # Code change validation
            if rec.code_changes:
                for change in rec.code_changes:
                    if not self._validate_code_change(change):
                        logger.warning("unsafe_code_change_detected", 
                                     file=change.get('file'),
                                     function=change.get('function'))
                        continue
            
            # Config change validation
            if rec.config_changes:
                if not self._validate_config_changes(rec.config_changes):
                    logger.warning("invalid_config_changes", changes=rec.config_changes)
                    continue
            
            validated.append(rec)
        
        logger.info("recommendations_validated", 
                   original=len(recommendations),
                   validated=len(validated))
        
        return validated
    
    def _validate_code_change(self, change: Dict[str, str]) -> bool:
        """Validate individual code change for safety"""
        
        # Check if file exists and is part of our codebase
        file_path = Path(change.get('file', ''))
        if not file_path.exists() or not str(file_path).startswith('src/'):
            return False
        
        # Blacklist dangerous operations
        dangerous_patterns = [
            'exec', 'eval', '__import__', 'subprocess', 'os.system',
            'rm -rf', 'DELETE FROM', 'DROP TABLE'
        ]
        
        suggested_value = change.get('suggested_value', '').lower()
        for pattern in dangerous_patterns:
            if pattern.lower() in suggested_value:
                return False
        
        return True
    
    def _validate_config_changes(self, changes: Dict[str, Any]) -> bool:
        """Validate configuration changes"""
        
        # Define safe config parameters
        safe_parameters = {
            'risk_management.min_profit_threshold',
            'risk_management.max_position_size', 
            'trading.order_timeout',
            'strategies.spatial_arbitrage.scan_interval',
            'engine.update_interval'
        }
        
        for key in changes.keys():
            if key not in safe_parameters:
                return False
        
        return True
    
    async def _apply_safe_recommendations(self, recommendations: List[ClaudeRecommendation]):
        """Automatically apply safe, low-risk recommendations"""
        
        applied_count = 0
        
        for rec in recommendations:
            # Only apply low/medium priority config changes automatically
            if (rec.priority in ['low', 'medium'] and 
                rec.config_changes and 
                not rec.code_changes):
                
                try:
                    await self._apply_config_changes(rec.config_changes)
                    applied_count += 1
                    
                    logger.info("auto_applied_recommendation",
                              title=rec.title,
                              changes=rec.config_changes)
                    
                except Exception as e:
                    logger.error("auto_apply_failed", 
                               title=rec.title,
                               error=str(e))
        
        if applied_count > 0:
            logger.info("recommendations_auto_applied", count=applied_count)
    
    async def _apply_config_changes(self, changes: Dict[str, Any]):
        """Apply configuration changes safely"""
        
        for key, value in changes.items():
            self.config.set(key, value)
            logger.debug("config_changed", key=key, value=value)
        
        # Save configuration
        # self.config.save()  # Would implement config saving
    
    async def _store_analysis_results(self, report: PerformanceReport, 
                                    recommendations: List[ClaudeRecommendation]):
        """Store analysis results for historical tracking"""
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Store performance report
        report_file = self.reports_dir / f'performance_report_{timestamp}.json'
        with open(report_file, 'w') as f:
            json.dump(asdict(report), f, indent=2, default=str)
        
        # Store recommendations
        recommendations_file = self.reports_dir / f'recommendations_{timestamp}.json'
        with open(recommendations_file, 'w') as f:
            json.dump([asdict(rec) for rec in recommendations], f, indent=2, default=str)
        
        # Update analysis history
        self.analysis_history.append({
            'timestamp': timestamp,
            'report_file': str(report_file),
            'recommendations_file': str(recommendations_file),
            'recommendations_count': len(recommendations),
            'total_profit': report.total_profit,
            'success_rate': report.success_rate
        })
        
        logger.info("analysis_results_stored", 
                   timestamp=timestamp,
                   recommendations_count=len(recommendations))
    
    async def get_manual_analysis(self, custom_prompt: str) -> str:
        """Get manual analysis from Claude with custom prompt"""
        
        if not self.claude_api_key:
            return "Claude API key not configured"
        
        # Add context about SmartArb Engine
        context_prompt = f"""
You are analyzing SmartArb Engine, a cryptocurrency arbitrage trading system.

Current system status:
- Running on Raspberry Pi 5
- Trading on Kraken, Bybit, MEXC
- Strategies: Spatial arbitrage (active), Triangular arbitrage (planned)
- Risk management: Active with emergency stops
- Performance tracking: Real-time

User question: {custom_prompt}

Please provide detailed analysis and recommendations.
"""
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    'Authorization': f'Bearer {self.claude_api_key}',
                    'Content-Type': 'application/json'
                }
                
                payload = {
                    'model': self.model,
                    'max_tokens': 3000,
                    'messages': [{'role': 'user', 'content': context_prompt}]
                }
                
                async with session.post(self.claude_api_url, 
                                      headers=headers, 
                                      json=payload) as response:
                    
                    if response.status == 200:
                        result = await response.json()
                        return result['content'][0]['text']
                    else:
                        return f"Error: {response.status} - {await response.text()}"
                        
        except Exception as e:
            logger.error("manual_analysis_failed", error=str(e))
            return f"Analysis failed: {str(e)}"
    
    def get_analysis_history(self) -> List[Dict[str, Any]]:
        """Get historical analysis results"""
        return self.analysis_history.copy()
    
    def get_latest_recommendations(self) -> Optional[List[ClaudeRecommendation]]:
        """Get most recent recommendations"""
        if not self.analysis_history:
            return None
        
        latest = self.analysis_history[-1]
        recommendations_file = Path(latest['recommendations_file'])
        
        if recommendations_file.exists():
            with open(recommendations_file, 'r') as f:
                recommendations_data = json.load(f)
                return [ClaudeRecommendation(**rec) for rec in recommendations_data]
        
        return None
