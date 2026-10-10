"""Trivial smoke tests to prove the test harness is wired up correctly."""


def test_hello_world():
    assert True


def test_sources_importable():
    """The src/ modules must be importable via pytest's pythonpath."""
    import api  # noqa: F401

    assert api.BASE_URL == 'https://api.porkbun.com'
