# Python Voice Assistant (Beginner & Advanced Tier)

A feature-rich, Python-based Voice Assistant built with AI assistance, capable of understanding free-form spoken or typed commands, synthesizing speech, managing reminders, retrieving live weather, querying general knowledge and executing custom user commands.

---

## 🚀 Features Breakdown

### 🌟 Beginner Tier Features

- **Voice Capture & Speech Recognition**: Captures microphone audio using the `speech_recognition` library with Google Speech API processing.
- **Text-to-Speech (TTS) Feedback**: Speaks all assistant responses aloud using `pyttsx3`.
- **Predefined Greetings**: Responds to greetings ("hello", "hi", "good morning") tailored to the time of day.
- **Current Time & Date**: Announces exact current time and date on request.
- **Web Search**: Opens default web browser and executes search queries on Google.
- **Graceful Error Handling**: Detects unclear input or audio timeouts and prompts the user to repeat.

### ⚡ Advanced Tier Features

- **Natural Language Understanding (NLU)**: Intent classification engine parsing free-form sentence structures and extracting key entities (cities, durations, email addresses, queries).
- **Timed Reminders & Audible Alerts**: Spawns background timers (`threading.Timer`) triggering system beep alerts and spoken notifications upon expiry.
- **Live Weather Updates**: Fetches weather data using OpenWeatherMap API (when configured) or zero-config `wttr.in` REST API fallback.
- **General Knowledge QA**: Responds to factual questions ("who is...", "what is...") via DuckDuckGo Instant Answer API and Wikipedia Summary API.
- **Custom Commands (`config.json`)**: Loads custom command triggers and targets from `config.json` or adds them dynamically via voice/text prompts ("add command open twitter target https://twitter.com").
- **Dual Input Mode**: Supports both **Voice Microphone Mode** and **Interactive Text Mode** (keyboard input) for headless or silent environments.

---

## 📦 Requirements & Installation

1. **Clone or navigate to the workspace**:

   ```bash
   cd voice-Assistant
   ```
2. **Install Python Dependencies**:

   ```bash
   pip install speechrecognition pyttsx3 pyaudio requests
   ```

   > *Platform Specific Note for PyAudio*:
   >
   > - **Windows**: `pip install pyaudio`
   > - **macOS**: `brew install portaudio && pip install pyaudio`
   > - **Linux**: `sudo apt-get install python3-pyaudio`
   >

---

## 🛠️ Usage

Run the main application:

```bash
python main.py
```

### Choosing Input Mode:

When launched, the assistant will detect available audio input devices and prompt:

- Select **`V`** for Microphone Voice Mode.
- Select **`T`** for Keyboard Text Mode.

---

## 🔒 Privacy Consideration

Privately processing user speech and data is a primary design goal of this assistant:

1. **Audio Capture**:

   - Audio is recorded only when the assistant is actively in the `Listening...` phase.
   - Captured audio clips are held temporarily in RAM solely for speech-to-text conversion and are **never saved to disk** or permanently stored.
2. **External Cloud Processing**:

   - Spoken audio is converted to text using Google's Speech Recognition endpoint over encrypted HTTPS connection (`speech_recognition`).
   - If Privacy is paramount or internet is disconnected, use **Text Mode (`T`)**, which processes commands 100% locally without cloud transmission.
3. **Text-to-Speech (TTS)**:

   - Voice synthesis is performed 100% locally on your machine via `pyttsx3` using native operating system speech engines (Windows SAPI5 / macOS NSSpeechSynthesizer / Linux espeak). No audio output data is sent to external servers.
4. **Credential Security**:

   - Credentials stored in `config.json` (such as SMTP details or API keys) remain exclusively on your local file system.
   - Email sending defaults to `dry_run: true` so no emails or passwords are sent anywhere unless explicitly configured by the user.

---

## ⚙️ Configuration (`config.json`)

Example configuration structure:

```json
{
  "custom_commands": {
    "open github": {
      "action": "open_url",
      "target": "https://github.com",
      "response": "Opening GitHub for you."
    }
  },
  "user_name": "Friend",
  "weather": {
    "city": "New York",
    "api_key": ""
  },
  "email": {
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "sender_email": "test_assistant@example.com",
    "sender_password": "",
    "dry_run": true
  },
  "tts": {
    "rate": 175,
    "volume": 1.0
  }
}
```

---

## 🧪 Testing

Run the automated test suite to verify NLU intent classification, weather API fallback, email dry-runs, and reminder timers:

```bash
python test_assistant.py
```
