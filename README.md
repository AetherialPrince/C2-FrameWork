# C2 Framework

A modular command-and-control framework designed for red team operations, adversary simulation, and security research.

## Overview
This framework consists of:
- C2 Server
- Operator Console
- Agent/Implant
- Module system

Supports encrypted communications, tasking, file transfer, and remote command execution.

## Features
- Encrypted C2 communications
- Session management
- Command execution
- File upload/download
- Modular plugin architecture
- Cross-platform agents

## Requirements
Python 3.10+

## Installation
git clone https://github.com/AetherialPrince/c2-framework.git
cd c2-framework
pip install -r requirements.txt

## Running Server
python server.py

## Running Agent
python agent.py

## Modules
Modules are located in /modules and automatically loaded.

## Legal Notice
For authorized security testing and educational use only.

## License
GNU GPLv3