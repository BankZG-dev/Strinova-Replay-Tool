# ⚡ Strinova Replay Tool

A tool to inject downloaded replay files into **Strinova** and **CalabiYau** so you can watch them in-game.

## ⬇️ Download

Go to the [**Releases**](../../releases/latest) page and download `StrinovaReplayTool.exe`.  
No installation needed — just run the `.exe`.

## How It Works

The game can only load replays it recorded itself. This tool swaps a downloaded replay's content into one of your own recorded files so the game accepts it.

1. **Record a short dummy replay** in-game (just enter a match and leave)
2. Open the tool and **select that dummy file** from the list (Step 1)
3. **Browse** to the `.dem` file you downloaded (Step 2)
4. Click **Swap** — done, open the game and watch the replay

## Features

- Supports both **Strinova** and **CalabiYau**
- Auto-detects your Demos folder
- Backup & restore before every swap
- Smooth dark UI

## Building from Source

```bash
git clone https://github.com/YOUR_USERNAME/StrinovaReplayTool.git
cd StrinovaReplayTool
pip install -r requirements.txt
python src/StrinovaReplayTool_v3.py
```

## Requirements (source only)

- Python 3.10+
- Windows (the game only runs on Windows)