#!/bin/bash
# Startup script for Render deployment

# Install dependencies
pip install -r requirements.txt

# Start the Flask-SocketIO application
python main.py
