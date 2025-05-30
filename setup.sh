#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Setting up development environment for Daily Intelligence Report...${NC}"

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed or not in PATH${NC}"
    echo "Please install Python 3.11+ before continuing"
    exit 1
fi

# Check Python version (need 3.11+)
PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PY_VERSION_NUM=$(echo $PY_VERSION | sed 's/\.//')

if [ "$PY_VERSION_NUM" -lt 311 ]; then
    echo -e "${RED}Error: Python 3.11+ is required (found $PY_VERSION)${NC}"
    echo "Please install Python 3.11 or higher"
    exit 1
fi

echo -e "${GREEN}Found Python $PY_VERSION${NC}"

# Check if Poetry is installed
if ! command -v poetry &> /dev/null; then
    echo -e "${YELLOW}Poetry not found. Installing...${NC}"
    curl -sSL https://install.python-poetry.org | python3 -
    
    # Add Poetry to PATH for the current session
    export PATH="$HOME/.local/bin:$PATH"
    
    # Check if installation succeeded
    if ! command -v poetry &> /dev/null; then
        echo -e "${RED}Failed to install Poetry. Please install it manually:${NC}"
        echo "https://python-poetry.org/docs/#installation"
        echo "Then run this script again."
        exit 1
    fi
fi

echo -e "${GREEN}Poetry is installed${NC}"

# Check if pyproject.toml exists, if not create it
if [ ! -f "pyproject.toml" ]; then
    echo -e "${YELLOW}Creating pyproject.toml...${NC}"
    
    # Initialize Poetry project
    poetry init --name "daily-intelligence-report" \
                --description "Personalized daily intelligence report system" \
                --author "Your Name <your.email@example.com>" \
                --python ">=3.11.0 <4.0.0" \
                --no-interaction
                
    echo -e "${GREEN}Created pyproject.toml${NC}"
else
    echo -e "${GREEN}Found existing pyproject.toml${NC}"
fi

# Add main dependencies
echo -e "${YELLOW}Adding main dependencies...${NC}"
poetry add httpx tenacity feedparser sqlite-utils scikit-learn jinja2 pydantic pyyaml

# Add development dependencies
echo -e "${YELLOW}Adding development dependencies...${NC}"
poetry add --group dev pytest pytest-cov mypy ruff black 

# Create project directory structure
echo -e "${YELLOW}Creating project directory structure...${NC}"
mkdir -p src/{connectors,models,pipeline,render,api} tests

# Configure Poetry to create virtual environment in project directory
echo -e "${YELLOW}Configuring Poetry to create virtual environment in project directory...${NC}"
poetry config virtualenvs.in-project true

# Install all dependencies and create virtual environment
echo -e "${YELLOW}Installing dependencies and creating virtual environment...${NC}"
poetry install

echo -e "${GREEN}Development environment setup complete!${NC}"
echo -e "You can now activate the virtual environment with: ${YELLOW}poetry shell${NC}"
echo -e "Or run commands within the environment with: ${YELLOW}poetry run <command>${NC}"