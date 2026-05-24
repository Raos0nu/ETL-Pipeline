#!/bin/bash

echo "========================================"
echo "DataFlow Studio — Setup"
echo "========================================"
echo ""

echo "[1/4] Installing Python dependencies..."
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "Error: Failed to install Python dependencies"
    exit 1
fi
echo "Python dependencies installed!"
echo ""

echo "[2/4] Setting up frontend..."
cd frontend || { echo "Error: frontend directory not found"; exit 1; }

echo "[3/4] Installing Node.js dependencies..."
npm install
if [ $? -ne 0 ]; then
    echo "Error: Failed to install Node.js dependencies"
    exit 1
fi
echo "Node.js dependencies installed!"
echo ""

echo "[4/4] Building React application..."
npm run build
if [ $? -ne 0 ]; then
    echo "Error: Failed to build React application"
    exit 1
fi
echo "React application built!"
echo ""

cd ..

echo "========================================"
echo "Setup Complete!"
echo "========================================"
echo ""
echo "To start the application, run:"
echo "  python api/index.py"
echo ""
echo "Then open your browser to:"
echo "  http://localhost:5000"
echo ""
