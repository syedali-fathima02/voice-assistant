"""
Python Voice Assistant - Beginner & Advanced Tiers
--------------------------------------------------
Features:
  - Speech Recognition (Microphone) & Text Mode Fallback
  - Text-to-Speech (pyttsx3)
  - Natural Language Understanding (NLU) Intent Classification
  - Predefined & Dynamic Greetings
  - Time and Date reporting
  - Web search execution
  - Timed reminders with audible alerts (threading.Timer)
  - Live Weather updates (OpenWeatherMap API or zero-config wttr.in fallback)
  - General Knowledge QA (DuckDuckGo Instant Answer / Wikipedia REST API)
  - Custom commands via config.json and voice/text prompts
  - Privacy compliance & structured logging
"""

import datetime
import json
import os
import random
import re
import sys
import threading
import time
import urllib.parse
import webbrowser
from typing import Any, Dict, Optional, Tuple

import requests
import speech_recognition as sr

try:
    import pyttsx3
except ImportError:
    pyttsx3 = None 

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")


def load_config() -> Dict[str, Any]:
    """Load configuration from config.json or return default settings."""
    default_config = {
        "custom_commands": {
            "open github": {
                "action": "open_url",
                "target": "https://github.com",
                "response": "Opening GitHub for you."
            },
            "open youtube": {
                "action": "open_url",
                "target": "https://www.youtube.com",
                "response": "Opening YouTube."
            },
            "tell me a joke": {
                "action": "speak",
                "target": "Why do programmers prefer dark mode? Because light attracts bugs!",
                "response": "Why do programmers prefer dark mode? Because light attracts bugs!"
            }
        },
        "user_name": "Friend",
        "weather": {
            "city": "Ramanathapuram",
            "api_key": ""
        },
        "tts": {
            "rate": 175,
            "volume": 1.0
        }
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
                # Ensure all key sections exist
                for key, val in default_config.items():
                    if key not in config:
                        config[key] = val
                return config
        except Exception as e:
            print(f"[Warning] Failed to load config.json ({e}). Using defaults.")
    return default_config


def save_config(config: Dict[str, Any]) -> None:
    """Save configuration dictionary to config.json."""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        print(f"[Error] Failed to save config.json: {e}")


class NLUParser:
    """Natural Language Understanding parser for spoken command intent & entity extraction."""

    @staticmethod
    def parse(text: str, custom_commands: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """Parse raw input string and return (intent, entities_dict)."""
        # Strip trailing sentence punctuation while retaining @, :, /, .
        text_clean = text.strip().rstrip("?.!").lower()
        if not text_clean:
            return "UNKNOWN", {}

        # 1. Exit / Stop
        if any(w in text_clean for w in ["exit", "quit", "goodbye", "stop assistant", "shut down"]):
            return "EXIT", {}

        # 2. Add Custom Command Intent
        if text_clean.startswith("add command") or text_clean.startswith("add custom command"):
            pattern = r"add (?:custom )?command (.+?) target (.+)"
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return "ADD_COMMAND", {"trigger": match.group(1).strip().lower(), "target": match.group(2).strip()}

        # 3. Check Custom Commands
        for trigger in custom_commands:
            if trigger in text_clean:
                return "CUSTOM_COMMAND", {"trigger": trigger}

        # 5. Timed Reminder Intent
        if "remind" in text_clean or "reminder" in text_clean:
            duration = 10  # default seconds
            sec_match = re.search(r"(\d+)\s*(?:second|sec|seconds|secs)", text_clean)
            min_match = re.search(r"(\d+)\s*(?:minute|min|minutes|mins)", text_clean)

            if sec_match:
                duration = int(sec_match.group(1))
            elif min_match:
                duration = int(min_match.group(1)) * 60

            note = "Check your reminder"
            note_match = re.search(r"(?:to|about)\s+(.+)", text_clean)
            if note_match:
                note = note_match.group(1).strip()

            return "REMINDER", {"duration": duration, "note": note}

        # 6. Weather Intent
        if "weather" in text_clean or "temperature" in text_clean or "forecast" in text_clean:
            city = ""
            city_match = re.search(r"(?:weather|temperature|forecast)\s+(?:in|at|for)?\s*([a-zA-Z\s]+)", text_clean)
            if city_match:
                city = city_match.group(1).strip().title()
            return "WEATHER", {"city": city}

        # 7. Web Search Intent
        if text_clean.startswith("search for") or text_clean.startswith("search ") or text_clean.startswith("google "):
            query = text_clean.replace("search for", "").replace("search", "").replace("google", "").strip()
            return "SEARCH", {"query": query}

        # 8. General Knowledge QA Intent
        if any(text_clean.startswith(prefix) for prefix in ["who is", "what is", "tell me about", "define ", "where is"]):
            return "QA", {"query": text_clean}

        # 9. Greeting Intent
        if any(w in text_clean for w in ["hello", "hi", "hey", "good morning", "good afternoon", "greetings"]):
            return "GREETING", {}

        # 10. Time Intent
        if "time" in text_clean and not ("timer" in text_clean or "reminder" in text_clean):
            return "TIME", {}

        # 11. Date Intent
        if "date" in text_clean or "day is it" in text_clean or "today's date" in text_clean:
            return "DATE", {}

        # Fallback search
        if "search" in text_clean:
            query = text_clean.replace("search", "").strip()
            return "SEARCH", {"query": query}

        return "UNKNOWN", {"text": text_clean}


class VoiceAssistant:
    """Main Voice Assistant class supporting Text-to-Speech, Speech Recognition, and Intent Processing."""

    def __init__(self):
        self.config = load_config() 
        self.recognizer = sr.Recognizer()
        self.engine = None
        self._tts_lock = threading.Lock()

        # Initialize pyttsx3 engine safely
        if pyttsx3 is not None:
            try:
                self.engine = pyttsx3.init()
                rate = self.config.get("tts", {}).get("rate", 175)
                volume = self.config.get("tts", {}).get("volume", 1.0)
                self.engine.setProperty("rate", rate)
                self.engine.setProperty("volume", volume)
            except Exception as e:
                print(f"[Warning] Could not initialize pyttsx3 engine: {e}. Falling back to console output.")
                self.engine = None

    def speak(self, text: str) -> None:
        """Output text via TTS and print to console."""
        print(f"\n[Assistant]: {text}")

        # Priority 1: Native Windows SAPI5 (Never hangs or locks PyAudio microphone stream)
        if sys.platform == "win32":
            try:
                import win32com.client
                speaker = win32com.client.Dispatch("SAPI.SpVoice")
                speaker.Speak(text)
                return
            except Exception:
                pass

        # Priority 2: pyttsx3 fallback
        if self.engine:
            with self._tts_lock:
                try:
                    self.engine.say(text)
                    self.engine.runAndWait()
                except Exception as e:
                    print(f"[TTS Error]: {e}")

    def listen(self, mode: str = "voice") -> str:
        """Capture input via Microphone (voice) or Console (text)."""
        if mode == "text":
            try:
                user_input = input("\n[You (Type command)]: ").strip()
                return user_input
            except (KeyboardInterrupt, EOFError):
                return "exit"

        # Voice Mode
        print("\n[Listening via Microphone... Speak now! (Press Ctrl+C to exit)]")
        try:
            with sr.Microphone() as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.3)
                self.recognizer.energy_threshold = max(self.recognizer.energy_threshold, 300)
                try:
                    audio = self.recognizer.listen(source, timeout=6, phrase_time_limit=10)
                except sr.WaitTimeoutError:
                    self.speak("I didn't hear anything. Could you please repeat?")
                    return ""

            try:
                command = self.recognizer.recognize_google(audio)
                print(f"[You (Spoken)]: {command}")
                return command
            except sr.UnknownValueError:
                self.speak("Sorry, I couldn't understand that. Could you please repeat?")
                return ""
            except sr.RequestError:
                self.speak("I'm having trouble connecting to the speech recognition server.")
                return ""
        except KeyboardInterrupt:
            return "exit"
        except Exception as e:
            print(f"[Microphone Error]: {e}. Switching to Text Input mode for this command.")
            try:
                return input("\n[You (Type command)]: ").strip()
            except (KeyboardInterrupt, EOFError):
                return "exit"

    # --- Feature Handlers ---

    def handle_greeting(self) -> None:
        user_name = self.config.get("user_name", "Friend")
        now_hour = datetime.datetime.now().hour
        if now_hour < 12:
            greeting = "Good morning"
        elif now_hour < 18:
            greeting = "Good afternoon"
        else:
            greeting = "Good evening"
        self.speak(f"{greeting}, {user_name}! How can I assist you today?")

    def handle_time(self) -> None:
        now_str = datetime.datetime.now().strftime("%I:%M %p")
        self.speak(f"The current time is {now_str}.")

    def handle_date(self) -> None:
        today_str = datetime.datetime.now().strftime("%A, %B %d, %Y")
        self.speak(f"Today is {today_str}.")

    def handle_search(self, query: str) -> None:
        if not query:
            self.speak("What topic would you like me to search for?")
            return
        self.speak(f"Searching the web for {query}.")
        search_url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
        webbrowser.open(search_url)

    def handle_reminder(self, duration: int, note: str) -> None:
        self.speak(f"Reminder set for {duration} seconds from now: '{note}'.")

        def trigger_alarm():
            print("\n" + "=" * 40)
            print(f"[REMINDER ALERT]: {note}")
            print("=" * 40)
            # Produce audible beep if platform supports
            try:
                if sys.platform == "win32":
                    import winsound
                    winsound.Beep(1000, 1000)
            except Exception:
                pass
            self.speak(f"Reminder Alert! {note}")

        timer_thread = threading.Timer(duration, trigger_alarm)
        timer_thread.daemon = True
        timer_thread.start()

    def handle_weather(self, city: str) -> None:
        target_city = city or self.config.get("weather", {}).get("city", "New York")
        api_key = self.config.get("weather", {}).get("api_key", "")

        self.speak(f"Fetching weather update for {target_city}...")

        # Option A: OpenWeatherMap API if API key provided
        if api_key:
            try:
                url = f"http://api.openweathermap.org/data/2.5/weather?q={urllib.parse.quote(target_city)}&appid={api_key}&units=metric"
                resp = requests.get(url, timeout=5)
                if resp.status_code == 200:
                    data = resp.json()
                    temp = data["main"]["temp"]
                    desc = data["weather"][0]["description"]
                    self.speak(f"The current weather in {target_city} is {desc} with a temperature of {temp}°C.")
                    return
            except Exception as e:
                print(f"[Weather API Warning]: {e}")

        # Option B: Zero-config fallback via wttr.in REST API
        try:
            url = f"https://wttr.in/{urllib.parse.quote(target_city)}?format=%C+%t"
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200 and resp.text:
                weather_info = resp.text.strip()
                self.speak(f"The weather in {target_city} is currently {weather_info}.")
                return
        except Exception as e:
            print(f"[wttr.in Error]: {e}")

        self.speak(f"Sorry, I couldn't fetch live weather updates for {target_city} right now.")

    def handle_qa(self, query: str) -> None:
        self.speak(f"Looking up information for: {query}...")

        # 1. Try DuckDuckGo Instant Answer API
        try:
            clean_q = re.sub(r"^(who is|what is|tell me about|define)\s+", "", query, flags=re.IGNORECASE).strip()
            url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(clean_q)}&format=json&no_html=1&skip_disambig=1"
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                abstract = data.get("AbstractText", "")
                if abstract:
                    self.speak(abstract)
                    return
        except Exception as e:
            print(f"[DuckDuckGo QA Error]: {e}")

        # 2. Try Wikipedia REST Summary API
        try:
            clean_q = re.sub(r"^(who is|what is|tell me about|define)\s+", "", query, flags=re.IGNORECASE).strip()
            wiki_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(clean_q.title().replace(' ', '_'))}"
            resp = requests.get(wiki_url, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                extract = data.get("extract", "")
                if extract:
                    # Truncate summary for spoken response length
                    short_extract = extract.split(". ")[0] + "."
                    self.speak(short_extract)
                    return
        except Exception as e:
            print(f"[Wikipedia QA Error]: {e}")

        # 3. Fallback to Web Search
        self.speak("I couldn't find a direct summary. Opening web search results for you.")
        self.handle_search(query)

    def handle_custom_command(self, trigger: str) -> None:
        custom_cmds = self.config.get("custom_commands", {})
        cmd_info = custom_cmds.get(trigger, {})
        action = cmd_info.get("action", "speak")
        target = cmd_info.get("target", "")
        response = cmd_info.get("response", f"Executing custom command: {trigger}")

        if trigger == "tell me a joke":
            jokes = [
                "Why do programmers prefer dark mode? Because light attracts bugs!",
                "There are 10 types of people in the world: those who understand binary, and those who don't.",
                "Why do Java developers wear glasses? Because they don't C#!",
                "A SQL query walks into a bar, walks up to two tables and asks, 'Can I join you?'",
                "An optimist says the glass is half full. A pessimist says it's half empty. A programmer says the glass is twice as large as necessary."
            ]
            response = random.choice(jokes)

        self.speak(response)

        if action == "open_url" and target:
            webbrowser.open(target)

    def handle_add_command(self, trigger: str, target: str) -> None:
        if not trigger or not target:
            self.speak("Invalid custom command specification.")
            return

        action = "open_url" if target.startswith("http") else "speak"
        self.config["custom_commands"][trigger] = {
            "action": action,
            "target": target,
            "response": f"Executing custom command: {trigger}"
        }
        save_config(self.config)
        self.speak(f"Successfully added custom command for '{trigger}'.")

    def process_command(self, text: str) -> bool:
        """Process a spoken or typed text command. Returns False if assistant should exit."""
        if not text:
            return True

        intent, entities = NLUParser.parse(text, self.config.get("custom_commands", {}))

        if intent == "EXIT":
            self.speak("Goodbye! Have a great day.")
            return False

        elif intent == "GREETING":
            self.handle_greeting()

        elif intent == "TIME":
            self.handle_time()

        elif intent == "DATE":
            self.handle_date()

        elif intent == "SEARCH":
            self.handle_search(entities.get("query", ""))

        elif intent == "REMINDER":
            self.handle_reminder(entities.get("duration", 10), entities.get("note", "Check reminder"))

        elif intent == "WEATHER":
            self.handle_weather(entities.get("city", ""))

        elif intent == "QA":
            self.handle_qa(entities.get("query", text))
 
        elif intent == "CUSTOM_COMMAND":
            self.handle_custom_command(entities.get("trigger", ""))

        elif intent == "ADD_COMMAND":
            self.handle_add_command(entities.get("trigger", ""), entities.get("target", ""))

        else:
            self.speak("Sorry, I didn't recognize that intent. Try asking for time, date, weather, web search, or setting a reminder.")

        return True

    def run(self) -> None:
        print("=" * 60)
        print("           PYTHON VOICE ASSISTANT (ADVANCED TIER)")
        print("=" * 60)

        # Check microphone availability
        mode = "voice"
        try:
            mics = sr.Microphone.list_microphone_names()
            if not mics:
                print("[Notice] No microphone hardware detected. Defaulting to Text Input Mode.")
                mode = "text"
            else:
                print(f"[System] Found {len(mics)} audio input device(s).")
                choice = input("Select Mode: [V]oice Microphone / [T]ext Keyboard (default V): ").strip().lower()
                if choice == "t":
                    mode = "text"
        except Exception as e:
            print(f"[Notice] Microphone initialization check error: {e}. Defaulting to Text Mode.")
            mode = "text"

        self.speak("Voice Assistant activated.  Say a command or type 'exit' to quit.")

        running = True
        while running:
            try:
                command_text = self.listen(mode=mode)
                running = self.process_command(command_text)
            except (KeyboardInterrupt, EOFError):
                print("\n\n[Exit requested]")
                self.speak("Goodbye! Have a great day.")
                break


if __name__ == "__main__":
    assistant = VoiceAssistant()
    assistant.run()
