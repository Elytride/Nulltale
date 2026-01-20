# Nulltale - Project Overview

**Last Updated:** January 20, 2026  
**Description:** A browser-based psychological horror/thriller application that resurrects digital personalities from chat histories using AI.

---

## 🎯 Core Concept

Nulltale allows users to upload chat logs (WhatsApp, Instagram, Discord, LINE), train an AI model on a specific person's communication style, and then interact with a chatbot that mimics that person's personality, vocabulary, and mannerisms. The app also supports voice cloning to make conversations feel even more realistic.

---

## 🏗️ Architecture

### Technology Stack

**Frontend:**
- **Framework:** React 19.2.0 with Vite 7.2.4
- **Styling:** TailwindCSS 4.1.18 with custom dark theme
- **UI Components:** Radix UI primitives
- **Animations:** Framer Motion 12.23.26
- **Icons:** Lucide React
- **Fonts:** Inter (body), Space Grotesk (display)

**Backend:**
- **Framework:** Flask (consolidated from Flask + FastAPI)
- **AI/ML:** Google Gemini API (gemini-2.5-flash-lite)
- **Voice:** WaveSpeed MiniMax Speech 2.6 Turbo API
- **Embeddings:** Gemini text-embedding-004
- **Vector Search:** Cosine similarity (NumPy)

**Data Processing:**
- Python 3.10+
- JSON-based file storage
- Local file persistence for chats/sessions

---

## 📁 Project Structure

```
Nulltale/
├── backend/
│   ├── api.py                      # Main Flask server (925 lines)
│   ├── processor.py                # Chat file classification & preprocessing (647 lines)
│   ├── chatbot.py                  # PersonaChatbot with RAG (227 lines)
│   ├── style_summarizer.py         # Gemini-based style analysis (244 lines)
│   ├── context_embedder.py         # Generate embeddings for chunks (99 lines)
│   ├── context_retriever.py        # RAG retrieval system (176 lines)
│   ├── wavespeed_manager.py        # Voice cloning & TTS (647 lines)
│   ├── instagram_zip_processor.py  # Instagram ZIP extraction (14.5KB)
│   ├── discord_zip_processor.py    # Discord ZIP extraction (13.6KB)
│   ├── stt_manager.py              # Speech-to-text (3.6KB)
│   ├── secrets_manager.py          # Encrypted API key storage (4.9KB)
│   ├── requirements.txt            # Python dependencies
│   ├── uploads/                    # User-uploaded files (text/voice)
│   ├── preprocessed/               # Generated style summaries & embeddings
│   ├── chats/                      # Persisted chat sessions
│   ├── temp_zip/                   # Temporary ZIP extraction
│   └── .secrets/                   # Encrypted credentials
│
├── src/
│   ├── pages/
│   │   └── Home.jsx                # Main app page (126 lines)
│   ├── components/
│   │   ├── layout/
│   │   │   ├── ChatInterface.jsx   # Chat UI with voice calls (678 lines)
│   │   │   └── Sidebar.jsx         # Session management & FAQ (262 lines)
│   │   ├── modals/
│   │   │   ├── FilesModal.jsx      # File upload & AI refresh (781 lines)
│   │   │   └── SettingsModal.jsx   # Settings & API keys
│   │   └── ui/                     # Radix UI components (14 files)
│   ├── lib/
│   │   ├── api.js                  # API service layer (333 lines)
│   │   └── utils.js                # Utility functions
│   ├── App.jsx                     # Root component
│   ├── main.jsx                    # React entry point
│   └── index.css                   # TailwindCSS config & theme
│
├── public/                         # Static assets
├── .env                            # Environment variables (GEMINI_API_KEY)
├── .gitignore                      # Excludes uploads, chats, secrets
├── package.json                    # Node dependencies
├── vite.config.js                  # Vite configuration
└── README.md                       # Project description
```

---

## 🔄 Data Flow & Processing Pipeline

### Stage 1: File Upload & Classification

