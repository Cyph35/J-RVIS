"""Predefined, bounded workflows: fixed tool sequences. The model only picks a name."""
WORKFLOWS: dict[str, list[tuple[str, dict]]] = {
    "start_work": [("open_application", {"name": "VS Code"}), ("open_application", {"name": "Terminal"})],
    "relax": [("open_application", {"name": "Spotify"}), ("music_control", {"action": "play"})],
}
