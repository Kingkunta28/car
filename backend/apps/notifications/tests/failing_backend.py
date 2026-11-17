from django.core.mail.backends.base import BaseEmailBackend


class FailingBackend(BaseEmailBackend):
    def send_messages(self, messages):
        raise ConnectionError("SMTP down")