1. **Upload:** User uploads chat files (`.txt`, `.json`, `.zip`, `.html`)
2. **Classification:** `processor.py::classify_file()` detects format:
   - WhatsApp (text format with timestamps)
   - Instagram (JSON format)
   - InstagramHTML (HTML export)
   - Discord (via ZIP with `messages/index.json`)
   - LINE (text format with specific headers)
3. **Participant Extraction:** Identifies all participants in conversation
4. **Subject Selection:** User selects which person to train the AI on
5. **Duplicate Detection:** Content fingerprinting prevents duplicate uploads

### Stage 2: Data Preprocessing

**Style File Generation** (`processor.py::generate_style_file`):
- Includes ALL participants' messages (for conversation context)
- Filters to last 3 months of data (or 2 months if >30K lines)
- Removes timestamps but keeps sender names
- Max 5,000 lines per file
- Output: `{subject}_style_temp.txt`

**Context Chunks Generation** (`processor.py::generate_context_chunks`):
- Groups messages into conversation blocks (2-hour silence gap = new chunk)
- Includes ONLY subject's messages
- Filters out: links, emoji-only messages, filler words
- Enriches with metadata: date, partner, message count
- Output: `{subject}_context_chunks.json`

### Stage 3: AI Analysis

**Style Summary** (`style_summarizer.py::generate_style_summary`):
- Uses Gemini to analyze communication patterns:
  - Vocabulary & slang
  - Tone & energy profile
  - Humor & sarcasm patterns
  - Response patterns by message type
  - Emoji usage
  - Message structure
- Includes examples from original data
- Output: `{subject}_style_summary.txt`

**Embeddings Generation** (`context_embedder.py::generate_embeddings`):
- Embeds context chunks using Gemini `text-embedding-004`
- Task type: `retrieval_document`
- Batch size: 100 chunks per API call
- Output: `{subject}_embeddings.json` (includes vectors + metadata)

### Stage 4: Chat Interaction

**RAG Retrieval** (`context_retriever.py::ContextRetriever`):
- Embeds user query with `retrieval_query` task type
- Computes cosine similarity with all chunk embeddings
- Returns top-K most relevant conversation chunks

**Chatbot Response** (`chatbot.py::PersonaChatbot`):
- Combines:
  1. Style summary (personality guide)
  2. Retrieved context (relevant memories)
  3. Conversation history (recent turns)
- Sends to Gemini with detailed system prompt
- Maintains max 10 conversation turns in memory

**Voice Cloning** (`wavespeed_manager.py::WaveSpeedManager`):
- Clones voice from uploaded audio file
- Voice ID format: `NullTale{sessionId}{cleanName}`
- 7-day expiration from last use
- Streaming TTS with chunked audio delivery

---

## 🔌 API Endpoints

### Files
- `POST /api/files/{text|voice}` - Upload files
- `GET /api/files/{text|voice}` - List uploaded files
- `POST /api/files/{type}/{id}/subject` - Set subject for file
- `DELETE /api/files/{type}/{id}` - Delete file
- `POST /api/files/text/zip/select` - Select conversations from ZIP

### Processing
- `GET /api/refresh/ready` - Check if ready to refresh
- `POST /api/refresh` - Process files & generate AI memory (SSE stream)

### Sessions & Chat
- `GET /api/sessions` - List chat sessions
- `POST /api/sessions` - Create new session
- `DELETE /api/sessions/{id}` - Delete session
- `GET /api/messages/{id}` - Get session messages
- `POST /api/chat` - Send message (text-only)

### Voice
- `POST /api/call/stream` - Stream voice call (text + audio, SSE)
- `GET /api/voice/status/{id}` - Check voice clone status
- `POST /api/voice/clone/{id}` - Clone voice for session
- `GET /api/voices` - List available voices

### Settings
- `GET /api/settings` - Get settings
- `PUT /api/settings` - Update settings
- `GET /api/settings/wavespeed-key` - Check WaveSpeed key status
- `POST /api/settings/wavespeed-key` - Save WaveSpeed key
- `DELETE /api/settings/wavespeed-key` - Delete WaveSpeed key
- `POST /api/settings/wavespeed-key/test` - Test WaveSpeed key
- `POST /api/warmup` - Warmup models

---

## 🎨 Frontend Components

