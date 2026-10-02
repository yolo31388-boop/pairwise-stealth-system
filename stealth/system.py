"""pairwise-stealth-system - StealthSystem

A stealth gameplay system featuring:

- Detection with line-of-sight occlusion, light-level influence and gradual
  (progress-based) spotting instead of instant detection.
- Noise propagation that distinguishes surface materials, attenuates over
  distance and scales with the performed action.
- Hiding spots with validity checks, enter/exit animations and a restricted
  field of view while hidden.
- Alertness that decays over time, has multiple levels and is shared between
  enemies.
- A stealth score with time bonus, no-kill (ghost) bonus and combo multiplier.
"""

from __future__ import annotations

import math


def _to_xy(point):
    """Normalize a position given as tuple/list or dict with 'position'."""
    if point is None:
        return None
    if isinstance(point, dict):
        point = point.get("position")
        if point is None:
            return None
    return (float(point[0]), float(point[1]))


def _segments_intersect(a1, a2, b1, b2):
    def orient(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])

    d1 = orient(b1, b2, a1)
    d2 = orient(b1, b2, a2)
    d3 = orient(a1, a2, b1)
    d4 = orient(a1, a2, b2)
    return ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0))


class StealthSystem:
    MATERIAL_NOISE = {
        "carpet": 0.3,
        "rug": 0.3,
        "grass": 0.6,
        "wood": 1.0,
        "floor": 1.0,
        "tile": 1.1,
        "concrete": 1.2,
        "metal": 1.6,
    }
    ACTION_NOISE = {
        "sneak": 0.3,
        "crouch": 0.4,
        "walk": 1.0,
        "run": 2.0,
        "sprint": 2.5,
    }
    ALERT_LEVELS = ("calm", "suspicious", "alert", "combat")

    NORMAL_VIEW_FOV = 120.0
    HIDDEN_VIEW_FOV = 60.0
    ENTER_ANIMATION_DURATION = 0.6
    EXIT_ANIMATION_DURATION = 0.4

    DETECTION_GAIN = 0.5
    DETECTION_DECAY = 0.2
    ALERTNESS_GAIN = 40.0

    def __init__(self, decay_rate=5.0, share_factor=0.5):
        self.state = {}
        self.decay_rate = float(decay_rate)
        self.share_factor = float(share_factor)
        self._detection = {}
        self._alertness = {}
        self._shared_alert = 0.0
        self._hiding = {"spot": None, "state": "outside", "progress": 0.0}

    # ------------------------------------------------------------------
    # Detection: line-of-sight occlusion + light influence + gradual build-up
    # ------------------------------------------------------------------
    def calculate_detection(self, enemy_pos=None, player_pos=None, walls=None,
                            light_level=1.0, view_distance=20.0, fov=120.0,
                            enemy_facing=None, dt=1.0, enemy_id="default",
                            **kwargs):
        light_level = kwargs.get("light", light_level)
        enemy = _to_xy(enemy_pos) or (0.0, 0.0)
        player = _to_xy(player_pos) or (5.0, 0.0)

        distance = math.dist(enemy, player)
        visible = distance <= view_distance
        if visible and enemy_facing is not None:
            visible = self._in_fov(enemy, enemy_facing, player, fov)
        if visible and walls:
            visible = not self._line_blocked(enemy, player, walls)

        light_factor = min(max(float(light_level), 0.0), 1.0)
        progress = self._detection.get(enemy_id, 0.0)
        if visible and light_factor > 0.0:
            proximity = 1.0 - 0.8 * min(distance / max(view_distance, 1e-9), 1.0)
            progress = min(1.0, progress + self.DETECTION_GAIN * light_factor
                           * proximity * dt)
        else:
            progress = max(0.0, progress - self.DETECTION_DECAY * dt)
        self._detection[enemy_id] = progress
        return progress

    @staticmethod
    def _wall_segment(wall):
        if isinstance(wall, dict):
            return _to_xy(wall.get("start")), _to_xy(wall.get("end"))
        wall = list(wall)
        if len(wall) == 2:
            return _to_xy(wall[0]), _to_xy(wall[1])
        if len(wall) == 4:
            return (float(wall[0]), float(wall[1])), (float(wall[2]), float(wall[3]))
        raise ValueError(f"Unsupported wall format: {wall!r}")

    def _line_blocked(self, start, end, walls):
        for wall in walls:
            w1, w2 = self._wall_segment(wall)
            if w1 is None or w2 is None:
                continue
            if _segments_intersect(start, end, w1, w2):
                return True
        return False

    @staticmethod
    def _in_fov(enemy, facing, target, fov):
        if isinstance(facing, (int, float)):
            fx, fy = math.cos(math.radians(facing)), math.sin(math.radians(facing))
        else:
            fx, fy = _to_xy(facing)
        dx, dy = target[0] - enemy[0], target[1] - enemy[1]
        norm = math.hypot(dx, dy)
        if norm == 0.0:
            return True
        dot = (fx * dx + fy * dy) / (math.hypot(fx, fy) * norm)
        angle = math.degrees(math.acos(max(-1.0, min(1.0, dot))))
        return angle <= fov / 2.0

    # ------------------------------------------------------------------
    # Noise: material + distance attenuation + action distinction
    # ------------------------------------------------------------------
    def calculate_noise(self, action="walk", material="floor", distance=5.0,
                        base_volume=10.0, **kwargs):
        action = kwargs.get("movement", action)
        material = kwargs.get("surface", material)
        distance = kwargs.get("dist", distance)
        action_factor = self.ACTION_NOISE.get(str(action).lower(), 1.0)
        material_factor = self.MATERIAL_NOISE.get(str(material).lower(), 1.0)
        attenuation = 1.0 / (1.0 + max(float(distance), 0.0))
        return base_volume * action_factor * material_factor * attenuation

    # ------------------------------------------------------------------
    # Hiding: validity check + enter/exit animation + restricted view
    # ------------------------------------------------------------------
    def check_hiding_spot(self, spot=None, enemies=None, walls=None, dt=0.0,
                          **kwargs):
        if spot is None:
            spot = {}
        elif not isinstance(spot, dict):
            spot = {"position": spot}

        exposed = bool(spot.get("exposed", False))
        concealed = bool(spot.get("concealed", not exposed))
        valid = concealed and not exposed and not spot.get("occupied", False)

        spot_pos = _to_xy(spot.get("position"))
        if valid and enemies and spot_pos is not None:
            for enemy in enemies:
                enemy_pos = _to_xy(enemy)
                if enemy_pos is None:
                    continue
                if walls and self._line_blocked(enemy_pos, spot_pos, walls):
                    continue
                valid = False
                break

        self._update_hiding_animation(valid, spot, dt)
        hidden = self._hiding["state"] in ("entering", "hidden")
        return {
            "valid": valid,
            "can_hide": valid,
            "hidden": hidden,
            "animation_state": self._hiding["state"],
            "animation_progress": self._hiding["progress"],
            "enter_animation_duration": self.ENTER_ANIMATION_DURATION,
            "exit_animation_duration": self.EXIT_ANIMATION_DURATION,
            "view_fov": self.HIDDEN_VIEW_FOV if hidden else self.NORMAL_VIEW_FOV,
            "normal_view_fov": self.NORMAL_VIEW_FOV,
        }

    def exit_hiding(self, dt=0.0):
        if self._hiding["state"] in ("entering", "hidden"):
            self._hiding["state"] = "exiting"
            self._hiding["progress"] = 0.0
        self._update_hiding_animation(False, None, dt)
        return dict(self._hiding)

    def _update_hiding_animation(self, valid, spot, dt):
        hiding = self._hiding
        if valid and hiding["state"] == "outside":
            hiding.update(spot=spot, state="entering", progress=0.0)
        if hiding["state"] == "entering" and dt:
            hiding["progress"] = min(
                1.0, hiding["progress"] + dt / self.ENTER_ANIMATION_DURATION)
            if hiding["progress"] >= 1.0:
                hiding["state"] = "hidden"
        elif hiding["state"] == "exiting" and dt:
            hiding["progress"] = min(
                1.0, hiding["progress"] + dt / self.EXIT_ANIMATION_DURATION)
            if hiding["progress"] >= 1.0:
                hiding.update(spot=None, state="outside", progress=0.0)

    # ------------------------------------------------------------------
    # Alertness: decay + levels + sharing between enemies
    # ------------------------------------------------------------------
    @classmethod
    def alert_level(cls, value):
        if value >= 75.0:
            return "combat"
        if value >= 50.0:
            return "alert"
        if value >= 25.0:
            return "suspicious"
        return "calm"

    def update_alertness(self, enemy_id="default", detected=False, dt=1.0,
                         **kwargs):
        detected = bool(detected or kwargs.get("spotted", False)
                        or kwargs.get("visible", False))
        value = self._alertness.get(enemy_id,
                                    self._shared_alert * self.share_factor)
        if detected:
            value = min(100.0, value + self.ALERTNESS_GAIN * dt)
            self._shared_alert = min(100.0, max(self._shared_alert, value))
        else:
            value = max(0.0, value - self.decay_rate * dt)
            self._shared_alert = max(
                0.0, self._shared_alert - self.decay_rate * 0.5 * dt)
            value = max(value, self._shared_alert * self.share_factor)
        self._alertness[enemy_id] = value
        return {
            "enemy_id": enemy_id,
            "alertness": value,
            "level": self.alert_level(value),
            "shared_alertness": self._shared_alert,
        }

    # ------------------------------------------------------------------
    # Score: time bonus + no-kill (ghost) bonus + combo multiplier
    # ------------------------------------------------------------------
    def calculate_stealth_score(self, base_score=1000, time_taken=None,
                              par_time=300.0, kills=0, combo=0, **kwargs):
        if time_taken is None:
            time_taken = kwargs.get("elapsed_time", kwargs.get("time", par_time))
        par_time = kwargs.get("target_time", par_time)
        kills = kwargs.get("kill_count", kills)
        combo = kwargs.get("streak", kwargs.get("stealth_combo", combo))

        time_bonus = max(0.0, float(par_time) - float(time_taken)) * 2.0
        ghost_bonus = 500.0 if kills == 0 else 0.0
        kill_penalty = 100.0 * kills
        combo_multiplier = 1.0 + 0.1 * max(0, int(combo))

        total = (float(base_score) + time_bonus + ghost_bonus
                 - kill_penalty) * combo_multiplier
        return max(0, int(round(total)))
