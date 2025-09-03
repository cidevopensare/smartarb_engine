#!/usr/bin/env python3
"""
SmartArb Engine - Test Completo Sistema
Verifica che tutti i componenti funzionino correttamente
"""

import requests
import subprocess
import time
import json
import os
import sys
from datetime import datetime

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header(text):
    print(f"\n{Colors.CYAN}{Colors.BOLD}{'='*60}{Colors.END}")
    print(f"{Colors.CYAN}{Colors.BOLD} {text:^56} {Colors.END}")
    print(f"{Colors.CYAN}{Colors.BOLD}{'='*60}{Colors.END}\n")

def print_success(text):
    print(f"{Colors.GREEN}✅ {text}{Colors.END}")

def print_error(text):
    print(f"{Colors.RED}❌ {text}{Colors.END}")

def print_warning(text):
    print(f"{Colors.YELLOW}⚠️ {text}{Colors.END}")

def print_info(text):
    print(f"{Colors.BLUE}ℹ️ {text}{Colors.END}")

def check_file_exists(filepath, description):
    """Verifica se un file esiste"""
    if os.path.exists(filepath):
        print_success(f"{description}: {filepath}")
        return True
    else:
        print_error(f"{description}: {filepath} NOT FOUND")
        return False

def test_telegram():
    """Test delle notifiche Telegram"""
    print_header("TEST TELEGRAM NOTIFICATIONS")
    
    # 1. Controlla file .env
    if not check_file_exists('.env', 'Environment file'):
        return False
    
    # 2. Controlla variabili Telegram
    try:
        with open('.env', 'r') as f:
            env_content = f.read()
        
        has_token = 'TELEGRAM_BOT_TOKEN' in env_content
        has_chat = 'TELEGRAM_CHAT_ID' in env_content
        has_enabled = 'TELEGRAM_ENABLED=true' in env_content
        
        if has_token:
            print_success("Bot token found in .env")
        else:
            print_error("Bot token missing in .env")
        
        if has_chat:
            print_success("Chat ID found in .env")
        else:
            print_error("Chat ID missing in .env")
            
        if has_enabled:
            print_success("Telegram enabled in .env")
        else:
            print_warning("Telegram not explicitly enabled")
            
    except Exception as e:
        print_error(f"Error reading .env: {e}")
        return False
    
    # 3. Test diretto Telegram
    if check_file_exists('test_telegram_direct.py', 'Telegram test script'):
        try:
            print_info("Running Telegram test...")
            result = subprocess.run(['python3', 'test_telegram_direct.py'], 
                                  capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0 and "SUCCESS" in result.stdout:
                print_success("Telegram test PASSED!")
                return True
            else:
                print_error("Telegram test FAILED!")
                print(f"Output: {result.stdout}")
                print(f"Error: {result.stderr}")
                return False
        except subprocess.TimeoutExpired:
            print_error("Telegram test timed out")
            return False
        except Exception as e:
            print_error(f"Error running Telegram test: {e}")
            return False
    
    return False

def test_dashboard():
    """Test della dashboard web"""
    print_header("TEST WEB DASHBOARD")
    
    # 1. Test connessione HTTP
    try:
        print_info("Testing dashboard connection...")
        response = requests.get('http://localhost:8001', timeout=10)
        
        if response.status_code == 200:
            print_success("Dashboard HTTP connection OK")
            
            # Controlla se è HTML valido
            if '<html>' in response.text.lower() or '<!doctype html>' in response.text.lower():
                print_success("Valid HTML dashboard detected")
            else:
                print_warning("Dashboard response doesn't look like HTML")
                
        else:
            print_error(f"Dashboard returned status code: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print_error("Cannot connect to dashboard on port 8001")
        print_info("Suggestion: Make sure dashboard server is running")
        return False
    except requests.exceptions.Timeout:
        print_error("Dashboard connection timed out")
        return False
    except Exception as e:
        print_error(f"Dashboard connection error: {e}")
        return False
    
    # 2. Test API Metrics
    try:
        print_info("Testing metrics API...")
        response = requests.get('http://localhost:8001/api/metrics', timeout=10)
        
        if response.status_code == 200:
            print_success("Metrics API responding")
            
            # Parse JSON
            try:
                metrics = response.json()
                print_info(f"Metrics keys: {list(metrics.keys())}")
                
                # Verifica metriche chiave
                expected_keys = ['trades_executed', 'success_rate', 'total_profit', 'memory_usage', 'cpu_usage']
                missing_keys = [key for key in expected_keys if key not in metrics]
                
                if not missing_keys:
                    print_success("All expected metrics present")
                else:
                    print_warning(f"Missing metrics: {missing_keys}")
                    
                return True
                
            except json.JSONDecodeError:
                print_error("Metrics API returned invalid JSON")
                return False
                
        else:
            print_error(f"Metrics API returned status: {response.status_code}")
            return False
            
    except Exception as e:
        print_error(f"Metrics API error: {e}")
        return False

def test_engine():
    """Test dell'engine di trading"""
    print_header("TEST TRADING ENGINE")
    
    # 1. Controlla file engine
    engine_files = [
        'src/core/engine.py',
        'src/core/engine_with_dashboard.py'
    ]
    
    engine_found = False
    for engine_file in engine_files:
        if check_file_exists(engine_file, f'Engine file'):
            engine_found = True
            break
    
    if not engine_found:
        print_error("No engine files found!")
        return False
    
    # 2. Controlla se l'engine è in esecuzione
    try:
        result = subprocess.run(['pgrep', '-f', 'src.core.engine'], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            pids = result.stdout.strip().split('\n')
            print_success(f"Engine running with PID(s): {', '.join(pids)}")
        else:
            print_warning("Engine process not detected")
            
    except Exception as e:
        print_info(f"Cannot check engine process: {e}")
    
    # 3. Controlla file di log
    log_files = ['logs/engine.log', 'logs/smartarb.log']
    for log_file in log_files:
        if check_file_exists(log_file, 'Engine log file'):
            try:
                with open(log_file, 'r') as f:
                    log_content = f.read()
                
                # Cerca indicatori di funzionamento
                if 'SmartArb Engine' in log_content:
                    print_success(f"Engine activity detected in {log_file}")
                elif 'ERROR' in log_content:
                    print_warning(f"Errors detected in {log_file}")
                else:
                    print_info(f"Log file {log_file} exists but is empty/unclear")
                    
            except Exception as e:
                print_warning(f"Cannot read log file {log_file}: {e}")
    
    return True

def test_system_resources():
    """Test delle risorse di sistema"""
    print_header("TEST SYSTEM RESOURCES")
    
    try:
        import psutil
        
        # CPU
        cpu_percent = psutil.cpu_percent(interval=1)
        if cpu_percent < 80:
            print_success(f"CPU usage OK: {cpu_percent}%")
        else:
            print_warning(f"High CPU usage: {cpu_percent}%")
        
        # Memory
        memory = psutil.virtual_memory()
        if memory.percent < 80:
            print_success(f"Memory usage OK: {memory.percent}%")
        else:
            print_warning(f"High memory usage: {memory.percent}%")
        
        # Disk
        disk = psutil.disk_usage('/')
        if disk.percent < 90:
            print_success(f"Disk usage OK: {disk.percent}%")
        else:
            print_warning(f"High disk usage: {disk.percent}%")
            
        # Network (basic check)
        try:
            response = requests.get('https://api.github.com', timeout=5)
            if response.status_code == 200:
                print_success("Internet connection OK")
            else:
                print_warning("Internet connection issues")
        except:
            print_warning("Cannot verify internet connection")
            
        return True
        
    except ImportError:
        print_warning("psutil not available for detailed system check")
        return True
    except Exception as e:
        print_error(f"System resource check failed: {e}")
        return False

def test_ports():
    """Test delle porte utilizzate"""
    print_header("TEST PORT USAGE")
    
    ports_to_check = [8000, 8001, 3000]
    
    for port in ports_to_check:
        try:
            response = requests.get(f'http://localhost:{port}', timeout=3)
            print_success(f"Port {port}: Service responding")
        except requests.exceptions.ConnectionError:
            print_info(f"Port {port}: No service")
        except requests.exceptions.Timeout:
            print_warning(f"Port {port}: Service timeout")
        except Exception as e:
            print_info(f"Port {port}: {e}")
    
    return True

def main():
    """Funzione principale del test"""
    print(f"{Colors.MAGENTA}{Colors.BOLD}")
    print("🚀 SmartArb Engine - Test Completo Sistema")
    print("==========================================")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{Colors.END}")
    
    tests = [
        ("System Resources", test_system_resources),
        ("Port Usage", test_ports),
        ("Trading Engine", test_engine),
        ("Web Dashboard", test_dashboard),
        ("Telegram Notifications", test_telegram),
    ]
    
    results = {}
    
    for test_name, test_function in tests:
        try:
            result = test_function()
            results[test_name] = result
        except Exception as e:
            print_error(f"Test {test_name} crashed: {e}")
            results[test_name] = False
    
    # Risultati finali
    print_header("RISULTATI FINALI")
    
    for test_name, result in results.items():
        if result:
            print_success(f"{test_name}: PASSED")
        else:
            print_error(f"{test_name}: FAILED")
    
    passed = sum(results.values())
    total = len(results)
    
    print(f"\n{Colors.BOLD}Score: {passed}/{total} tests passed{Colors.END}")
    
    if passed == total:
        print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 ALL TESTS PASSED! SmartArb Engine is ready!{Colors.END}")
        return 0
    elif passed >= total * 0.7:
        print(f"\n{Colors.YELLOW}{Colors.BOLD}⚠️ Most tests passed, but some issues found{Colors.END}")
        return 1
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}❌ Multiple issues found, review required{Colors.END}")
        return 2

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Test interrupted by user{Colors.END}")
        sys.exit(130)
