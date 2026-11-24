"""Tests de l'intégration Brevo. Aucun e-mail réel n'est envoyé et aucune vraie clé n'est nécessaire :
``urlopen`` est simulé et la clé ci-dessous est factice."""
import io
import json
import socket
import urllib.error
from types import SimpleNamespace
from unittest import mock

from django.core.mail import EmailMultiAlternatives, send_mail
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from apps.notifications.brevo import BrevoEmailBackend, BrevoError, build_payload, post_to_brevo, send_brevo_email

FAKE_KEY = "xkeysib-FAKE-TEST-KEY-0123456789"
BACKEND = "apps.notifications.brevo.BrevoEmailBackend"
URLOPEN = "apps.notifications.brevo.urllib.request.urlopen"

BREVO_SETTINGS = dict(
    EMAIL_BACKEND=BACKEND,
    BREVO_API_KEY=FAKE_KEY,
    MAIL_FROM="INDPNS Market <no-reply@indpns.test>",
    DEFAULT_FROM_EMAIL="INDPNS Market <no-reply@indpns.test>",
    CELERY_ENABLED=False,
)


class FakeResponse:
    def __init__(self, status=201, body=b'{"messageId": "<abc@smtp-relay.brevo.com>"}'):
        self.status, self._body = status, body

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def http_error(code, body=b'{"code": "invalid_parameter", "message": "Sender is not valid"}'):
    return urllib.error.HTTPError("https://api.brevo.com/v3/smtp/email", code, "err", {}, io.BytesIO(body))


def sent_request(urlopen_mock, index=0):
    """(Request, payload JSON, timeout) du ``index``-ième appel simulé."""
    call = urlopen_mock.call_args_list[index]
    req = call.args[0]
    return req, json.loads(req.data.decode("utf-8")), call.kwargs.get("timeout")


@override_settings(**BREVO_SETTINGS)
class BuildPayloadTests(SimpleTestCase):
    def test_html_and_text_message(self):
        msg = EmailMultiAlternatives("Hello", "plain body", None, ["Jane Doe <jane@example.com>"])
        msg.attach_alternative("<p>html body</p>", "text/html")
        p = build_payload(msg)
        self.assertEqual(p["sender"], {"name": "INDPNS Market", "email": "no-reply@indpns.test"})  # MAIL_FROM
        self.assertEqual(p["to"], [{"name": "Jane Doe", "email": "jane@example.com"}])
        self.assertEqual(p["subject"], "Hello")
        self.assertEqual(p["textContent"], "plain body")
        self.assertEqual(p["htmlContent"], "<p>html body</p>")

    def test_text_only_and_extra_recipients(self):
        msg = EmailMultiAlternatives("S", "body", None, ["a@example.com", "b@example.com"], cc=["c@example.com"],
                                     bcc=["d@example.com"], reply_to=["r@example.com"])
        p = build_payload(msg)
        self.assertEqual([t["email"] for t in p["to"]], ["a@example.com", "b@example.com"])
        self.assertEqual(p["cc"], [{"email": "c@example.com"}])
        self.assertEqual(p["bcc"], [{"email": "d@example.com"}])
        self.assertEqual(p["replyTo"], {"email": "r@example.com"})
        self.assertNotIn("htmlContent", p)

    def test_html_subtype_message(self):
        msg = EmailMultiAlternatives("S", "<b>x</b>", None, ["a@example.com"])
        msg.content_subtype = "html"
        p = build_payload(msg)
        self.assertEqual(p["htmlContent"], "<b>x</b>")
        self.assertNotIn("textContent", p)

    def test_attachment_is_base64(self):
        msg = EmailMultiAlternatives("S", "body", None, ["a@example.com"])
        msg.attach("note.txt", "hello", "text/plain")
        self.assertEqual(build_payload(msg)["attachment"], [{"name": "note.txt", "content": "aGVsbG8="}])

    def test_sender_priority_mail_from_then_default_from_email(self):
        msg = EmailMultiAlternatives("S", "b", "other@example.com", ["a@example.com"])
        self.assertEqual(build_payload(msg)["sender"]["email"], "no-reply@indpns.test")   # MAIL_FROM gagne
        with override_settings(MAIL_FROM="", DEFAULT_FROM_EMAIL="Legacy <legacy@indpns.test>"):
            msg = EmailMultiAlternatives("S", "b", None, ["a@example.com"])
            msg.from_email = ""
            self.assertEqual(build_payload(msg)["sender"], {"name": "Legacy", "email": "legacy@indpns.test"})

    def test_invalid_messages_rejected(self):
        with self.assertRaises(BrevoError):
            build_payload(EmailMultiAlternatives("S", "b", None, []))
        with self.assertRaises(BrevoError):
            build_payload(EmailMultiAlternatives("S", "b", None, ["not-an-address"]))
        with self.assertRaises(BrevoError):
            build_payload(EmailMultiAlternatives("S", "", None, ["a@example.com"]))


