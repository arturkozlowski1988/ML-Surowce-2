import re


class DataAnonymizer:
    def __init__(self):
        # Regex patterns for sensitive data
        self.pl_nip_pattern = r"\b\d{10}\b"  # Simplified NIP
        self.pl_pesel_pattern = r"\b\d{11}\b"  # Simplified PESEL
        self.email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"

    def anonymize_text(self, text: str) -> str:
        """
        Masks sensitive information in the text locally before sending to Cloud AI.
        """
        if not text:
            return ""

        # Mask NIP
        text = re.sub(self.pl_nip_pattern, "[NIP]", text)

        # Mask PESEL
        text = re.sub(self.pl_pesel_pattern, "[PESEL]", text)

        # Mask Emails
        text = re.sub(self.email_pattern, "[EMAIL]", text)

        return text

    def clean_response(self, text: str) -> str:
        """
        Optional: Processes the AI response if needed.
        """
        return text
