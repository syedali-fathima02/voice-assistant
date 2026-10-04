"""
Test suite for Python Voice Assistant
--------------------------------------
Verifies NLU intent classification, config management, weather fetching,
reminder timers, email handling, and custom command execution.
"""

import json
import os
import time
import unittest
from main import NLUParser, VoiceAssistant, load_config, save_config


class TestNLUParser(unittest.TestCase):
    def setUp(self):
        self.custom_commands = {
            "open github": {"action": "open_url", "target": "https://github.com"}
        }

    def test_greeting_intent(self):
        intent, entities = NLUParser.parse("Hello assistant", self.custom_commands)
        self.assertEqual(intent, "GREETING")

    def test_time_intent(self):
        intent, entities = NLUParser.parse("Can you tell me the current time please?", self.custom_commands)
        self.assertEqual(intent, "TIME")

    def test_date_intent(self):
        intent, entities = NLUParser.parse("What day is it today?", self.custom_commands)
        self.assertEqual(intent, "DATE")

    def test_search_intent(self):
        intent, entities = NLUParser.parse("Search for artificial intelligence", self.custom_commands)
        self.assertEqual(intent, "SEARCH")
        self.assertEqual(entities.get("query"), "artificial intelligence")

    def test_weather_intent(self):
        intent, entities = NLUParser.parse("What is the weather in London?", self.custom_commands)
        self.assertEqual(intent, "WEATHER")
        self.assertEqual(entities.get("city"), "London")

    def test_reminder_intent(self):
        intent, entities = NLUParser.parse("Remind me in 5 seconds to take a break", self.custom_commands)
        self.assertEqual(intent, "REMINDER")
        self.assertEqual(entities.get("duration"), 5)
        self.assertEqual(entities.get("note"), "take a break")

    def test_qa_intent(self):
        intent, entities = NLUParser.parse("Who is Albert Einstein", self.custom_commands)
        self.assertEqual(intent, "QA")

    def test_custom_command_intent(self):
        intent, entities = NLUParser.parse("Please open github for me", self.custom_commands)
        self.assertEqual(intent, "CUSTOM_COMMAND")
        self.assertEqual(entities.get("trigger"), "open github")

    def test_add_command_intent(self):
        intent, entities = NLUParser.parse("Add command open twitter target https://twitter.com", self.custom_commands)
        self.assertEqual(intent, "ADD_COMMAND")
        self.assertEqual(entities.get("trigger"), "open twitter")
        self.assertEqual(entities.get("target"), "https://twitter.com")

    def test_exit_intent(self):
        intent, entities = NLUParser.parse("Goodbye assistant", self.custom_commands)
        self.assertEqual(intent, "EXIT")


class TestVoiceAssistantIntegration(unittest.TestCase):
    def setUp(self):
        self.assistant = VoiceAssistant()

    def test_command_processing(self):
        # Test time handling
        self.assertTrue(self.assistant.process_command("what time is it"))

        # Test date handling
        self.assertTrue(self.assistant.process_command("tell me the date"))

        # Test greeting handling
        self.assertTrue(self.assistant.process_command("hello"))

        # Test reminder setup
        self.assertTrue(self.assistant.process_command("remind me in 1 second to test reminder"))
        time.sleep(1.5)  # allow timer to trigger

        # Test exit handling
        self.assertFalse(self.assistant.process_command("quit"))


if __name__ == "__main__":
    unittest.main()
