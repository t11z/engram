import engram_core


def test_version_exposed() -> None:
    assert engram_core.__version__ == "0.1.0"
