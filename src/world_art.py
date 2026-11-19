# --- Imports ---
import math
from pathlib import Path

from kivy.clock import Clock
from kivy.graphics import Color, Ellipse, RoundedRectangle, Line
from kivy.utils import get_color_from_hex
from src.visual_effects import night_strength, particle_position, make_burst
from kivy.metrics import dp
from kivy.uix.image import Image
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.scrollview import ScrollView

from src.game_state import read_json


# --- Interactive Sprite ---
class WorldSprite(Image):
    def __init__(self, identifier, on_select=None, **kwargs):
        super().__init__(**kwargs)
        self.identifier = identifier
        self.on_select = on_select
        self.touch_origin = None

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self.touch_origin = touch.pos
        return super().on_touch_down(touch)

    def on_touch_up(self, touch):
        if self.touch_origin is not None:
            ox, oy = self.touch_origin
            self.touch_origin = None
            if (math.hypot(touch.x - ox, touch.y - oy) <= dp(12)
                    and self.collide_point(*touch.pos) and self.on_select):
                self.on_select(self.identifier)
                return True
        return super().on_touch_up(touch)


# --- Settlement Artwork ---
class SettlementScene(RelativeLayout):
    def __init__(self, root_dir, state, on_select=None, **kwargs):
        super().__init__(size_hint=(None, 1), **kwargs)
        self.art = read_json(Path(root_dir) / 'config' / 'art.json')
        self.state = state
        self.root_dir = Path(root_dir)
        self.on_select = on_select
        self.animated = []
        self.citizens = []
        self.elapsed = 0.0
        self.effects = self.art["effects"]
        self.particles = []
        self.pulse = None
        self._populate()
        self.animation_clock = Clock.schedule_interval(self._animate, 1 / self.art['world']['animation_fps'])

    def _image(self, name, pos_hint, size_hint, identifier=None):
        source = self.root_dir / 'data' / 'art' / 'png' / (name + '.png')
        kwargs = dict(source=str(source), pos_hint=pos_hint, size_hint=size_hint,
                      allow_stretch=True, keep_ratio=False)
        if identifier:
            return WorldSprite(identifier=identifier, on_select=self.on_select, **kwargs)
        return Image(**kwargs)

    def _populate(self):
        self.clear_widgets()
        self.animated.clear()
        self._make_citizens()
        tiles = self.art['world']['background_tiles']
        for index in range(tiles):
            self.add_widget(self._image(self.art['scene']['image'],
                                        {'x': index / tiles, 'y': 0}, (1 / tiles, 1)))
        for entry in self.art['decorations']:
            if entry.get('requires') and not self.state.buildings.get(entry['requires'], 0):
                continue
            sprite = self._image(entry['image'], {'x': entry['x'], 'y': entry['y']},
                                 (entry['width'], entry['height']), entry['id'])
            self.add_widget(sprite)
            if entry.get('animation'):
                self.animated.append((sprite, entry['y'], entry['animation']))

    def _make_citizens(self):
        self.citizens = []
        config = self.art['citizens']
        with self.canvas.after:
            self.canvas.after.clear()
            for index in range(min(self.state.population, config['max_visible'])):
                color = config['colors'][index % len(config['colors'])].lstrip('#')
                rgb = tuple(int(color[start:start + 2], 16) / 255 for start in (0, 2, 4))
                Color(*rgb, 1)
                body = RoundedRectangle(radius=[dp(config["corner_radius_dp"])])
                Color(*(int(config["head_color"].lstrip("#")[start:start + 2], 16) / 255 for start in (0, 2, 4)), 1)
                head = Ellipse()
                self.citizens.append((body, head, index))
        self._position_citizens()

    def _position_citizens(self):
        config = self.art['citizens']
        for body, head, index in self.citizens:
            movement = config['walk_amplitude'] * math.sin(self.elapsed * config['animation_speed'] + index)
            x = self.x + self.width * (config['starting_x'] + index * config['spacing_x'] + movement)
            y = self.y + self.height * (config['base_y'] + config["vertical_bob"] * math.sin(self.elapsed * config["vertical_speed"] + index))
            width = max(dp(config["min_body_width_dp"]), self.width * config['body_width'])
            height = self.height * config['body_height']
            body.pos = (x, y)
            body.size = (width, height)
            head.size = (max(dp(config["min_head_size_dp"]), self.width * config['head_size']),) * 2
            head.pos = (x - width * config["head_horizontal_offset"], y + height * config["head_vertical_offset"])

    def refresh_buildings(self):
        self._populate()

    def on_size(self, *_):
        if hasattr(self, "citizens"):
            self._position_citizens()

    def _animate(self, dt):
        self.elapsed += min(dt, self.art['world']['max_animation_step'])
        self._position_citizens()
        self._render_effects(dt)
        for sprite, y, kind in self.animated:
            motion = self.art['animations'][kind]
            phase = self.elapsed * motion['speed'] + motion['phase']
            sprite.opacity = motion['opacity_base'] + motion['opacity_range'] * math.sin(phase)
            sprite.pos_hint = {'x': sprite.pos_hint['x'],
                               'y': y + motion['bob'] * math.sin(phase)}

    # --- Animated Atmosphere And Sparks ---
    def celebrate(self, origin=None):
        if not self.effects["enabled"]:
            return
        origin = origin or (self.center_x, self.y + self.height * 0.65)
        self.particles = [(point, speed, color, 0.0) for point, speed, color
                          in make_burst(origin, self.effects)]
        self.pulse = (origin, 0.0)

    def _render_effects(self, dt):
        with self.canvas.after:
            self.canvas.after.clear()
            opacity = night_strength(self.elapsed, self.effects["day_cycle_seconds"],
                                     self.effects["night_overlay_opacity"])
            Color(0.06, 0.10, 0.25, opacity)
            RoundedRectangle(pos=self.pos, size=self.size)
            for index in range(self.effects["ambient_count"]):
                phase = (index * 0.61803398875 + self.elapsed * self.effects["ambient_speed"]) % 1
                x = self.x + self.width * phase
                y = self.y + self.height * (0.30 + 0.47 * ((index * 0.414213562) % 1))
                Color(1.0, 0.83, 0.51, self.effects["ambient_opacity"])
                radius = dp(self.effects["ambient_radius_dp"])
                Ellipse(pos=(x, y), size=(radius * 2, radius * 2))
            alive = []
            for origin, velocity, color, age in self.particles:
                age += dt
                life = self.effects["spark_lifetime"]
                if age >= life:
                    continue
                x, y = particle_position(origin, (dp(velocity[0]), dp(velocity[1])), age,
                                         dp(self.effects["spark_gravity_dp"]))
                rgba = get_color_from_hex(color)
                Color(*rgba[:3], (1 - age / life) * rgba[3])
                radius = dp(self.effects["spark_radius_dp"]) * (1 - age / life)
                Ellipse(pos=(x - radius, y - radius), size=(2 * radius, 2 * radius))
                alive.append((origin, velocity, color, age))
            self.particles = alive
            if self.pulse:
                origin, age = self.pulse
                age += dt
                life = self.effects["pulse_lifetime"]
                if age >= life:
                    self.pulse = None
                else:
                    Color(1, .85, .51, 1 - age / life)
                    Line(circle=(origin[0], origin[1], dp(self.effects["pulse_radius_dp"]) * age / life),
                         width=dp(self.effects["pulse_width_dp"]))
                    self.pulse = (origin, age)

    def on_parent(self, instance, parent):
        if parent is None and hasattr(self, 'animation_clock'):
            self.animation_clock.cancel()


# --- Horizontal Camera ---
class WorldViewport(ScrollView):
    def __init__(self, root_dir, state, on_select=None, **kwargs):
        art = read_json(Path(root_dir) / 'config' / 'art.json')
        self.art = art
        super().__init__(do_scroll_x=True, do_scroll_y=False, bar_width=dp(art['world']['scrollbar_dp']),
                         size_hint_y=None, height=dp(art['world']['height_dp']), **kwargs)
        self.scene = SettlementScene(root_dir, state, on_select=on_select)
        self.add_widget(self.scene)
        self.bind(width=self._resize, height=self._resize)
        Clock.schedule_once(self._resize, 0)

    def _resize(self, *_):
        scene_width = max(self.width * self.art['world']['width_multiplier'],
                          dp(self.art['world']['min_width_dp']))
        self.scene.width = scene_width
        self.scene.height = self.height

    def refresh_buildings(self):
        self.scene.refresh_buildings()
