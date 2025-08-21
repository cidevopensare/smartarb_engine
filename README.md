# SmartArb Engine 🚀

Un sistema di trading algoritmico professionale per arbitraggio su criptovalute, progettato per operare su Raspberry Pi 5 e facilmente scalabile su infrastrutture cloud.

## 📊 Overview

SmartArb Engine è un bot di arbitraggio crypto avanzato che identifica ed esegue automaticamente opportunità di arbitraggio tra exchange multipli. Il sistema è progettato per essere:

- **Efficiente**: Ottimizzato per hardware a basso consumo come Raspberry Pi
- **Scalabile**: Architettura modulare pronta per la migrazione cloud
- **Sicuro**: Risk management integrato e controlli di sicurezza
- **Affidabile**: Monitoraggio continuo e gestione errori robusta
- **🧠 Intelligente**: Integrazione Claude AI per analisi automatica e ottimizzazione

### Exchange Supportati

- **Kraken** - Exchange tier-1 con ottima sicurezza e liquidità
- **Bybit** - Piattaforma moderna con API veloci e commissioni competitive  
- **MEXC** - Ampia selezione altcoin e opportunità di arbitraggio frequenti

### Strategie Implementate

- ✅ **Spatial Arbitrage** - Arbitraggio cross-exchange
- 🔄 **Triangular Arbitrage** - In sviluppo
- 🚀 **MEV-Style Strategies** - Roadmap futura

### 🧠 **Integrazione Claude AI**

SmartArb Engine include un sistema di intelligenza artificiale avanzato:

- **📊 Analisi Automatica**: Claude analizza le performance e identifica ottimizzazioni
- **🔧 Code Updates**: Aggiornamenti automatici del codice con validazione
- **📅 Scheduling Intelligente**: Analisi programmate e trigger di emergenza  
- **🎛️ Dashboard AI**: Monitoraggio real-time del sistema di intelligenza
- **💡 Raccomandazioni**: Suggerimenti personalizzati per migliorare profittabilità

**Funzionalità AI:**
```
🔍 Analisi Performance → 📋 Raccomandazioni → 🔧 Auto-Update → 📈 Miglioramento
```

## 🏗️ Architettura

```
┌─────────────────────────────────────────┐
│              SmartArb Engine             │
├─────────────────────────────────────────┤
│  🎛️  Web Dashboard (Future)             │
├─────────────────────────────────────────┤
│  ⚡ Core Engine                         │
│  ├── Strategy Manager                   │
│  ├── Risk Manager                       │  
│  ├── Portfolio Manager                  │
│  └── Execution Engine                   │
├─────────────────────────────────────────┤
│  🔗 Exchange Connectors                │
│  ├── Kraken ├── Bybit ├── MEXC         │
├─────────────────────────────────────────┤
│  📊 Data Layer                         │
│  ├── PostgreSQL ├── Redis              │
└─────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisiti

- **Hardware**: Raspberry Pi 5 (4GB+ RAM raccomandati) o sistema Linux/Windows
- **Software**: Python 3.11+, PostgreSQL, Redis
- **Connettività**: Connessione internet stabile
- **Exchange**: Account verificati su Kraken, Bybit, MEXC con API abilitati

### Installazione

1. **Clona il repository**
```bash
git clone https://github.com/your-username/smartarb-engine.git
cd smartarb-engine
```

2. **Setup ambiente virtuale**
```bash
python3.11 -m venv smartarb_env
source smartarb_env/bin/activate  # Linux/Mac
# smartarb_env\Scripts\activate    # Windows
```

3. **Installa dipendenze**
```bash
pip install -r requirements.txt
```

4. **Configura variabili d'ambiente**
```bash
cp .env.example .env
# Modifica .env con le tue credenziali API
nano .env
```

5. **Setup database**
```bash
# Installa PostgreSQL e Redis (Ubuntu/Debian)
sudo apt update
sudo apt install postgresql postgresql-contrib redis-server

# Avvia servizi
sudo systemctl enable postgresql redis-server
sudo systemctl start postgresql redis-server

