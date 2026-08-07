from src.utils import extract_response_text


class Response:
    def __init__(self, content):
        self.content = content


def test_extract_response_text_from_string_content():
    assert extract_response_text(Response("plain text")) == "plain text"


def test_extract_response_text_from_structured_content():
    response = Response([
        {"text": "hello"},
        " ",
        {"ignored": "value"},
        {"text": "world"},
    ])

    assert extract_response_text(response) == "hello world"


def test_extract_response_text_from_other_content():
    assert extract_response_text(Response({"answer": 42})) == "{'answer': 42}"


def test_extract_response_text_from_plain_object():
    assert extract_response_text("already text") == "already text"
