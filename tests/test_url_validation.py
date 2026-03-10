import pytest

from app.core.destination_store import validate_callback_url


class TestValidUrls:
    def test_https_url_valid(self):
        assert validate_callback_url("https://hooks.example.com/callback") is None

    def test_http_localhost_valid(self):
        assert validate_callback_url("http://localhost:3000/webhook") is None

    def test_http_127_valid(self):
        assert validate_callback_url("http://127.0.0.1:8000/test") is None

    def test_https_with_path_and_query(self):
        assert validate_callback_url("https://api.example.com/v1/hook?token=abc") is None


class TestInvalidSchemes:
    def test_http_non_localhost_rejected(self):
        error = validate_callback_url("http://api.example.com/callback")
        assert error is not None
        assert "HTTPS" in error

    def test_ftp_rejected(self):
        error = validate_callback_url("ftp://files.example.com/data")
        assert error is not None

    def test_file_rejected(self):
        error = validate_callback_url("file:///etc/passwd")
        assert error is not None


class TestPrivateIPs:
    def test_10_x_rejected(self):
        error = validate_callback_url("https://10.0.0.1/hook")
        assert error is not None
        assert "private" in error.lower()

    def test_172_16_rejected(self):
        error = validate_callback_url("https://172.16.0.1/hook")
        assert error is not None

    def test_192_168_rejected(self):
        error = validate_callback_url("https://192.168.1.1/hook")
        assert error is not None

    def test_169_254_link_local_rejected(self):
        error = validate_callback_url("https://169.254.169.254/latest/meta-data")
        assert error is not None


class TestEdgeCases:
    def test_no_hostname_rejected(self):
        error = validate_callback_url("https:///path")
        assert error is not None

    def test_public_hostname_allowed(self):
        assert validate_callback_url("https://hooks.zapier.com/123") is None
