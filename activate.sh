#!/bin/bash
# Activate the virtual environment for this project
source venv/bin/activate
echo "Virtual environment activated. Use 'deactivate' to exit."
echo "Python version: $(python3 --version)"
echo "Python location: $(which python3)"
echo ""
echo "Available commands:"
echo "  python3 delta_parser.py  - Parse DELTA files and create database"
echo "  python3 test_parser.py   - Run comprehensive tests"