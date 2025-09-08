#!/usr/bin/env python3
"""
SmartArb Engine Setup Script
Professional setup configuration for SmartArb cryptocurrency arbitrage trading bot
"""

from setuptools import setup, find_packages
import os
import sys
from pathlib import Path

# Read version from __init__.py
version_file = Path(__file__).parent / "src" / "__init__.py"
version = "1.0.0"  # Default version

if version_file.exists():
    with open(version_file, 'r') as f:
        for line in f:
            if line.startswith('__version__'):
                version = line.split('=')[1].strip().strip('"').strip("'")
                break

# Read long description from README
readme_file = Path(__file__).parent / "README.md"
long_description = ""
if readme_file.exists():
    with open(readme_file, 'r', encoding='utf-8') as f:
        long_description = f.read()

# Read requirements
def read_requirements(filename):
    """Read requirements from file"""
    req_file = Path(__file__).parent / filename
    if req_file.exists():
        with open(req_file, 'r') as f:
            return [line.strip() for line in f 
                   if line.strip() and not line.startswith('#')]
    return []

# Core requirements
install_requires = read_requirements('requirements.txt')

# Development requirements
dev_requires = [
    'pytest>=8.3.3',
    'pytest-asyncio>=0.24.0',
    'pytest-mock>=3.14.0',
    'pytest-cov>=5.0.0',
    'black>=24.10.0',
    'flake8>=7.1.1',
    'mypy>=1.12.0',
    'pre-commit>=3.5.0',
    'sphinx>=7.1.0',
    'sphinx-rtd-theme>=1.3.0',
]

# Raspberry Pi specific requirements
rpi_requires = [
    'RPi.GPIO>=0.7.1; sys_platform == "linux"',
    'picamera>=1.13; sys_platform == "linux"',
    'adafruit-circuitpython-dht>=3.7.0; sys_platform == "linux"',
]

# AI features requirements
ai_requires = [
    'anthropic>=0.39.0',
    'openai>=1.0.0',
    'scikit-learn>=1.5.2',
    'lightgbm>=4.5.0',
    'matplotlib>=3.9.2',
    'seaborn>=0.13.2',
    'plotly>=5.24.1',
]

# Production requirements
prod_requires = [
    'gunicorn>=21.2.0',
    'supervisor>=4.2.5',
    'prometheus-client>=0.19.0',
    'grafana-api>=1.0.3',
]

# All extras
all_requires = dev_requires + rpi_requires + ai_requires + prod_requires

setup(
    name="smartarb-engine",
    version=version,
    author="SmartArb Development Team",
    author_email="info@smartarb.dev",
    description="Professional cryptocurrency arbitrage trading bot optimized for Raspberry Pi",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/smartarb/smartarb-engine",
    project_urls={
        "Bug Tracker": "https://github.com/smartarb/smartarb-engine/issues",
        "Documentation": "https://docs.smartarb.dev",
        "Source Code": "https://github.com/smartarb/smartarb-engine",
        "Changelog": "https://github.com/smartarb/smartarb-engine/blob/main/CHANGELOG.md",
    },
    
    # Package configuration
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    include_package_data=True,
    
    # Requirements
    python_requires=">=3.11",
    install_requires=install_requires,
    extras_require={
        'dev': dev_requires,
        'rpi': rpi_requires,
        'ai': ai_requires,
        'prod': prod_requires,
        'all': all_requires,
    },
    
    # Entry points
    entry_points={
        'console_scripts': [
            'smartarb=src.cli.main:main',
            'smartarb-engine=src.core.engine:main',
            'smartarb-setup=scripts.setup_system:main',
            'smartarb-monitor=src.monitoring.dashboard:main',
        ],
    },
    
    # Package data
    package_data={
        'smartarb': [
            'config/*.yaml',
            'config/*.yml',
            'config/*.json',
            'templates/*.html',
            'static/css/*.css',
            'static/js/*.js',
            'static/images/*',
        ],
    },
    
    # Classification
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Financial and Insurance Industry",
        "Intended Audience :: Developers",
        "Topic :: Office/Business :: Financial :: Investment",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
        "Environment :: Console",
        "Environment :: Web Environment",
        "Natural Language :: English",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Framework :: AsyncIO",
    ],
    
    # Keywords
    keywords=[
        "cryptocurrency", "arbitrage", "trading", "bot", "bitcoin", 
        "ethereum", "raspberry-pi", "ccxt", "exchanges", "kraken", 
        "bybit", "mexc", "ai", "claude", "automation", "fintech"
    ],
    
    # License
    license="MIT",
    
    # Zip safe
    zip_safe=False,
    
    # Options
    options={
        'build_scripts': {
            'executable': '/usr/bin/python3',
        },
    },
    
    # Data files for system installation
    data_files=[
        # Configuration files
        ('etc/smartarb', [
            'config/settings.yaml',
            'config/exchanges.yaml', 
            'config/strategies.yaml',
        ]),
        
        # Systemd service files (Linux)
        ('lib/systemd/system', [
            'scripts/systemd/smartarb.service',
        ]) if sys.platform.startswith('linux') else [],
        
        # Log rotation (Linux)
        ('etc/logrotate.d', [
            'scripts/logrotate/smartarb',
        ]) if sys.platform.startswith('linux') else [],
        
        # Documentation
        ('share/doc/smartarb', [
            'README.md',
            'CHANGELOG.md',
            'LICENSE',
        ]),
        
        # Example scripts
        ('share/smartarb/examples', [
            'examples/basic_arbitrage.py',
            'examples/custom_strategy.py',
            'examples/risk_management.py',
        ]),
    ],
)

# Post-installation setup
def post_install():
    """Post-installation setup tasks"""
    import subprocess
    import os
    
    print("🚀 SmartArb Engine installation completed!")
    print("")
    print("Next steps:")
    print("1. Copy configuration template:")
    print("   cp /etc/smartarb/settings.yaml config/")
    print("")
    print("2. Configure your API keys:")
    print("   nano config/settings.yaml")
    print("")
    print("3. Set up environment variables:")
    print("   cp .env.example .env")
    print("   nano .env")
    print("")
    print("4. Initialize database (if using PostgreSQL):")
    print("   smartarb-setup database")
    print("")
    print("5. Start the engine:")
    print("   smartarb start")
    print("")
    print("6. Monitor logs:")
    print("   smartarb logs --follow")
    print("")
    print("For detailed documentation, visit: https://docs.smartarb.dev")
    print("")
    
    # Create directories
    dirs_to_create = [
        'logs',
        'data', 
        'backups',
        'config',
    ]
    
    for directory in dirs_to_create:
        os.makedirs(directory, exist_ok=True)
        print(f"✅ Created directory: {directory}")
    
    # Set permissions (Linux/Mac)
    if sys.platform != 'win32':
        try:
            subprocess.run(['chmod', '+x', 'scripts/setup_system.py'], check=False)
            subprocess.run(['chmod', '+x', 'scripts/setup_database.py'], check=False)
            print("✅ Set executable permissions on scripts")
        except:
            pass
    
    print("")
    print("🎉 Setup completed! SmartArb Engine is ready to use.")

# Run post-install if this is being installed
if __name__ == "__main__" and "install" in sys.argv:
    try:
        post_install()
    except Exception as e:
        print(f"⚠️  Post-installation setup encountered an issue: {e}")
        print("You can run the setup manually later.")