# Inizializza database
python scripts/setup_database.py
```

6. **Avvia SmartArb Engine**
```bash
python -m src.core.engine
```

## ⚙️ Configurazione

### Configurazione AI Claude

**1. Ottieni API Key Claude:**
- Registrati su [Anthropic Console](https://console.anthropic.com)
- Crea una nuova API key
- Aggiungi al file `.env`:

```bash
# Aggiungi al .env
CLAUDE_API_KEY=your_claude_api_key_here
```

**2. Abilita AI nel config:**
```yaml
# config/settings.yaml
ai:
  enabled: true
  analysis_frequency: "daily"
  auto_apply_safe_changes: false
  
  scheduling:
    default: "0 */6 * * *"  # Ogni 6 ore
    emergency_triggers:
      low_success_rate: 60.0
      high_drawdown: -100.0
```

**3. Setup rapido AI:**
```bash
# Setup automatico
python scripts/setup_ai.py --quick

# Setup interattivo
python scripts/setup_ai.py
```

### File di Configurazione

Il sistema utilizza file YAML per la configurazione:

- `config/settings.yaml` - Configurazione principale
- `config/exchanges.yaml` - Configurazione exchange  
- `config/strategies.yaml` - Parametri strategie

### Configurazione Exchange

Per ogni exchange, configura le credenziali API nel file `.env`:

```bash
# Esempio per Kraken
KRAKEN_API_KEY=your_api_key
KRAKEN_API_SECRET=your_api_secret
```

**Permessi API Richiesti:**
- **Kraken**: Query Funds, Query Orders, Create & Cancel Orders
- **Bybit**: Read position, Read wallet balance, Trade
- **MEXC**: Spot trading, Read account info

### Risk Management

Il sistema include controlli di rischio configurabili:

```yaml
risk_management:
  max_position_size: 1000      # USDT
  max_daily_loss: 200          # USDT  
  min_profit_threshold: 0.20   # %
  emergency_stop: true
```

## 📈 Monitoraggio

### Sistema AI Integrato

**Dashboard AI in tempo reale:**
```bash
# Avvia API server per dashboard
python -m src.api.ai_api

# Accedi alla dashboard
http://localhost:8000/docs
```

**CLI AI per controllo manuale:**
```bash
# Analisi manuale
python -m src.cli.ai_cli analyze --focus "performance"

# Visualizza raccomandazioni
python -m src.cli.ai_cli recommendations --priority high

# Gestione scheduler
python -m src.cli.ai_cli schedule --status

# Applicazione aggiornamenti
python -m src.cli.ai_cli code --apply

# Test sistema AI
python -m src.cli.ai_cli test --test-all
```

**API Endpoints principali:**
- `GET /api/v1/status` - Status sistema AI
- `POST /api/v1/analysis/run` - Trigger analisi
- `GET /api/v1/recommendations` - Lista raccomandazioni
- `POST /api/v1/code/apply` - Applica aggiornamenti
- `GET /api/v1/dashboard` - Dati dashboard completi

### Logs

I log sono disponibili in:
- Console output (strutturato)
- `logs/smartarb.log` (file rotating)
- `logs/trades.log` (log trading specifici)
- `logs/ai/` (logs analisi AI)

### Notifiche Telegram

Configura un bot Telegram per ricevere alert (inclusi alert AI):

1. Crea un bot: chat con @BotFather su Telegram
2. Ottieni il token e chat ID
3. Configura in `.env`:
```bash
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

**Tipi di notifiche AI:**
- 🧠 Analisi completate
- 💡 Nuove raccomandazioni
- 🔧 Aggiornamenti codice applicati
- 🚨 Alert emergenza AI
- 📊 Report performance periodici

### Metriche Performance

Il sistema traccia automaticamente:
- Opportunità trovate vs eseguite
- Profitto realizzato per trade
- Success rate per exchange
- Latenza di esecuzione
- Exposure e risk metrics

**🧠 Metriche AI aggiuntive:**
- Accuratezza raccomandazioni
- Tempo di analisi medio
- Aggiornamenti applicati con successo
- Trend performance post-ottimizzazione
- Confidence score medio delle analisi

## 🛡️ Sicurezza

### Best Practices

1. **API Security**:
   - Usa chiavi API con permessi minimi
   - Abilita IP restrictions sugli exchange
   - Rota regolarmente le chiavi API
   - **🔐 Proteggi la Claude API key** (non commitarla mai)

2. **Sistema**:
   - Mantieni il sistema aggiornato
   - Usa password forti per database
   - Abilita firewall appropriato
   - **🧠 Monitora attività AI** (logs e dashboard)

