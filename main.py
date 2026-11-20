import sys

from core.assistant import Assistant


def ask_confirm(summary: str) -> bool:
    return input(f"  JARVIS wants to run {summary}. Allow? [y/N] ").strip().lower() in {"y", "yes"}


def show(assistant: Assistant, reply: str, speaker=None) -> None:
    print("jarvis>", reply)
    for name, args, outcome in assistant.last_tool_calls:
        print(f"  [tool] {name}({args}) -> {'ok' if outcome['ok'] else 'FAILED'}")
    if speaker and not speaker.speak(reply):
        print("  (audio playback failed - reply shown as text only)")


def text_loop(assistant: Assistant, speaker=None) -> None:
    print("JARVIS v0.2 - text mode (add --speak for spoken replies). Type 'quit' to exit.")
    while True:
        try:
            text = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if text.lower() in {"quit", "exit"}:
            break
        if text:
            show(assistant, assistant.handle(text), speaker)


def voice_loop(assistant: Assistant, speaker=None) -> None:
    from voice.listener import record_utterance
    from voice.transcriber import Transcriber

    print("Loading speech model...")
    transcriber = Transcriber()
    print("JARVIS v0.2 - voice mode. Press Enter to speak, or type 'quit'. Ctrl+C stops.")
    while True:
        try:
            if input("[Enter = speak] ").strip().lower() in {"quit", "exit"}:
                break
            audio = record_utterance()
            if audio is None:
                print("(didn't hear anything)")
                continue
            text = transcriber.transcribe(audio)
            if not text:
                print("(couldn't make out any words)")
                continue
            print("you said>", text)
            show(assistant, assistant.handle(text), speaker)
        except (EOFError, KeyboardInterrupt):
            if speaker:
                speaker.stop()
            print()
            break


def wake_loop(assistant: Assistant) -> None:
    import threading

    from core import hands_free
    from core.state import State, StateTracker
    from voice.listener import record_utterance
    from voice.speaker import Speaker
    from voice.transcriber import Transcriber
    from voice.wake_word import WakeWordDetector

    print("Loading models (wake word + speech)...")
    wake, transcriber, speaker = WakeWordDetector(), Transcriber(), Speaker()
    stop, muted = threading.Event(), threading.Event()
    tracker = StateTracker(lambda s: print(f"[{s.value}]"))

    def commands() -> None:
        for line in sys.stdin:
            cmd = line.strip().lower()
            if cmd == "mute":
                muted.set()
            elif cmd == "unmute":
                muted.clear()
            elif cmd in {"quit", "exit"}:
                break
        stop.set()

    threading.Thread(target=commands, daemon=True).start()
    print("JARVIS v1.0 - say 'Hey Jarvis'. Type mute / unmute / quit + Enter. Ctrl+C also stops.")
    try:
        hands_free.run(assistant, wake, lambda: record_utterance(on_status=lambda m: None),
                       transcriber.transcribe, speaker.speak, tracker, stop, muted)
    except KeyboardInterrupt:
        speaker.stop()
    stop.set()
    print("\nJARVIS stopped.")


def main() -> None:
    from memory.conversation import Memory

    memory = Memory()
    if "--forget" in sys.argv:
        memory.forget_all()
        print("All saved history, preferences and task logs were deleted.")
        return
    assistant = Assistant(confirm=ask_confirm, memory=memory)
    if "--menubar" in sys.argv:
        from interface.menubar import JarvisMenuBar

        JarvisMenuBar(assistant).run()
        return
    if "--wake" in sys.argv:
        wake_loop(assistant)
        return
    speaker = None
    if "--voice" in sys.argv or "--speak" in sys.argv:
        from voice.speaker import Speaker

        speaker = Speaker()
    (voice_loop if "--voice" in sys.argv else text_loop)(assistant, speaker)


if __name__ == "__main__":
    main()
