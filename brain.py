"""Goal selection for Flit's autonomous behavior."""

import random


class Brain:
    """Decides what the fly wants; replace this policy to upgrade its behavior."""

    def choose_goal(self, heatmap, width, height):
        if random.random() < 0.45:
            spot = heatmap.pick_hotspot(width, height)
            if spot is not None:
                return "hotspot", spot

        margin_x = min(40, width / 2)
        margin_y = min(40, height / 2)
        return "wander", (
            random.uniform(margin_x, width - margin_x),
            random.uniform(margin_y, height - margin_y),
        )