### Home.jsx
- Main app container
- Manages modal states (Files, Settings)
- Responsive sidebar (desktop fixed, mobile drawer)
- Landing screen with feature cards

### ChatInterface.jsx
- Message display with auto-scroll
- Text input with send button
- Voice call toggle (Phone icon)
- Speech recognition (Mic icon)
- Streaming audio playback with Web Audio API
- Call status indicators (listening, speaking, processing)

### Sidebar.jsx
- Session list with previews
- "New Chat" button
- FAQ collapsible section
- Settings & Files buttons
- Session deletion with confirmation

### FilesModal.jsx
- Tabbed interface (Text Data, Voice Data, Refresh AI)
- Drag-and-drop file upload
- ZIP conversation selection UI
- Subject picker for each file
- Voice upload staging (not immediate cloning)
- Refresh progress with SSE streaming
- Voice cloning status display

### SettingsModal.jsx
- Model version selection
- Temperature slider
- WaveSpeed API key management
- Key validation testing

---

## 🔐 Security & Data Management

### Secrets Storage
- WaveSpeed API keys encrypted with `cryptography.Fernet`
- Encryption key derived from machine-specific identifier
- Stored in `backend/.secrets/` (gitignored)

### Data Persistence
- **Sessions:** `backend/chats/sessions.json`
- **Message History:** `backend/chats/history_{session_id}.json`
- **Uploaded Files:** `backend/uploads/{text|voice}/`
- **Preprocessed Data:** `backend/preprocessed/`

### .gitignore Coverage
- All user data directories
- Environment files
- Python cache
- Credentials & secrets
- Debug/temp files

---

## 🎯 Key Features

### 1. Multi-Platform Chat Support
- WhatsApp (`.txt` export)
- Instagram (`.json` or `.zip` export)
- Discord (`.zip` export)
- LINE (`.txt` export)
- Instagram HTML (`.html` export)

### 2. Intelligent Preprocessing
- Duplicate detection via content fingerprinting
- Time-based filtering (last 3 months)
- Filler word removal
- Link & emoji-only message filtering
- Conversation chunking by silence gaps

### 3. Advanced AI Personality Replication
- Deep style analysis with Gemini
- RAG-based contextual memory
- Conversation history tracking
- Response pattern matching
- Humor & sarcasm detection

### 4. Voice Cloning & Calls
- WaveSpeed voice cloning from audio samples
- Real-time streaming TTS
- Speech recognition for hands-free chat
- Voice expiration management (7 days)

### 5. Session Management
- Multiple chat sessions per subject
- Persistent conversation history
- Session deletion with cleanup
- Preview generation

---

## 🚀 Workflow

### User Journey
1. **Upload Data:** Drag-and-drop chat files (Files Modal → Text Data tab)
2. **Select Subject:** Choose which person to train on for each file
3. **Refresh AI Memory:** Click "Refresh AI Memory" (processes all files)
4. **Create Session:** Click "New Chat" in sidebar
5. **Chat:** Type messages or use voice call feature
6. **(Optional) Clone Voice:** Upload audio sample in Voice Data tab, then refresh

### Processing Steps (Behind the Scenes)
1. File classification & participant extraction
2. Style file generation (conversation context)
3. Context chunks generation (subject messages only)
4. Gemini style analysis (personality summary)
5. Embedding generation (vector database)
6. Voice cloning (if audio provided)
7. Chatbot initialization with RAG retrieval

---

## 🐛 Known Issues & Considerations

### From Conversation History
1. **Backend Consolidation:** Previously had separate Flask (`api.py`) and FastAPI (`main.py`) servers. Now consolidated into single Flask server.
2. **Voice Feature 404s:** Fixed by merging all endpoints into `api.py`
3. **Discord Username Resolution:** Discord exports use IDs; conversion logic in `discord_zip_processor.py`
4. **LINE Subject Selection:** Enabled via participant extraction
5. **Instagram ZIP Handling:** Supports direct ZIP upload with conversation selection UI

### Current Limitations
- Voice clones expire after 7 days of inactivity
- Max 10,000 characters per TTS request
- Gemini API rate limits apply
- Local storage only (no cloud sync)
- Single-user application (no multi-tenancy)

