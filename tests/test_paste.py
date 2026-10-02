"""Auto-Enter's send key: ⌘Return on sites where Return is a new line."""

import pytest



class TestSendKey:
    @pytest.mark.parametrize("url, command", [
        ("https://www.linkedin.com/messaging/thread/1", True), ("https://mail.google.com/mail/u/0", True),
        ("https://outlook.office.com/mail/", True), ("https://slack.com/x", False), ("https://notlinkedin.com", False),
        (None, False), ("", False),
    ])
    def test_sites_where_return_is_a_new_line(self, url, command):
        from mispr.paste import send_with_command
        assert send_with_command(url) is command

    def test_command_return_sets_only_command(self, monkeypatch):
        import Quartz
        from mispr import paste
        flags = []
        monkeypatch.setattr(paste.Quartz, "CGEventSetFlags", lambda e, f: flags.append(f))
        paste.press_enter(command=True, post=lambda e: None)
        paste.press_enter(post=lambda e: None)
        assert flags == [Quartz.kCGEventFlagMaskCommand] * 2 + [0, 0]
