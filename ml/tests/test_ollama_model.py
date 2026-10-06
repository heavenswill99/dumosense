"""Local adapter contract; no model download or network request in tests."""
import io
import json
import unittest
from unittest.mock import patch

from dumosense_ai.ollama_model import OllamaExplanationModel


class OllamaExplanationModelTest(unittest.TestCase):
    def setUp(self):
        self.context = {"states": [{"observation": "Accuracy was 80.0%."}],
                        "evidence": [], "allowed_actions": ["review_history"]}

    def test_uses_loopback_structured_output_and_bounded_context(self):
        answer = {"text": "The observed result is available.",
                  "action_class": "review_history", "evidence_ids": []}
        wire = {"message": {"content": json.dumps(answer)}}
        with patch("dumosense_ai.ollama_model.urlopen",
                   return_value=io.BytesIO(json.dumps(wire).encode())) as call:
            self.assertEqual(OllamaExplanationModel().generate(self.context), answer)
        request = call.call_args.args[0]
        self.assertEqual(request.full_url, "http://127.0.0.1:11434/api/chat")
        payload = json.loads(request.data)
        self.assertFalse(payload["stream"])
        self.assertEqual(payload["format"]["required"],
                         ["text", "action_class", "evidence_ids"])
        self.assertEqual(payload["format"]["properties"]["action_class"]["enum"],
                         ["review_history"])
        self.assertEqual(payload["options"]["num_ctx"], 2048)

    def test_malformed_response_fails_closed(self):
        with patch("dumosense_ai.ollama_model.urlopen",
                   return_value=io.BytesIO(b'{"message":{"content":"not json"}}')):
            with self.assertRaises(ValueError):
                OllamaExplanationModel().generate(self.context)


if __name__ == "__main__":
    unittest.main()