@override_settings(**BREVO_SETTINGS)
class PostToBrevoTests(SimpleTestCase):
    def test_request_shape_key_url_timeout(self):
        with mock.patch(URLOPEN, return_value=FakeResponse()) as m:
            result = post_to_brevo({"subject": "x"})
        req, payload, timeout = sent_request(m)
        self.assertEqual(req.full_url, "https://api.brevo.com/v3/smtp/email")
        self.assertEqual(req.get_method(), "POST")
        self.assertEqual(req.get_header("Api-key"), FAKE_KEY)          # BREVO_API_KEY
        self.assertEqual(req.get_header("Content-type"), "application/json")
        self.assertEqual(payload, {"subject": "x"})
        self.assertEqual(timeout, 15)
        self.assertEqual(result["messageId"], "<abc@smtp-relay.brevo.com>")

    @override_settings(BREVO_TIMEOUT=7)
    def test_timeout_is_configurable(self):
        with mock.patch(URLOPEN, return_value=FakeResponse()) as m:
            post_to_brevo({"subject": "x"})
        self.assertEqual(sent_request(m)[2], 7)

    @override_settings(BREVO_API_KEY="")
    def test_missing_key_raises_without_network_call(self):
        with mock.patch(URLOPEN) as m:
            with self.assertRaises(BrevoError) as cm:
                post_to_brevo({"subject": "x"})
        m.assert_not_called()
        self.assertIn("BREVO_API_KEY", str(cm.exception))

    def test_client_error_not_retryable_and_no_key_leak(self):
        leaky = b'{"code": "unauthorized", "message": "Key %s is invalid"}' % FAKE_KEY.encode()
        with mock.patch(URLOPEN, side_effect=http_error(401, leaky)):
            with self.assertRaises(BrevoError) as cm:
                post_to_brevo({"subject": "x"})
        self.assertEqual(cm.exception.status, 401)
        self.assertFalse(cm.exception.retryable)
        self.assertNotIn(FAKE_KEY, str(cm.exception))

    def test_server_error_and_rate_limit_are_retryable(self):
        for code in (429, 500, 503):
            with mock.patch(URLOPEN, side_effect=http_error(code, b"")):
                with self.assertRaises(BrevoError) as cm:
                    post_to_brevo({"subject": "x"})
            self.assertTrue(cm.exception.retryable, code)

    def test_network_errors_are_retryable_and_sanitized(self):
        for exc in (urllib.error.URLError(socket.gaierror("dns " + FAKE_KEY)), socket.timeout("timed out")):
            with mock.patch(URLOPEN, side_effect=exc):
                with self.assertRaises(BrevoError) as cm:
                    post_to_brevo({"subject": "x"})
            self.assertTrue(cm.exception.retryable)
            self.assertNotIn(FAKE_KEY, str(cm.exception))


@override_settings(**BREVO_SETTINGS)
class BackendTests(SimpleTestCase):
    def test_send_mail_goes_through_brevo(self):
        with mock.patch(URLOPEN, return_value=FakeResponse()) as m:
            n = send_mail("Subject", "Body", None, ["user@example.com"], html_message="<p>Body</p>")
        self.assertEqual(n, 1)
        _, payload, _ = sent_request(m)
        self.assertEqual(payload["sender"]["email"], "no-reply@indpns.test")
        self.assertEqual(payload["to"], [{"email": "user@example.com"}])
        self.assertEqual(payload["htmlContent"], "<p>Body</p>")

    def test_failure_raises_unless_fail_silently(self):
        with mock.patch(URLOPEN, side_effect=http_error(400)):
            with self.assertRaises(BrevoError):
                send_mail("S", "B", None, ["user@example.com"])
            self.assertEqual(send_mail("S", "B", None, ["user@example.com"], fail_silently=True), 0)

    def test_several_messages_counted(self):
        msgs = [EmailMultiAlternatives("S%d" % i, "b", None, ["u%d@example.com" % i]) for i in range(3)]
        with mock.patch(URLOPEN, return_value=FakeResponse()) as m:
            self.assertEqual(BrevoEmailBackend().send_messages(msgs), 3)
        self.assertEqual(m.call_count, 3)

    def test_send_brevo_email_helper_returns_message_id(self):
        with mock.patch(URLOPEN, return_value=FakeResponse()):
            self.assertEqual(send_brevo_email("u@example.com", "S", html="<p>x</p>", text="x"), "<abc@smtp-relay.brevo.com>")

    def test_api_key_never_logged(self):
        leaky = b'{"code": "unauthorized", "message": "bad key %s"}' % FAKE_KEY.encode()
        with self.assertLogs("apps.notifications.brevo", level="DEBUG") as logs:
            with mock.patch(URLOPEN, side_effect=http_error(401, leaky)):
                send_mail("S", "B", None, ["u@example.com"], fail_silently=True)
            with mock.patch(URLOPEN, return_value=FakeResponse()):
                send_mail("S", "B", None, ["u@example.com"])
        output = "\n".join(logs.output)
        self.assertIn("Brevo send failed", output)
        self.assertNotIn(FAKE_KEY, output)


