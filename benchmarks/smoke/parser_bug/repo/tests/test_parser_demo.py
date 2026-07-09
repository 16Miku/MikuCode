from parser_demo import parse_value


def test_parse_value_strips_whitespace():
    assert parse_value("  miku  ") == "miku"
