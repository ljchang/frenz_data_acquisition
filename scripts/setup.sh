#!/bin/bash
# Quick setup script for FRENZ Data Acquisition System

echo "🧠 FRENZ Data Acquisition System - Setup"
echo "========================================"

# Check if UV is installed
if ! command -v uv &> /dev/null; then
    echo "⚠️  UV not found. Installing UV..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    echo "✅ UV installed"
else
    echo "✅ UV is already installed"
fi

# Create virtual environment
echo "📦 Creating virtual environment..."
uv venv

# Install dependencies
echo "📦 Installing dependencies..."
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" || "$OSTYPE" == "win32" ]]; then
    # Windows
    .venv/Scripts/pip install -e .
else
    # Unix/Linux/Mac
    .venv/bin/pip install -e .
fi

# Create directories
echo "📁 Creating required directories..."
mkdir -p data logs

# Check for .env file
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env with your FRENZ device credentials"
else
    echo "✅ .env file already exists"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env with your FRENZ credentials"
echo "2. Activate the virtual environment:"
echo "   source .venv/bin/activate  # On Windows: .venv\\Scripts\\activate"
echo "3. Run the quick start verification:"
echo "   python quick_start.py"
echo "4. Launch the dashboard:"
echo "   marimo run dashboard.py"
echo ""
echo "📚 See README.md for detailed documentation"