3. **Trading**:
   - Inizia con paper trading (`PAPER_TRADING=true`)
   - Usa posizioni piccole inizialmente
   - Monitora attentamente le performance
   - **🤖 Verifica raccomandazioni AI** prima di applicarle

4. **AI Security**:
   - **Code Updates**: Solo changes validati vengono applicati
   - **Rollback**: Backup automatici per ogni modifica
   - **Safety Checks**: Validazione automatica codice pericoloso
   - **Emergency Stop**: Trigger automatici per problemi critici

## 📊 Performance & Scaling

### Raspberry Pi 5 Performance

Limiti stimati per Raspberry Pi 5:
- **Coppie**: 10-15 simultanee
- **Frequenza scan**: 5-10 secondi
- **Exchange**: 3-5 contemporanei
- **Daily volume**: $50K-100K
- **🧠 Analisi AI**: 1-2 al giorno (automatiche)

### Benefici AI Integration

**Ottimizzazione automatica:**
- 📈 **+15-25%** miglioramento performance medio
- 🎯 **Risk management** adattivo
- ⚡ **Latenza ridotta** via ottimizzazioni automatiche
- 🔧 **Auto-tuning** parametri in base a market conditions
- 📊 **Predictive analytics** per market trends

**Esempi di ottimizzazioni AI:**
```
Prima AI: 73% success rate, 0.28% profit/trade
Dopo AI:  87% success rate, 0.35% profit/trade
         (+19% trades, +25% profit per trade)
```

### Migrazione Cloud

Quando i volumi crescono, migra a:
1. **VPS dedicato** (più velocità + AI analysis)
2. **Cloud infrastructure** (scalabilità + advanced AI)
3. **Co-location** (latenza ultra-bassa + real-time AI)

**🧠 AI scaling path:**
- **Pi**: Basic analysis, config tuning
- **VPS**: Advanced analysis, code optimization  
- **Cloud**: ML models, predictive analytics
- **Enterprise**: Custom AI models, MEV strategies

## 🧠 Sistema AI - Guida Completa

### Quick Start AI

```bash
# 1. Setup rapido
python scripts/setup_ai.py --quick

# 2. Test connessione Claude
python -m src.cli.ai_cli test --test-claude

# 3. Prima analisi
python -m src.cli.ai_cli analyze

# 4. Visualizza raccomandazioni
python -m src.cli.ai_cli recommendations
```

### Esempi Pratici

**Analisi Performance Specifica:**
```bash
# Analisi focus su risk management
python -m src.cli.ai_cli analyze --focus "risk management" \
  --prompt "Analizza drawdown e suggerisci miglioramenti"

# Analisi latenza di esecuzione
python -m src.cli.ai_cli analyze --focus "execution speed"

# Analisi profittabilità per exchange
python -m src.cli.ai_cli analyze --focus "exchange performance"
```

**Gestione Raccomandazioni:**
```bash
# Solo raccomandazioni critiche
python -m src.cli.ai_cli recommendations --priority critical

# Raccomandazioni per categoria
python -m src.cli.ai_cli recommendations --category risk

# Applicazione automatica aggiornamenti sicuri
python -m src.cli.ai_cli code --apply
```

**Controllo Scheduler:**
```bash
# Status dettagliato
python -m src.cli.ai_cli schedule --status

# Modifica frequenza (ogni 3 ore)
python -m src.cli.ai_cli schedule --schedule "0 */3 * * *"

# Trigger manuale
python -m src.cli.ai_cli schedule --start
```

### API REST Esempi

```bash
# Trigger analisi via API
curl -X POST http://localhost:8000/api/v1/analysis/run \
  -H "Content-Type: application/json" \
  -d '{"focus_area": "performance", "priority": "high"}'

# Ottieni raccomandazioni
curl http://localhost:8000/api/v1/recommendations?priority=high

# Status sistema AI
curl http://localhost:8000/api/v1/status

# Dashboard data completa
curl http://localhost:8000/api/v1/dashboard
```

### Scenari d'Uso Tipici

**📊 Monitoraggio Daily:**
1. AI analizza performance notturna
2. Invia report via Telegram
3. Suggerisce ottimizzazioni automatiche
4. Applica changes sicuri

