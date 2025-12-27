"""Tests for service layer functions."""
from unittest.mock import patch

from backend.services.nlp_service import generate_hypothesis, _confidence_label


class TestConfidenceLabel:
    """Tests for confidence label conversion."""

    def test_high_confidence(self):
        assert _confidence_label(0.95) == "[HIGH]"
        assert _confidence_label(0.80) == "[HIGH]"

    def test_medium_confidence(self):
        assert _confidence_label(0.79) == "[MEDIUM]"
        assert _confidence_label(0.50) == "[MEDIUM]"

    def test_low_confidence(self):
        assert _confidence_label(0.49) == "[LOW]"
        assert _confidence_label(0.10) == "[LOW]"
        assert _confidence_label(0.0) == "[LOW]"


class TestGenerateHypothesis:
    """Tests for hypothesis generation."""

    @patch("app.services.nlp_service.ollama")
    def test_generate_hypothesis_success(self, mock_ollama):
        """Test successful hypothesis generation."""
        mock_ollama.chat.return_value = {
            "message": {
                "content": "The evidence suggests a break-in occurred. The victim likely knew the attacker."
            }
        }

        result = generate_hypothesis(
            detected_objects=[{"label": "knife", "confidence": 0.9}],
            extracted_texts=[{"text": "HELP", "confidence": 0.8}]
        )

        assert "content" in result
        assert result["confidence"] == 0.7
        assert "break-in" in result["content"]

    @patch("app.services.nlp_service.ollama")
    def test_generate_hypothesis_with_context(self, mock_ollama):
        """Test hypothesis generation with additional context."""
        mock_ollama.chat.return_value = {
            "message": {"content": "Based on the context provided, this appears deliberate."}
        }

        result = generate_hypothesis(
            detected_objects=[],
            extracted_texts=[],
            context="Scene found in residential area"
        )

        # Verify context was passed to the prompt
        call_args = mock_ollama.chat.call_args
        user_message = call_args[1]["messages"][1]["content"]
        assert "residential area" in user_message

    @patch("app.services.nlp_service.ollama")
    def test_generate_hypothesis_ollama_error(self, mock_ollama):
        """Test fallback when Ollama is unavailable."""
        mock_ollama.chat.side_effect = Exception("Connection refused")

        result = generate_hypothesis(
            detected_objects=[{"label": "person", "confidence": 0.7}],
            extracted_texts=[]
        )

        assert result["confidence"] == 0.0
        assert "Unable to generate hypothesis" in result["content"]

    @patch("app.services.nlp_service.ollama")
    def test_confidence_labels_in_prompt(self, mock_ollama):
        """Test that confidence labels are included in the prompt."""
        mock_ollama.chat.return_value = {
            "message": {"content": "Analysis complete."}
        }

        generate_hypothesis(
            detected_objects=[
                {"label": "knife", "confidence": 0.95},  # HIGH
                {"label": "blood", "confidence": 0.60},  # MEDIUM
                {"label": "figure", "confidence": 0.30},  # LOW
            ],
            extracted_texts=[]
        )

        call_args = mock_ollama.chat.call_args
        user_message = call_args[1]["messages"][1]["content"]
        assert "[HIGH] knife" in user_message
        assert "[MEDIUM] blood" in user_message
        assert "[LOW] figure" in user_message

    @patch("app.services.nlp_service.ollama")
    def test_empty_evidence(self, mock_ollama):
        """Test with no detected objects or text."""
        mock_ollama.chat.return_value = {
            "message": {"content": "Insufficient evidence for analysis."}
        }

        generate_hypothesis(
            detected_objects=[],
            extracted_texts=[]
        )

        call_args = mock_ollama.chat.call_args
        user_message = call_args[1]["messages"][1]["content"]
        assert "No objects detected" in user_message
        assert "No text extracted" in user_message