---

## 🔧 Configuration

### Environment Variables (.env)
```
GEMINI_API_KEY=your_gemini_api_key_here
```

### Python Dependencies (requirements.txt)
- flask
- flask-cors
- python-dotenv
- google-generativeai
- numpy
- requests
- cryptography

### Node Dependencies (package.json)
- React 19.2.0
- Vite 7.2.4
- TailwindCSS 4.1.18
- Radix UI components
- Framer Motion
- Lucide React

---

## 🎨 Design System

### Color Palette (Dark Theme)
- **Background:** `hsl(240 10% 3.9%)` - Near black
- **Primary:** `hsl(263.4 70% 50.4%)` - Deep purple
- **Foreground:** `hsl(0 0% 98%)` - Off-white
- **Muted:** `hsl(240 5% 64.9%)` - Gray text
- **Border:** `hsl(240 3.7% 15.9%)` - Subtle borders

### Typography
- **Body:** Inter (sans-serif)
- **Display:** Space Grotesk (headings, logo)

### Components
- Glass morphism effects (`bg-background/80 backdrop-blur-md`)
- Radial gradient backgrounds
- Smooth animations with Framer Motion
- Custom scrollbars (8px width, rounded)

---

## 📊 File Size Reference

### Backend (Total: ~127KB)
- `api.py`: 35.6KB (925 lines)
- `processor.py`: 26.3KB (647 lines)
- `wavespeed_manager.py`: 27.1KB (647 lines)
- `instagram_zip_processor.py`: 14.5KB
- `discord_zip_processor.py`: 13.6KB
- `style_summarizer.py`: 8.9KB (244 lines)
- `chatbot.py`: 7.8KB (227 lines)
- `context_retriever.py`: 5.6KB (176 lines)
- `secrets_manager.py`: 4.9KB
- `stt_manager.py`: 3.6KB
- `context_embedder.py`: 3.4KB (99 lines)

### Frontend (Total: ~90KB)
- `FilesModal.jsx`: 43.2KB (781 lines)
- `ChatInterface.jsx`: 32.9KB (678 lines)
- `Sidebar.jsx`: 12.7KB (262 lines)
- `api.js`: 11.7KB (333 lines)
- `Home.jsx`: 6.6KB (126 lines)
- `index.css`: 3.5KB (126 lines)

---

## 🎯 Next Steps for Major Changes

Based on your request to prepare for "major changes," here are areas to consider:

### Potential Enhancements
1. **Cloud Storage:** Migrate from local files to Firebase/Supabase
2. **Multi-User Support:** Add authentication & user isolation
3. **Real-time Collaboration:** WebSocket for live chat updates
4. **Advanced Analytics:** Conversation insights & statistics
5. **Export Features:** Download chat history, style reports
6. **Mobile App:** React Native version
7. **Improved RAG:** Fine-tuned embeddings, hybrid search
8. **Voice Improvements:** Multiple voice samples, accent preservation
9. **UI Enhancements:** Themes, customization, accessibility
10. **Performance:** Caching, lazy loading, code splitting

### Architecture Considerations
- **Database Migration:** SQLite → PostgreSQL for scalability
- **API Gateway:** Add rate limiting, authentication middleware
- **Microservices:** Separate voice, chat, processing services
- **CDN:** Static asset delivery
- **Monitoring:** Error tracking (Sentry), analytics (Mixpanel)

---

## 📝 Development Notes

### Running Locally
```bash
# Frontend
npm install
npm run dev  # http://localhost:5173

# Backend
cd backend
pip install -r requirements.txt
python api.py  # http://localhost:5000
```

### Key Design Decisions
1. **Consolidated Backend:** Single Flask server for simplicity
2. **Local Persistence:** JSON files for easy debugging
3. **RAG over Fine-tuning:** Faster iteration, no model training
4. **Gemini Flash:** Balance of speed & quality
5. **Dark Theme:** Psychological horror aesthetic
6. **Component Library:** Radix UI for accessibility

---

**End of Project Overview**
