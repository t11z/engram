import bartleby_server


def test_version_exposed() -> None:
    assert bartleby_server.__version__ == "0.1.0"
