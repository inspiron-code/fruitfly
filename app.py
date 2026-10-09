"""Application entry point and global input-listener lifecycle."""

import logging
import os
import sys

from pynput import keyboard, mouse
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from flit.fly import Fly
from flit.heatmap import Heatmap

logger = logging.getLogger("flit")


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
    )
    app = QApplication(sys.argv)
    app.setApplicationName("Flit")
    screen = app.primaryScreen()
    if screen is None:
        raise RuntimeError("Flit needs an available desktop screen.")

    geometry = screen.geometry()
    heatmap = Heatmap()
    fly = Fly(heatmap, geometry)
    fly.show()

    scale = screen.devicePixelRatio() if sys.platform == "win32" else 1.0

    def record_click(x, y, _button, pressed):
        if not pressed:
            return
        logical_x = x / scale - geometry.x()
        logical_y = y / scale - geometry.y()
        if 0 <= logical_x < geometry.width() and 0 <= logical_y < geometry.height():
            heatmap.add(logical_x, logical_y)

    quit_requested = {"value": False}
    mouse_listener = mouse.Listener(on_click=record_click)
    keyboard_listener = keyboard.GlobalHotKeys(
        {"<ctrl>+<alt>+q": lambda: quit_requested.__setitem__("value", True)}
    )
    quit_timer = QTimer()
    quit_timer.timeout.connect(
        lambda: app.quit() if quit_requested["value"] else None
    )
    quit_timer.start(100)

    started = []
    try:
        mouse_listener.start()
        started.append(mouse_listener)
        keyboard_listener.start()
        started.append(keyboard_listener)
        logger.info("Flit is running. Press Ctrl+Alt+Q to quit.")
        return app.exec()
    finally:
        quit_timer.stop()
        for listener in reversed(started):
            listener.stop()
        heatmap.save()


if __name__ == "__main__":
    raise SystemExit(main())
