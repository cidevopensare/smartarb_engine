#!/usr/bin/env python3
"""
SmartArb Engine - AI Advisor Module
Provides intelligent trading recommendations and risk assessments
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

try:
    import structlog
    logger = structlog.get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

class Priority(Enum):
    """Recommendation priority levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class AdviceType(Enum):
    """Types of AI advice"""
    RISK_MANAGEMENT = "risk_management"
    STRATEGY_OPTIMIZATION = "strategy_optimization"
    MARKET_ANALYSIS = "market_analysis"
    SYSTEM_HEALTH = "system_health"
    EMERGENCY_ACTION = "emergency_action"

@dataclass
class Recommendation:
    """Individual AI recommendation"""
    id: str
    type: AdviceType
    priority: Priority
    title: str
    description: str
    action_required: bool
    confidence_score: float
    data_support: Dict[str, Any]
    timestamp: datetime
    expires_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format"""
        return {
            'id': self.id,
            'type': self.type.value,
            'priority': self.priority.value,
            'title': self.title,
            'description': self.description,
            'action_required': self.action_required,
            'confidence_score': self.confidence_score,
            'data_support': self.data_support,
            'timestamp': self.timestamp.isoformat(),
            'expires_at': self.expires_at.isoformat() if self.expires_at else None
        }

class SmartArbAIAdvisor:
    """AI Advisory system for SmartArb Engine"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.recommendations = []
        self.analysis_history = []
        self.risk_thresholds = self._load_risk_thresholds()
        self.is_initialized = False
        
    def _load_risk_thresholds(self) -> Dict[str, float]:
        """Load risk management thresholds"""
        return {
            'max_drawdown': self.config.get('risk.max_drawdown', 0.05),  # 5%
            'min_win_rate': self.config.get('risk.min_win_rate', 0.60),  # 60%
            'max_daily_loss': self.config.get('risk.max_daily_loss', 100),  # $100
            'min_confidence': self.config.get('ai.min_confidence', 0.70),  # 70%
            'max_position_size': self.config.get('risk.max_position_size', 0.10),  # 10%
        }
    
    async def initialize(self) -> bool:
        """Initialize the AI advisor"""
        try:
            logger.info("🧠 Initializing AI Advisor...")
            
            # Load historical data if available
            await self._load_analysis_history()
            
            # Initialize recommendation engine
            await self._initialize_recommendation_engine()
            
            self.is_initialized = True
            logger.info("✅ AI Advisor initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ AI Advisor initialization failed: {e}")
            return False
    
    async def _load_analysis_history(self):
        """Load previous analysis history"""
        try:
            # In a real implementation, this would load from database
            # For now, just initialize empty
            self.analysis_history = []
            logger.info("📚 Analysis history loaded")
        except Exception as e:
            logger.warning(f"⚠️ Could not load analysis history: {e}")
    
    async def _initialize_recommendation_engine(self):
        """Initialize the recommendation engine"""
        try:
            # Initialize any ML models or external services here
            logger.info("🤖 Recommendation engine initialized")
        except Exception as e:
            logger.warning(f"⚠️ Recommendation engine init warning: {e}")
    
    async def analyze_trading_performance(self, performance_data: Dict[str, Any]) -> List[Recommendation]:
        """Analyze trading performance and generate recommendations"""
        recommendations = []
        
        try:
            total_trades = performance_data.get('total_trades', 0)
            win_rate = performance_data.get('win_rate', 0.0)
            total_profit = performance_data.get('total_profit', 0.0)
            max_drawdown = performance_data.get('max_drawdown', 0.0)
            daily_profit = performance_data.get('daily_profit', 0.0)
            
            # Risk Management Analysis
            recommendations.extend(
                await self._analyze_risk_metrics(win_rate, max_drawdown, daily_profit)
            )
            
            # Performance Analysis
            recommendations.extend(
                await self._analyze_performance_trends(total_trades, total_profit, win_rate)
            )
            
            # Market Condition Analysis
            recommendations.extend(
                await self._analyze_market_conditions(performance_data)
            )
            
            # Store analysis
            self.analysis_history.append({
                'timestamp': datetime.now(),
                'performance_data': performance_data,
                'recommendations_count': len(recommendations)
            })
            
            # Update current recommendations
            self.recommendations = recommendations
            
            logger.info(f"📊 Analysis complete: {len(recommendations)} recommendations generated")
            return recommendations
            
        except Exception as e:
            logger.error(f"❌ Performance analysis failed: {e}")
            return []
    
    async def _analyze_risk_metrics(self, win_rate: float, max_drawdown: float, daily_profit: float) -> List[Recommendation]:
        """Analyze risk metrics and generate risk recommendations"""
        recommendations = []
        
        # Win Rate Analysis
        if win_rate < self.risk_thresholds['min_win_rate']:
            recommendations.append(Recommendation(
                id=f"risk_winrate_{int(time.time())}",
                type=AdviceType.RISK_MANAGEMENT,
                priority=Priority.HIGH if win_rate < 0.50 else Priority.MEDIUM,
                title="Low Win Rate Detected",
                description=f"Current win rate ({win_rate:.1%}) is below target ({self.risk_thresholds['min_win_rate']:.1%}). Consider adjusting strategy parameters or reducing position sizes.",
                action_required=True,
                confidence_score=0.85,
                data_support={'current_win_rate': win_rate, 'target_win_rate': self.risk_thresholds['min_win_rate']},
                timestamp=datetime.now(),
                expires_at=datetime.now() + timedelta(hours=24)
            ))
        
        # Drawdown Analysis
        if max_drawdown > self.risk_thresholds['max_drawdown']:
            recommendations.append(Recommendation(
                id=f"risk_drawdown_{int(time.time())}",
                type=AdviceType.RISK_MANAGEMENT,
                priority=Priority.CRITICAL if max_drawdown > 0.10 else Priority.HIGH,
                title="Excessive Drawdown Alert",
                description=f"Maximum drawdown ({max_drawdown:.1%}) exceeds safe limits ({self.risk_thresholds['max_drawdown']:.1%}). Implement stricter risk controls immediately.",
                action_required=True,
                confidence_score=0.95,
                data_support={'current_drawdown': max_drawdown, 'max_allowed': self.risk_thresholds['max_drawdown']},
                timestamp=datetime.now(),
                expires_at=datetime.now() + timedelta(hours=1)
            ))
        
        # Daily Loss Analysis
        if daily_profit < -self.risk_thresholds['max_daily_loss']:
            recommendations.append(Recommendation(
                id=f"risk_daily_loss_{int(time.time())}",
                type=AdviceType.EMERGENCY_ACTION,
                priority=Priority.CRITICAL,
                title="Daily Loss Limit Exceeded",
                description=f"Daily losses (${abs(daily_profit):.2f}) exceed maximum threshold (${self.risk_thresholds['max_daily_loss']:.2f}). Consider halting trading for today.",
                action_required=True,
                confidence_score=0.99,
                data_support={'daily_loss': daily_profit, 'max_loss_threshold': -self.risk_thresholds['max_daily_loss']},
                timestamp=datetime.now(),
                expires_at=datetime.now() + timedelta(minutes=30)
            ))
        
        return recommendations
    
    async def _analyze_performance_trends(self, total_trades: int, total_profit: float, win_rate: float) -> List[Recommendation]:
        """Analyze performance trends"""
        recommendations = []
        
        # Low Activity Analysis
        if total_trades < 5 and total_trades > 0:
            recommendations.append(Recommendation(
                id=f"perf_low_activity_{int(time.time())}",
                type=AdviceType.STRATEGY_OPTIMIZATION,
                priority=Priority.MEDIUM,
                title="Low Trading Activity",
                description=f"Only {total_trades} trades executed. Check for market opportunities or adjust strategy sensitivity.",
                action_required=False,
                confidence_score=0.75,
                data_support={'total_trades': total_trades},
                timestamp=datetime.now(),
                expires_at=datetime.now() + timedelta(hours=12)
            ))
        
        # Profitability Analysis
        if total_trades > 10:
            avg_profit_per_trade = total_profit / total_trades if total_trades > 0 else 0
            
            if avg_profit_per_trade < 0:
                recommendations.append(Recommendation(
                    id=f"perf_negative_avg_{int(time.time())}",
                    type=AdviceType.STRATEGY_OPTIMIZATION,
                    priority=Priority.HIGH,
                    title="Negative Average Profit Per Trade",
                    description=f"Average loss per trade: ${avg_profit_per_trade:.2f}. Strategy optimization urgently needed.",
                    action_required=True,
                    confidence_score=0.90,
                    data_support={
                        'avg_profit_per_trade': avg_profit_per_trade,
                        'total_profit': total_profit,
                        'total_trades': total_trades
                    },
                    timestamp=datetime.now(),
                    expires_at=datetime.now() + timedelta(hours=6)
                ))
        
        return recommendations
    
    async def _analyze_market_conditions(self, performance_data: Dict[str, Any]) -> List[Recommendation]:
        """Analyze market conditions and provide insights"""
        recommendations = []
        
        # Market Volatility Analysis
        volatility_score = performance_data.get('volatility_score', 0.5)
        
        if volatility_score > 0.8:
            recommendations.append(Recommendation(
                id=f"market_high_vol_{int(time.time())}",
                type=AdviceType.MARKET_ANALYSIS,
                priority=Priority.MEDIUM,
                title="High Market Volatility",
                description="Elevated market volatility detected. Consider reducing position sizes and increasing monitoring frequency.",
                action_required=False,
                confidence_score=0.70,
                data_support={'volatility_score': volatility_score},
                timestamp=datetime.now(),
                expires_at=datetime.now() + timedelta(hours=4)
            ))
        elif volatility_score < 0.2:
            recommendations.append(Recommendation(
                id=f"market_low_vol_{int(time.time())}",
                type=AdviceType.MARKET_ANALYSIS,
                priority=Priority.LOW,
                title="Low Market Volatility",
                description="Market volatility is unusually low. Arbitrage opportunities may be limited.",
                action_required=False,
                confidence_score=0.60,
                data_support={'volatility_score': volatility_score},
                timestamp=datetime.now(),
                expires_at=datetime.now() + timedelta(hours=8)
            ))
        
        return recommendations
    
    async def get_active_recommendations(self, priority_filter: Optional[Priority] = None) -> List[Recommendation]:
        """Get active recommendations, optionally filtered by priority"""
        try:
            active_recommendations = []
            now = datetime.now()
            
            for rec in self.recommendations:
                # Check if recommendation has expired
                if rec.expires_at and rec.expires_at < now:
                    continue
                
                # Apply priority filter if specified
                if priority_filter and rec.priority != priority_filter:
                    continue
                
                active_recommendations.append(rec)
            
            # Sort by priority and timestamp
            priority_order = {Priority.CRITICAL: 0, Priority.HIGH: 1, Priority.MEDIUM: 2, Priority.LOW: 3}
            active_recommendations.sort(
                key=lambda x: (priority_order[x.priority], x.timestamp), 
                reverse=True
            )
            
            return active_recommendations
            
        except Exception as e:
            logger.error(f"❌ Failed to get active recommendations: {e}")
            return []
    
    async def get_system_health_score(self) -> Dict[str, Any]:
        """Calculate overall system health score"""
        try:
            health_metrics = {
                'overall_score': 0.8,  # Default good score
                'risk_score': 0.9,
                'performance_score': 0.7,
                'market_score': 0.8,
                'timestamp': datetime.now().isoformat(),
                'status': 'healthy'
            }
            
            # Analyze current recommendations for health impact
            critical_count = len([r for r in self.recommendations if r.priority == Priority.CRITICAL])
            high_count = len([r for r in self.recommendations if r.priority == Priority.HIGH])
            
            # Adjust health score based on recommendation severity
            if critical_count > 0:
                health_metrics['overall_score'] -= 0.3 * critical_count
                health_metrics['status'] = 'critical'
            elif high_count > 2:
                health_metrics['overall_score'] -= 0.1 * high_count
                health_metrics['status'] = 'warning'
            
            # Ensure score doesn't go below 0
            health_metrics['overall_score'] = max(0.0, health_metrics['overall_score'])
            
            return health_metrics
            
        except Exception as e:
            logger.error(f"❌ Health score calculation failed: {e}")
            return {
                'overall_score': 0.5,
                'status': 'unknown',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    async def generate_daily_report(self) -> Dict[str, Any]:
        """Generate daily AI analysis report"""
        try:
            active_recs = await self.get_active_recommendations()
            health_score = await self.get_system_health_score()
            
            report = {
                'date': datetime.now().date().isoformat(),
                'summary': {
                    'total_recommendations': len(active_recs),
                    'critical_alerts': len([r for r in active_recs if r.priority == Priority.CRITICAL]),
                    'high_priority': len([r for r in active_recs if r.priority == Priority.HIGH]),
                    'health_score': health_score['overall_score'],
                    'status': health_score['status']
                },
                'recommendations': [rec.to_dict() for rec in active_recs[:10]],  # Top 10
                'health_metrics': health_score,
                'analysis_count': len(self.analysis_history),
                'generated_at': datetime.now().isoformat()
            }
            
            return report
            
        except Exception as e:
            logger.error(f"❌ Daily report generation failed: {e}")
            return {
                'error': str(e),
                'generated_at': datetime.now().isoformat()
            }
    
    def get_advisor_status(self) -> Dict[str, Any]:
        """Get current advisor status"""
        return {
            'initialized': self.is_initialized,
            'active_recommendations': len(self.recommendations),
            'analysis_history_count': len(self.analysis_history),
            'last_analysis': self.analysis_history[-1]['timestamp'].isoformat() if self.analysis_history else None,
            'risk_thresholds': self.risk_thresholds,
            'version': '1.0.0'
        }

# Create aliases for backward compatibility
AIAdvisor = SmartArbAIAdvisor
AISuggestion = Recommendation
SuggestionType = AdviceType
AnalysisLevel = Priority

# Export main class and aliases
__all__ = ['SmartArbAIAdvisor', 'AIAdvisor', 'Recommendation', 'AISuggestion', 'SuggestionType', 'AnalysisLevel', 'Priority', 'AdviceType']
