# WJX Auto Fill System

This project provides a GUI tool for questionnaire parsing and auto-filling.

## Entry Point

- Main app: `wjx_auto_fill.py`

## Project Layout

- `wjx_auto_fill.py`: main desktop app (Tkinter + Selenium)
- `core/`: parsing, filling, AI-related modules
- `ui/`: UI components
- `config/`: config and logging modules
- `scripts/`: setup, doctor, and run scripts
- `requirements.txt`: Python dependencies

## Quick Start (Windows PowerShell)

1. Setup environment:

```powershell
.\scripts\setup_env.ps1
```

2. Run diagnostics:

```powershell
.\scripts\doctor.ps1
```

3. Start app:

```powershell
.\scripts\run.ps1
```

## VS Code Notes

- Workspace interpreter is configured in `.vscode/settings.json`:
  - `python.defaultInterpreterPath = ${workspaceFolder}\.venv\Scripts\python.exe`
- If Pylance still shows stale diagnostics:
  - close deleted file tabs
  - run `Developer: Reload Window`
  - ensure `.venv` exists by running `.\scripts\setup_env.ps1`

## Common Issues

- `reportMissingImports` in Pylance:
  - Root cause: dependencies not installed in selected interpreter.
  - Fix: run setup script and re-select interpreter.

- `py` command not found:
  - Install Python 3.10+ from python.org and enable `Add python.exe to PATH`.

