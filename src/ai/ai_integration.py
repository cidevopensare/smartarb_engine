#!/usr/bin/env python3
"""
SmartArb Engine - AI Integration Manager
========================================
Modulo di integrazione tra AI Advisor e Core Engine
"""

import asyncio
import logging
import time
import json
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from src.ai.ai_advisor import AIAdvisor, AISuggestion, SuggestionType, AnalysisLevel
    from src.core.logger import get_logger
except ImportError as e:
    print(f"Import error: {e}")
    # Fallback logger
    def get_logger(name):
        logging.basicConfig(level=logging.INFO)
        return logging.getLogger(name)

@dataclass
class AIIntegrationConfig:
    """Configurazione per l'integrazione AI"""
    enabled: bool = True
    analysis_interval: int = 300  # 5 minuti
    auto_telegram_alerts: bool = True
    high_priority_threshold: int = 4
    suggestion_retention_hours: int = 24

class AIIntegrationManager:
    """
    Gestisce l'integrazione tra AI Advisor e SmartArb Engine
    """
    
    def __init__(self, config: AIIntegrationConfig, telegram_notifier=None):
        self.config = config
        self.telegram = telegram_notifier
        self.logger = get_logger('ai_integration')
        
        # Inizializza AI Advisor
        ai_config = {
            'ai_enabled': config.enabled,
            'ai_analysis_interval': config.analysis_interval,
            'ai_suggestion_threshold': 0.7
        }
        self.ai_advisor = AIAdvisor(ai_config)
        
        # Stato integrazione
        self.is_running = False
        self.last_analysis = None
        self.analysis_queue = asyncio.Queue()
        
        # Statistiche integrazione
        self.integration_stats = {
            'total_analyses': 0,
            'suggestions_sent_to_telegram': 0,
            'opportunities_analyzed': 0,
            'start_time': time.time()
        }
        
        self.logger.info("🔗 AI Integration Manager initialized")
    
    async def start(self):
        """Avvia il manager di integrazione AI"""
        if not self.config.enabled:
            self.logger.info("🧠 AI Integration disabled by configuration")
            return
        
        self.is_running = True
        self.logger.info("🚀 Starting AI Integration Manager...")
        
        # Avvia task asincroni
        tasks = [
            asyncio.create_task(self._analysis_loop()),
            asyncio.create_task(self._suggestion_monitor()),
            asyncio.create_task(self._cleanup_loop())
        ]
        
        # Messaggio di avvio
        await self._send_startup_notification()
        
        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            self.logger.error(f"❌ AI Integration error: {e}")
        finally:
            self.is_running = False
    
    async def stop(self):
        """Ferma il manager"""
        self.logger.info("⏹️ Stopping AI Integration Manager...")
        self.is_running = False
        await self._send_shutdown_notification()
    
    async def analyze_opportunity(self, opportunity: Dict[str, Any]) -> List[AISuggestion]:
        """Analizza un'opportunità tramite AI"""
        if not self.config.enabled:
            return []
        
        try:
            # Aggiungi alla coda per analisi
            await self.analysis_queue.put({
                'type': 'opportunity',
                'data': opportunity,
                'timestamp': datetime.now()
            })
            
            # Analisi immediata per opportunità critiche
            if opportunity.get('spread', 0) > 3.0:
                suggestions = await self.ai_advisor.analyze_arbitrage_opportunity(opportunity)
                await self._process_suggestions(suggestions, opportunity)
                return suggestions
            
            return []
            
        except Exception as e:
            self.logger.error(f"❌ Error analyzing opportunity: {e}")
            return []
    
    async def _analysis_loop(self):
        """Loop principale di analisi"""
        while self.is_running:
            try:
                # Processa coda di analisi
                if not self.analysis_queue.empty():
                    analysis_item = await self.analysis_queue.get()
                    await self._process_analysis_item(analysis_item)
                
                await asyncio.sleep(5)
                
            except Exception as e:
                self.logger.error(f"❌ Analysis loop error: {e}")
                await asyncio.sleep(10)
    
    async def _process_analysis_item(self, item: Dict[str, Any]):
        """Processa un elemento dalla coda di analisi"""
        try:
            if item['type'] == 'opportunity':
                opportunity = item['data']
                suggestions = await self.ai_advisor.analyze_arbitrage_opportunity(opportunity)
                await self._process_suggestions(suggestions, opportunity)
                self.integration_stats['opportunities_analyzed'] += 1
            
            self.integration_stats['total_analyses'] += 1
            
        except Exception as e:
            self.logger.error(f"❌ Error processing analysis item: {e}")
    
    async def _process_suggestions(self, suggestions: List[AISuggestion], context: Dict[str, Any] = None):
        """Processa i suggerimenti generati dall'AI"""
        if not suggestions:
            return
        
        for suggestion in suggestions:
            # Aggiunge alla lista attiva
            self.ai_advisor.add_suggestion_to_active(suggestion)
            
            # Log del suggerimento
            self.logger.info(f"💡 AI Suggestion: {suggestion.title} (Priority: {suggestion.priority})")
            
            # Invio notifica Telegram per alta priorità
            if (suggestion.priority >= self.config.high_priority_threshold and 
                self.config.auto_telegram_alerts and self.telegram):
                await self._send_telegram_suggestion(suggestion, context)
    
    async def _send_telegram_suggestion(self, suggestion: AISuggestion, context: Dict[str, Any] = None):
        """Invia suggerimento tramite Telegram"""
        try:
            emoji_map = {
                SuggestionType.OPPORTUNITY: "🎯",
                SuggestionType.RISK_WARNING: "⚠️",
                SuggestionType.OPTIMIZATION: "⚡",
                SuggestionType.MARKET_INSIGHT: "📊"
            }
            
            emoji = emoji_map.get(suggestion.type, "🤖")
            priority_stars = "⭐" * suggestion.priority
            
            message = f"""{emoji} **AI SUGGESTION** {priority_stars}

**{suggestion.title}**

📝 {suggestion.description}

🧠 **Reasoning**: {suggestion.reasoning}

🎯 **Confidence**: {suggestion.confidence:.1%}

⏰ **Time**: {suggestion.timestamp.strftime('%H:%M:%S')}"""
            
            if suggestion.expires_at:
                message += f"\n⏳ **Expires**: {suggestion.expires_at.strftime('%H:%M:%S')}"
            
            if context and context.get('pair'):
                message += f"\n💱 **Pair**: {context['pair']}"
                if context.get('spread'):
                    message += f"\n📈 **Spread**: {context['spread']:.2f}%"
            
            # Invia notifica
            if hasattr(self.telegram, 'send_notification'):
                await self.telegram.send_notification(message)
                self.integration_stats['suggestions_sent_to_telegram'] += 1
            
        except Exception as e:
            self.logger.error(f"❌ Error sending Telegram suggestion: {e}")
    
    async def _suggestion_monitor(self):
        """Monitor dei suggerimenti attivi"""
        while self.is_running:
            try:
                # Cleanup suggerimenti scaduti
                await self.ai_advisor.cleanup_expired_suggestions()
                
                # Report periodico suggerimenti
                active_suggestions = await self.ai_advisor.get_active_suggestions()
                high_priority = [s for s in active_suggestions if s.priority >= 4]
                
                if len(high_priority) > 3:
                    self.logger.warning(f"⚠️ {len(high_priority)} high-priority AI suggestions active")
                
                await asyncio.sleep(60)
                
            except Exception as e:
                self.logger.error(f"❌ Suggestion monitor error: {e}")
                await asyncio.sleep(60)
    
    async def _cleanup_loop(self):
        """Loop di pulizia periodica"""
        while self.is_running:
            try:
                await self.ai_advisor.cleanup_expired_suggestions()
                await asyncio.sleep(3600)  # Ogni ora
                
            except Exception as e:
                self.logger.error(f"❌ Cleanup loop error: {e}")
                await asyncio.sleep(3600)
    
    async def _send_startup_notification(self):
        """Invia notifica di avvio AI"""
        if self.telegram and self.config.auto_telegram_alerts:
            message = """🧠 **AI SYSTEM ACTIVATED**

✅ AI Advisor: Online
✅ Analysis Engine: Ready
✅ Suggestion Monitor: Running

🚀 **SmartArb AI is now providing intelligent suggestions!**"""
            
            try:
                if hasattr(self.telegram, 'send_notification'):
                    await self.telegram.send_notification(message)
            except:
                pass
    
    async def _send_shutdown_notification(self):
        """Invia notifica di spegnimento AI"""
        if self.telegram and self.config.auto_telegram_alerts:
            stats = await self.get_integration_stats()
            message = f"""🧠 **AI SYSTEM SHUTDOWN**

📊 **Session Summary**:
🔍 Total Analyses: {stats['total_analyses']}
💡 Suggestions Generated: {stats.get('total_suggestions', 0)}
📱 Telegram Alerts: {stats['suggestions_sent_to_telegram']}

✅ AI system gracefully shut down"""
            
            try:
                if hasattr(self.telegram, 'send_notification'):
                    await self.telegram.send_notification(message)
            except:
                pass
    
    async def get_integration_stats(self) -> Dict[str, Any]:
        """Ottieni statistiche di integrazione"""
        ai_stats = self.ai_advisor.get_stats()
        uptime = time.time() - self.integration_stats['start_time']
        
        return {
            **self.integration_stats,
            'total_suggestions': ai_stats.get('suggestions_generated', 0),
            'uptime_hours': uptime / 3600,
            'ai_advisor_stats': ai_stats,
            'active_suggestions_count': len(await self.ai_advisor.get_active_suggestions())
        }
    
    def get_active_suggestions_sync(self) -> List[Dict[str, Any]]:
        """Versione sincrona per API REST"""
        try:
            suggestions = self.ai_advisor.active_suggestions[-5:]  # Ultimi 5
            return [
                {
                    'type': s.type.value,
                    'priority': s.priority,
                    'title': s.title,
                    'description': s.description[:100] + '...' if len(s.description) > 100 else s.description,
                    'confidence': f"{s.confidence:.1%}",
                    'timestamp': s.timestamp.strftime('%H:%M:%S')
                } for s in suggestions
            ]
        except:
            return []

if __name__ == "__main__":
    # Test integration manager
    config = AIIntegrationConfig(enabled=True)
    manager = AIIntegrationManager(config)
    
    import asyncio
    
    async def test_ai_integration():
        print("Testing AI Integration Manager...")
        
        test_opportunity = {
            'pair': 'BTC-USDT',
            'spread': 4.5,  # High spread to trigger suggestions
            'volume': 5000,
            'exchanges': ['Bybit', 'MEXC']
        }
        
        result = await manager.analyze_opportunity(test_opportunity)
        print(f"Analysis result: {len(result)} suggestions")
        
        stats = await manager.get_integration_stats()
        print(f"Integration stats: {stats}")
    
    asyncio.run(test_ai_integration())
    print("AI Integration test completed")

# Compatibility alias
SmartArbAI = SmartArbAIAdvisor if 'SmartArbAIAdvisor' in globals() else None

# Or create a simple SmartArbAI class
class SmartArbAI:
    def __init__(self):
        self.initialized = False
    
    async def initialize(self):
        self.initialized = True
        return True

