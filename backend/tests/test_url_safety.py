import pytest

from seo_audit.url_safety import UnsafeTargetError, normalize_http_url, validate_public_target


def test_normalizes_bare_domain():
    assert normalize_http_url("Example.COM") == "https://example.com/"


@pytest.mark.asyncio
async def test_rejects_localhost_before_request():
    with pytest.raises(UnsafeTargetError, match="Localhost"):
        await validate_public_target("http://localhost:8000")


def test_rejects_non_http_scheme():
    with pytest.raises(UnsafeTargetError, match="http and https"):
        normalize_http_url("file:///etc/passwd")