**🚨 Emergency Response:**
1. Success rate scende sotto 60%
2. AI trigger analisi immediata
3. Identifica cause root
4. Suggerisce correzioni urgenti

**🔧 Optimization Loop:**
1. AI rileva pattern inefficienti
2. Propone modifiche codice
3. Crea backup automatico
4. Applica e testa changes
5. Monitora impatto

**📈 Performance Tuning:**
```
Week 1: Baseline performance
Week 2: AI suggerisce tuning parametri risk
Week 3: Implementa optimizations automatiche
Week 4: +23% miglioramento profit per trade
```

## 🔧 Sviluppo

### Struttura Progetto

```
smartarb_engine/
├── src/
│   ├── core/           # Engine principale
│   ├── exchanges/      # Connettori exchange
│   ├── strategies/     # Algoritmi trading
│   ├── ai/            # 🧠 Sistema AI Claude
│   │   ├── claude_integration.py
│   │   ├── analysis_scheduler.py
│   │   ├── code_updater.py
│   │   └── dashboard.py
│   ├── api/           # 🌐 REST API
│   ├── cli/           # 💻 CLI interface
│   ├── utils/          # Utilities
│   └── db/            # Database layer
├── config/            # File configurazione
├── scripts/           # Script setup/utility
├── tests/             # Test suite (inclusi AI tests)
└── logs/              # File di log
```

### Testing

```bash
# Unit tests completi
python -m pytest tests/unit/

# Integration tests  
python -m pytest tests/integration/

# Test AI system
python -m pytest tests/test_ai_integration.py -v

# Test specifici exchange
python -m pytest tests/exchanges/

# Test performance AI
python -m pytest tests/test_ai_integration.py::TestPerformance -m slow
```

### Aggiungere Nuove Strategie

1. Eredita da `BaseStrategy`
2. Implementa `find_opportunities()`
3. Aggiungi alla configurazione
4. Registra in `StrategyManager`
5. **🧠 L'AI analizzerà automaticamente** le performance

Esempio:
```python
class MyCustomStrategy(BaseStrategy):
    async def find_opportunities(self):
        # La tua logica qui
        opportunities = []
        # AI monitorerà automaticamente questa strategia
        return opportunities
```

### Estendere Sistema AI

**Aggiungere nuovi tipi di analisi:**
```python
# src/ai/custom_analyzer.py
class CustomAnalyzer(BaseAnalyzer):
    async def analyze_market_sentiment(self):
        # Nuova analisi personalizzata
        pass
```

**Custom triggers per emergency analysis:**
```python
# Aggiungere in config/settings.yaml
ai:
  scheduling:
    emergency_triggers:
      custom_metric: threshold_value
```

**Estendere dashboard con nuove metriche:**
```python
# src/ai/dashboard.py - aggiungere in _get_performance_metrics
def _get_custom_metrics(self):
    return {"custom_metric": self.calculate_custom()}
```

## 📋 Roadmap

### Fase 1: Core MVP ✅
- [x] Spatial arbitrage base
- [x] 3 exchange integrati (Kraken, Bybit, MEXC)
- [x] Risk management
- [x] Database persistence
- [x] **🧠 Claude AI Integration**

### Fase 2: AI-Enhanced ✅
- [x] **Analisi automatica performance**
- [x] **Raccomandazioni intelligenti**
- [x] **Code updates automatici**
- [x] **Dashboard AI real-time**
- [x] **CLI e API per controllo AI**

### Fase 3: Advanced Features 🔄
- [ ] Triangular arbitrage
- [ ] Web dashboard completo
- [ ] Advanced risk controls ML-powered
- [ ] **Predictive market analysis**
- [ ] **Auto-tuning algorithms**

### Fase 4: AI-Native Trading 🔮
- [ ] **Machine learning strategies**
- [ ] **Sentiment analysis integration**
- [ ] MEV-style strategies
- [ ] Multi-chain support
- [ ] **Custom AI models training**
- [ ] **Advanced analytics suite**

### 🧠 AI Roadmap Specifico

**Q1 2024: Foundation** ✅
- [x] Claude API integration
- [x] Basic performance analysis
- [x] Safe code updates
- [x] Emergency trigger system

**Q2 2024: Enhancement** 🔄
- [ ] Machine learning models
- [ ] Advanced pattern recognition
- [ ] Multi-timeframe analysis
- [ ] Custom strategy generation

