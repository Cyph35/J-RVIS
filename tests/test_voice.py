from voice.listener import CHUNK_SEC, EndpointDetector


def run(levels, **kw):
    d = EndpointDetector(threshold=0.1, **kw)
    for i, lvl in enumerate(levels):
        state = d.feed(lvl)
        if state != "continue":
            return state, i + 1
    return "continue", len(levels)


def test_done_after_silence_following_speech():
    state, n = run([0.0] * 3 + [0.5] * 10 + [0.0] * 20, silence_sec=1.0)
    assert state == "done" and n == 3 + 10 + 10


def test_timeout_when_nobody_speaks():
    assert run([0.0] * 200, no_speech_timeout=2.0) == ("timeout", 20)


def test_max_length_cuts_off_long_speech():
    assert run([0.5] * 500, max_sec=3.0) == ("done", 30)


def test_pause_shorter_than_silence_does_not_end():
    state, _ = run([0.5] * 5 + [0.0] * 5 + [0.5] * 5, silence_sec=1.0)
    assert state == "continue"


def test_clean_for_speech():
    from voice.speaker import clean_for_speech
    out = clean_for_speech("**Done!** 🎉 Opened https://google.com/search?q=x `now`")
    assert out == "Done! Opened link now"


def test_speaker_reports_failure_without_raising(monkeypatch):
    import subprocess
    from voice.speaker import Speaker

    def boom(*a, **k):
        raise OSError("no audio")
    monkeypatch.setattr(subprocess, "Popen", boom)
    assert Speaker().speak("hello") is False
