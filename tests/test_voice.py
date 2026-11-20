from voice.listener import EndpointDetector


def run(levels, **kw):
    d = EndpointDetector(threshold=0.5, **kw)
    for i, lvl in enumerate(levels):
        state = d.feed(lvl)
        if state != "continue":
            return state, i + 1
    return "continue", len(levels)


def test_done_after_silence_following_speech():
    d = EndpointDetector()
    state, n = run([0.0] * 3 + [0.9] * 10 + [0.0] * 20)
    assert state == "done" and n == 3 + 10 + d.silence_chunks


def test_timeout_when_nobody_speaks():
    state, _ = run([0.0] * 200, no_speech_timeout=2.0)
    assert state == "timeout"


def test_max_length_cuts_off_long_speech():
    state, n = run([0.9] * 500, max_sec=3.0)
    assert state == "done" and n == EndpointDetector(max_sec=3.0).max_chunks


def test_pause_shorter_than_silence_does_not_end():
    state, _ = run([0.9] * 5 + [0.0] * 3 + [0.9] * 5, silence_sec=1.0)
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


def test_single_noise_spike_is_not_speech():
    state, _ = run([0.0, 0.9, 0.0, 0.0, 0.9, 0.0] * 5, no_speech_timeout=3.0)
    assert state == "timeout"


def test_mic_selection_prefers_named_device(monkeypatch):
    import sounddevice as sd
    from voice import audio

    devices = [{"name": "UGREEN Studio Max2", "max_input_channels": 1},
               {"name": "MacBook Air Speakers", "max_input_channels": 0},
               {"name": "MacBook Air Microphone", "max_input_channels": 1}]
    monkeypatch.setattr(sd, "query_devices", lambda *a: devices)
    monkeypatch.setattr(audio.config, "MIC_DEVICE", "macbook")
    assert audio.input_device() == 2
    monkeypatch.setattr(audio.config, "MIC_DEVICE", "nonexistent")
    assert audio.input_device() is None


def test_default_is_system_default_and_refresh_is_safe(monkeypatch):
    import sounddevice as sd
    from voice import audio

    monkeypatch.setattr(audio.config, "MIC_DEVICE", "")
    assert audio.input_device() is None  # auto: follow whatever macOS has selected
    calls = []
    monkeypatch.setattr(sd, "_terminate", lambda: calls.append("t"))
    monkeypatch.setattr(sd, "_initialize", lambda: calls.append("i"))
    audio.refresh_devices()
    assert calls == ["t", "i"]
    monkeypatch.setattr(sd, "_terminate", lambda: (_ for _ in ()).throw(RuntimeError("boom")))
    audio.refresh_devices()  # must never raise


def test_split_sentences_merges_tiny_fragments():
    from voice.speaker import split_sentences
    assert split_sentences("Ok. The time is seven thirty. Anything else?") == [
        "Ok. The time is seven thirty.", "Anything else?"]
    assert split_sentences("Hello there") == ["Hello there"]


def test_make_speaker_falls_back_to_say_when_models_missing(monkeypatch, tmp_path):
    from voice import speaker
    monkeypatch.setattr(speaker.config, "KOKORO_MODEL", tmp_path / "none.onnx")
    assert type(speaker.make_speaker()).__name__ == "Speaker"