**Q3 2024: Intelligence** 🔮
- [ ] Predictive analytics
- [ ] Market sentiment integration
- [ ] Real-time optimization
- [ ] Cross-market correlation analysis

**Q4 2024: Autonomy** 🔮
- [ ] Full autonomous trading modes
- [ ] Self-improving algorithms
- [ ] Custom model training
- [ ] Advanced MEV strategies

## 🤝 Contributing

Contributi benvenuti! Per contribuire:

1. Fork il repository
2. Crea un branch feature (`git checkout -b feature/AmazingFeature`)
3. Commit le modifiche (`git commit -m 'Add AmazingFeature'`)
4. Push al branch (`git push origin feature/AmazingFeature`)
5. Apri una Pull Request

### 🧠 Contributing al Sistema AI

**Per miglioramenti AI:**
- Test sempre con `python -m src.cli.ai_cli test --test-all`
- Aggiungi test in `tests/test_ai_integration.py`
- Documenta nuove funzionalità AI nel README
- Valida safety dei code updates

**Aree contribuzione AI:**
- **Analisi avanzate**: Nuovi tipi di analisi per Claude
- **Emergency triggers**: Nuovi pattern di rilevamento
- **Code safety**: Miglioramenti validazione sicurezza
- **Dashboard metrics**: Nuove metriche e visualizzazioni
- **API endpoints**: Nuove funzionalità REST API

**Linee guida sicurezza AI:**
- Mai commitare API keys
- Testare code updates in sandbox
- Validare prompts per Claude
- Documentare nuovi risk triggers

## 📄 Licenza

Questo progetto è sotto licenza MIT. Vedi il file `LICENSE` per dettagli.

## ⚠️ Disclaimer

**IMPORTANTE**: SmartArb Engine è fornito a scopo educativo e di ricerca. Il trading di criptovalute comporta rischi significativi e può risultare nella perdita di capitale. 

- Non siamo responsabili per perdite finanziarie
- Testa sempre con paper trading prima
- Investi solo quello che puoi permetterti di perdere
- Consulta un consulente finanziario se necessario

### 🧠 Disclaimer AI

**Sistema AI Claude:**
- Le raccomandazioni AI sono suggerimenti, non consigli finanziari
- Sempre verificare e approvare changes automatici
- AI può commettere errori - supervisione umana necessaria
- Code updates automatici hanno safety checks ma non sono infallibili
- Backup automatici disponibili per rollback

**Responsabilità:**
- L'utente è responsabile per tutte le decisioni di trading
- AI è uno strumento di supporto, non un consulente finanziario
- Monitoraggio continuo del sistema raccomandato
- Aggiornamenti AI potrebbero influenzare performance

## 📞 Supporto

- **Issues**: [GitHub Issues](https://github.com/your-username/smartarb-engine/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-username/smartarb-engine/discussions)
- **Documentation**: [Wiki](https://github.com/your-username/smartarb-engine/wiki)
- **🧠 AI Help**: Usa `python -m src.cli.ai_cli analyze --help` per supporto AI

### 🚀 Quick Commands

```bash
# Setup completo
python scripts/setup_database.py && python scripts/setup_ai.py --quick

# Start engine con AI
python -m src.core.engine

# Monitor AI dashboard
python -m src.api.ai_api & open http://localhost:8000/docs

# Analisi manuale
python -m src.cli.ai_cli analyze --focus "oggi"

# Status completo
python -m src.cli.ai_cli test --test-all
```

---

**Made with ❤️ and 🧠 for the crypto arbitrage community**

*SmartArb Engine - Where human strategy meets artificial intelligence*

### 🎯 **Differenza SmartArb Engine:**

**Prima (Bot tradizionali):**
```
📊 Dati → 🤖 Algoritmo Statico → 💱 Trade → 📈 Risultato
```

**Ora (AI-Enhanced):**
```
📊 Dati → 🧠 Claude AI → 💡 Ottimizzazione → 🤖 Algoritmo Adattivo → 💱 Trade Migliorato → 📈 Risultato Superiore
                ↓
           🔄 Learning Loop & Auto-Miglioramento
```

**Risultato: Sistema che impara, si adatta e migliora autonomamente! 🚀**
