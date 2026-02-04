# AlterEcho

> **Gemini 3.0 Hackathon 2026 Submission**

**AlterEcho** is a digital persona system that allows you to "resurrect" or clone digital personalities from chat history and voice samples. By analyzing linguistic patterns from Instagram/Discord logs and cloning voice profiles using WaveSpeed, AlterEcho creates a hyper-realistic AI companion that speaks and texts exactly like the original person.

![AlterEcho Interface](public/vite.svg)

## Features

-   **Linguistic Style Analysis**: Mathematically deconstructs chat logs to replicate vocabulary, sarcasm patterns, and emotional tone.
-   **Voice Cloning**: Integrates WaveSpeed MiniMax 2.6 Turbo for high-fidelity voice synthesis.
-   **Multi-Source Import**: Supports Instagram (`.json`) and Discord (`.zip`) chat exports.
-   **Hybrid Memory**: Combines static style guides with RAG (Retrieval Augmented Generation) for accurate long-term memory.
-   **Local-First**: Data stays on your machine (`backend/data/`).

---

## Local Setup Guide

Follow these steps to run AlterEcho locally.

### Prerequisites
-   **Python 3.10+**
-   **Node.js 18+** (for the frontend)
-   **Gemini API Key** (from Google AI Studio)
-   **WaveSpeed API Key** (for voice features)

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/alterecho.git
cd alterecho
```

### 2. Backend Setup
The backend runs on Flask and handles all AI processing.

1.  Navigate to the backend folder:
    ```bash
    cd backend
    ```
2.  Install python dependencies:
    ```bash
    pip install -r requirements.txt
    ```
3.  Set up your environment variables:
    *   Create a `.env` file in the **root** folder (one level up from `backend/`).
    *   Add your keys:
        ```ini
        GEMINI_API_KEY=your_gemini_key_here
        WAVESPEED_API_KEY=your_wavespeed_key_here
        ```
4.  Run the server:
    ```bash
    python api.py
    ```
    *The server will start on `http://localhost:5000`.*

### 3. Frontend Setup
The frontend is a modern React application built with Vite.

1.  Open a new terminal and navigate to the root folder:
    ```bash
    cd alterecho
    ```
2.  Install Node dependencies:
    ```bash
    npm install
    ```
3.  Start the development server:
    ```bash
    npm run dev
    ```
    *The app will be available at `http://localhost:5173`.*

---

## Tech Stack
-   **Frontend**: React, TailwindCSS v4, Radix UI, Framer Motion
-   **Backend**: Python, Flask
-   **AI**: Google Gemini 2.0 Flash (Logic/Text), WaveSpeed MiniMax (Voice)
