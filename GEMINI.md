# Gemini Code Assistant Context

This file provides context to the Gemini code assistant to help it understand the project and provide more relevant and accurate assistance.

## 1. Project Overview

This project is a real-time audio and MIDI processing system for live music performance. The core of the system is a Python audio/MIDI engine that runs on a Raspberry Pi. The system is controlled via a Svelte/TypeScript PWA, which can be accessed from a Mac or an iPhone to control the engine remotely.

### Key Features:
*   **Backend:** Python-based audio engine using `mido` for MIDI and `simpleaudio` for playback.
*   **Frontend:** Svelte/TypeScript PWA for the user interface.
*   **Real-time Communication:** WebSockets are used for low-latency communication between the frontend and backend.
*   **Deployment:** A one-click deployment system using Git and a shell script, triggered from the web UI.

## 2. Tech Stack

*   **Git Repository:** `https://github.com/benjarlett/rexloop.git`

### Backend (Raspberry Pi)
*   **Language:** Python 3.9
*   **Key Libraries:** `websockets`, `mido`, `python-rtmidi`, `simpleaudio`
*   **Deployment:** `git`, `bash` script (`deploy.sh`)
*   **Service Management:** `systemd`

### Frontend (Web)
*   **Framework:** Svelte
*   **Language:** TypeScript
*   **Build Tool:** Vite
*   **UI:** PWA for cross-platform compatibility.

### Hardware
*   **Audio/MIDI Engine:** Raspberry Pi 3 Model B Rev 1.2
*   **Development Machine:** Mac
*   **Controller:** iPhone or Mac via web browser
*   **Audio/MIDI Interface:** Pisound

## 3. Project Structure

```
/Users/ben/Apps/rexloop
├── backend/
│   ├── engine.py         # Main Python audio/MIDI engine
│   ├── requirements.txt  # Python dependencies
│   ├── loops/            # Directory for WAV audio loops
│   │   └── loop.wav
│   ├── deploy.sh         # Deployment script for the Pi
│   └── venv/             # Python virtual environment (on Pi)
├── frontend/
│   ├── src/
│   │   └── App.svelte    # Main Svelte component
│   ├── package.json      # Node.js dependencies
│   └── ...
└── GEMINI.md             # This file
```

## 4. Development & Deployment Workflow

### A. Local Development (on Mac)

1.  **Terminal 1 (Backend):**
    ```bash
    cd backend
    # First time setup:
    # python3 -m venv venv
    # source venv/bin/activate
    # pip3 install -r requirements.txt

    # Run engine (use --midi-port if you have a local MIDI device)
    python3 engine.py
    ```
2.  **Terminal 2 (Frontend):**
    ```bash
    cd frontend
    # First time setup:
    # npm install

    npm run dev
    ```

### B. Deploying to Raspberry Pi

This is a one-click process from the web UI.

1.  **Make Changes:** Edit code on the Mac.
2.  **Commit & Push:**
    ```bash
    git add .
    git commit -m "Your changes"
    git push origin main
    ```
3.  **Deploy:** Open the web UI, and click the **"Deploy Latest Code"** button.

### C. Initial Pi Setup (One-Time Only)

1.  **Clone Repo:**
    ```bash
    ssh patch@patchbox.local
    git clone https://github.com/benjarlett/rexloop.git ~/rexloop
    ```
2.  **Create & Activate Venv:**
    ```bash
    cd ~/rexloop/backend
    python3 -m venv venv
    source venv/bin/activate
    pip3 install -r requirements.txt
    ```
3.  **Make Deploy Script Executable:**
    ```bash
    chmod +x deploy.sh
    ```
4.  **Create and Start Systemd Service:**
    *   `sudo nano /etc/systemd/system/rexloop-backend.service`
    *   Paste in the service configuration (see previous turn).
    *   `sudo systemctl enable --now rexloop-backend.service`

## 5. Coding Conventions

*   **Python:** Follow PEP 8. Use type hints.
*   **TypeScript/Svelte:** Follow standard SvelteKit/Vite conventions. Use Prettier for formatting.
