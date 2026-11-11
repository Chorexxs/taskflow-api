"""Email sender and verification link (T-113)."""

from app import email


class FakeSender:
    def __init__(self):
        self.messages = []

    def send(self, *, to, subject, body):
        self.messages.append((to, subject, body))


def test_send_verification_email_builds_a_usable_link(monkeypatch):
    sender = FakeSender()
    monkeypatch.setattr(email, "get_email_sender", lambda: sender)
    monkeypatch.setattr(email.settings, "FRONTEND_URL", "https://app.example.com/")

    email.send_verification_email("user@example.com", "token-123")

    assert len(sender.messages) == 1
    to, subject, body = sender.messages[0]
    assert to == "user@example.com"
    assert subject == email.VERIFICATION_SUBJECT
    assert "https://app.example.com/verify-email?token=token-123" in body


def test_smtp_sender_uses_starttls_and_login(monkeypatch):
    calls = {}

    class FakeSMTP:
        def __init__(self, host, port, timeout):
            calls["connect"] = (host, port, timeout)

        def starttls(self):
            calls["starttls"] = True

        def login(self, username, password):
            calls["login"] = (username, password)

        def send_message(self, message):
            calls["message"] = message

        def quit(self):
            calls["quit"] = True

    monkeypatch.setattr(email.settings, "EMAIL_BACKEND", "smtp")
    monkeypatch.setattr(email.settings, "SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr(email.settings, "SMTP_PORT", 587)
    monkeypatch.setattr(email.settings, "SMTP_USERNAME", "user")
    monkeypatch.setattr(email.settings, "SMTP_PASSWORD", "pass")
    monkeypatch.setattr(email.settings, "SMTP_FROM", "no-reply@example.com")
    monkeypatch.setattr(email.settings, "SMTP_USE_TLS", True)
    monkeypatch.setattr(email.settings, "SMTP_USE_SSL", False)
    monkeypatch.setattr(email.smtplib, "SMTP", FakeSMTP)

    email.SMTPEmailSender().send(to="user@example.com", subject="Subject", body="Body")

    assert calls["connect"] == ("smtp.example.com", 587, 10)
    assert calls["starttls"] is True
    assert calls["login"] == ("user", "pass")
    assert calls["quit"] is True
    assert calls["message"]["To"] == "user@example.com"
