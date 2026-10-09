"""Transparent desktop overlay and fly animation."""

import math
import random
import time
from datetime import datetime

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget

from flit.brain import Brain

MAX_SPEED = 260.0
TURN_RATE = 6.0


def wrap(angle):
    return (angle + math.pi) % (2 * math.pi) - math.pi


class Fly(QWidget):
    def __init__(self, heatmap, screen_geometry):
        super().__init__()
        self.heatmap = heatmap
        self.brain = Brain()

        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.WindowTransparentForInput
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setGeometry(screen_geometry)
        self.width = screen_geometry.width()
        self.height = screen_geometry.height()

        self.position = QPointF(-40, self.height * 0.2)
        self.heading = 0.0
        self.state = "greet_in"
        self.goal = "wander"
        self.target = QPointF(self.width / 2, self.height / 2)
        self.state_until = 0.0
        self.bubble = ""
        self.last_tick = time.monotonic()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(16)

    def fly_to(self, dt):
        dx = self.target.x() - self.position.x()
        dy = self.target.y() - self.position.y()
        distance = math.hypot(dx, dy)
        desired = math.atan2(dy, dx)
        difference = wrap(desired - self.heading)
        turn = max(-TURN_RATE * dt, min(TURN_RATE * dt, difference))
        self.heading += turn + random.uniform(-1, 1) * 1.2 * dt
        speed = min(MAX_SPEED, 70 + distance * 2.5)
        self.position += QPointF(math.cos(self.heading), math.sin(self.heading)) * speed * dt
        return distance

    def tick(self):
        now = time.monotonic()
        dt = min(now - self.last_tick, 0.05)
        self.last_tick = now

        if self.state == "greet_in":
            if self.fly_to(dt) < 40:
                hour = datetime.now().hour
                part = "morning" if hour < 12 else "afternoon" if hour < 18 else "evening"
                self.bubble = f"Good {part}! Welcome back."
                self.state, self.state_until = "greet", now + 4
        elif self.state == "greet":
            self.target = QPointF(
                self.width / 2 + math.cos(now * 2) * 40,
                self.height / 2 + math.sin(now * 3) * 25,
            )
            self.fly_to(dt)
            if now > self.state_until:
                self.bubble = ""
                self.state = "choose"
        elif self.state == "choose":
            self.goal, (x, y) = self.brain.choose_goal(
                self.heatmap, self.width, self.height
            )
            self.target = QPointF(x, y)
            self.state = "fly"
        elif self.state == "fly":
            if self.fly_to(dt) < 18:
                if self.goal == "hotspot":
                    self.state, self.state_until = "land", now + random.uniform(5, 10)
                else:
                    self.state = "choose"
        elif self.state == "land":
            self.position += QPointF(random.uniform(-1, 1), random.uniform(-1, 1)) * 12 * dt
            if now > self.state_until:
                self.state = "choose"
        self.update()

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        flying = self.state != "land"
        painter.save()
        painter.translate(self.position)
        painter.rotate(math.degrees(self.heading))

        flap = math.sin(time.monotonic() * 80) * 18 if flying else 0
        painter.setPen(QPen(QColor(120, 120, 140, 160), 1))
        painter.setBrush(QColor(210, 220, 240, 110))
        for side in (-1, 1):
            painter.save()
            painter.rotate(side * (28 + flap))
            painter.drawEllipse(QRectF(-20, -4, 22, 8))
            painter.restore()

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(60, 40, 25))
        painter.drawEllipse(QRectF(-16, -6, 14, 12))
        painter.setBrush(QColor(170, 120, 60))
        painter.drawEllipse(QRectF(-8, -6, 12, 12))
        painter.setBrush(QColor(150, 100, 50))
        painter.drawEllipse(QRectF(3, -5, 9, 10))
        painter.setBrush(QColor(200, 30, 30))
        painter.drawEllipse(QRectF(6, -6, 5, 5))
        painter.drawEllipse(QRectF(6, 1, 5, 5))
        painter.restore()

        if self.bubble:
            painter.setFont(QFont("Sans", 12))
            bubble_width = painter.fontMetrics().horizontalAdvance(self.bubble) + 24
            bubble = QRectF(self.position.x() + 25, self.position.y() - 50, bubble_width, 30)
            painter.setBrush(QColor(255, 255, 255, 235))
            painter.setPen(QPen(QColor(80, 80, 80), 1))
            painter.drawRoundedRect(bubble, 10, 10)
            painter.drawText(bubble, Qt.AlignCenter, self.bubble)
