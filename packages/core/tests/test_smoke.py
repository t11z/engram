import bartleby_core


def test_version_exposed() -> None:
    assert bartleby_core.__version__ == "0.1.0"