class SettingsSelectionTests(SimpleTestCase):
    def test_brevo_backend_selected_by_environment(self):
        import importlib
        import os
        from config.settings import base
        env = {"BREVO_API_KEY": FAKE_KEY, "MAIL_FROM": "X <x@indpns.test>", "EMAIL_HOST": "smtp.example.com"}
        with mock.patch.dict(os.environ, env, clear=False):
            os.environ.pop("EMAIL_BACKEND", None)
            reloaded = importlib.reload(base)
            self.assertEqual(reloaded.EMAIL_BACKEND, BACKEND)                    # Brevo prioritaire sur SMTP
            self.assertEqual(reloaded.DEFAULT_FROM_EMAIL, "X <x@indpns.test>")   # MAIL_FROM > DEFAULT_FROM_EMAIL
        importlib.reload(base)   # restaure les valeurs du module pour les autres tests


@override_settings(**BREVO_SETTINGS)
class ApplicationEmailFlowTests(TestCase):
    """Les e-mails existants (vérification de compte, réinitialisation de mot de passe) passent par Brevo."""

    def test_verification_email_via_notifications_service(self):
        from apps.accounts.services import send_verification_email
        from tests.conftest_helpers import make_user
        user = make_user("v@example.com")
        with mock.patch(URLOPEN, return_value=FakeResponse()) as m:
            send_verification_email(user)
        _, payload, _ = sent_request(m)
        self.assertEqual(payload["to"], [{"email": "v@example.com"}])
        self.assertEqual(payload["subject"], "Confirm your email · INDPNS Market")
        self.assertIn("/verify/", payload["htmlContent"])
        self.assertTrue(payload["textContent"])

    def test_send_email_returns_false_when_brevo_fails(self):
        from apps.notifications.services import send_email
        with mock.patch(URLOPEN, side_effect=http_error(400)):
            with self.assertLogs("apps.notifications", level="ERROR") as logs:
                ok = send_email("x@example.com", "S", "emails/verify_email.html",
                                {"user": SimpleNamespace(get_short_name=lambda: "X"), "url": "https://x"})
        self.assertFalse(ok)
        self.assertNotIn(FAKE_KEY, "\n".join(logs.output))

    def test_password_reset_email_via_brevo(self):
        from tests.conftest_helpers import make_user
        make_user("r@example.com")
        with mock.patch(URLOPEN, return_value=FakeResponse()) as m:
            self.client.post(reverse("accounts:password_reset"), {"email": "r@example.com"})
        self.assertEqual(m.call_count, 1)
        _, payload, _ = sent_request(m)
        self.assertEqual(payload["to"], [{"email": "r@example.com"}])
        self.assertEqual(payload["subject"], "Reset your INDPNS Market password")
        self.assertIn("/reset/", payload["textContent"])


class CeleryTaskRetryTests(SimpleTestCase):
    def test_non_retryable_brevo_error_is_not_retried(self):
        from apps.notifications.tasks import deliver_email
        with mock.patch("apps.notifications.tasks._deliver", side_effect=BrevoError("bad sender", status=400)):
            with mock.patch.object(deliver_email, "retry") as retry:
                with self.assertRaises(BrevoError):
                    deliver_email.run("a@example.com", "S", "t", "<p>t</p>")
        retry.assert_not_called()

    def test_retryable_brevo_error_is_retried(self):
        from apps.notifications.tasks import deliver_email
        err = BrevoError("down", status=503, retryable=True)
        with mock.patch("apps.notifications.tasks._deliver", side_effect=err):
            with mock.patch.object(deliver_email, "retry", side_effect=RuntimeError("retry called")) as retry:
                with self.assertRaises(RuntimeError):
                    deliver_email.run("a@example.com", "S", "t", "<p>t</p>")
        retry.assert_called_once()
