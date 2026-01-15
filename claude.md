# VoiceInk Linux Port Progress

## Project
Porting VoiceInk (macOS voice-to-text app) to Ubuntu 24.04 using GTK4/libadwaita

## Tech Stack
- Python 3.10+
- GTK 4 + libadwaita
- whisper.cpp (ctypes bindings)
- PipeWire/PulseAudio (sounddevice)
- SQLite for persistence

## Phases

| Phase | Name | Status |
|-------|------|--------|
| 01 | Project Setup | completed |
| 02 | Whisper Integration | completed |
| 03 | Audio Recording | completed |
| 04 | Core UI | completed |
| 05 | Persistence | completed |
| 06 | Cloud Services | in_progress |
| 07 | System Integration | pending |
| 08 | Vocabulary | pending |
| 09 | Power Mode | pending |
| 10 | Polish | pending |

## Completed Work

### Phase 1: Project Setup
- GTK4/libadwaita app structure in `voiceink-linux/`
- meson.build, pyproject.toml
- Adw.Application + Adw.ApplicationWindow
- GSettings schema, .desktop file

### Phase 2: Whisper Integration
- ctypes bindings for libwhisper.so
- ModelManager with HuggingFace download
- WhisperState thread-safe manager
- LocalTranscriptionService
- Audio utils (load any format via ffmpeg)
- Models at ~/.local/share/voiceink/models/

### Phase 3: Audio Recording
- AudioRecorder with sounddevice (PipeWire/PulseAudio/ALSA)
- DeviceManager for device enumeration
- Real-time audio level metering
- Automatic resampling to 16kHz for Whisper
- WAV file export/import

### Phase 4: Core UI
- RecordingView with level meter and duration timer
- TranscriptionView with copy/clear buttons
- PreferencesWindow (model, audio, AI settings)
- Full window integration with recording/transcription flow
- Toast notifications, status bar
- GNOME HIG styling

### Phase 5: Persistence
- SQLite database with FTS5 full-text search
- TranscriptionRepository for CRUD operations
- HistoryService for high-level history management
- HistoryView with search and list display
- GSettings schema for app preferences
- XDG-compliant paths (~/.local/share/voiceink/)

## Current: Phase 6 - Cloud Services
- Cloud transcription APIs (OpenAI, Deepgram, Groq)
- AI enhancement service

## Directory Structure
```
voiceink-linux/
├── src/voiceink/
│   ├── main.py, application.py, window.py
│   ├── whisper/ (bindings, state, model_manager)
│   ├── audio/ (utils, recorder, device_manager)
│   ├── services/ (local_transcription)
│   └── models/ (transcription)
├── data/ (desktop, gschema)
├── meson.build
└── pyproject.toml
```
