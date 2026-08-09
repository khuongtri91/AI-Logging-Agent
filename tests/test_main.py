from types import SimpleNamespace

from src import main as app_main


def test_main_renders_streamlit_application(monkeypatch):
    calls = []
    settings = object()
    agent = object()
    fake_streamlit = SimpleNamespace(
        session_state=SimpleNamespace(
            agent=agent,
            user_id="user-1",
            session_id="session-1",
        )
    )

    monkeypatch.setattr(app_main, "st", fake_streamlit)
    monkeypatch.setattr(app_main, "apply_page_styles", lambda: calls.append(("styles", None)))
    monkeypatch.setattr(
        app_main,
        "initialize_session_state",
        lambda: calls.append(("state", None)) or settings,
    )
    monkeypatch.setattr(
        app_main,
        "render_sidebar",
        lambda received_settings: calls.append(("sidebar", received_settings)),
    )
    monkeypatch.setattr(
        app_main,
        "render_chat_interface",
        lambda received_agent, user_id, session_id: calls.append(
            ("chat", received_agent, user_id, session_id)
        ),
    )

    app_main.main()

    assert calls == [
        ("styles", None),
        ("state", None),
        ("sidebar", settings),
        ("chat", agent, "user-1", "session-1"),
    ]
