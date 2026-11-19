# --- Imports ---
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, RoundedRectangle
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.utils import get_color_from_hex, platform

from src.game_state import read_json
from src.world_art import WorldViewport
from src.audio import AudioFeedback
from src.layout import viewport_layout


# --- Panel ---
class Panel(BoxLayout):
    def __init__(self, fill, radius, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(*get_color_from_hex(fill))
            self.bg = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(radius)])
        self.bind(pos=self._sync_bg, size=self._sync_bg)

    def _sync_bg(self, *_):
        self.bg.pos = self.pos
        self.bg.size = self.size


# --- Rounded Touch Button ---
class RoundedButton(Button):
    def __init__(self, fill, radius, **kwargs):
        super().__init__(background_normal="", background_down="", background_color=(0, 0, 0, 0), **kwargs)
        with self.canvas.before:
            self.fill_instruction = Color(*get_color_from_hex(fill))
            self.rounded_background = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(radius)])
        self.bind(pos=self._sync_background, size=self._sync_background, state=self._touch_state)

    def _sync_background(self, *_):
        self.rounded_background.pos = self.pos
        self.rounded_background.size = self.size

    def _touch_state(self, *_):
        self.fill_instruction.a = self.opacity * (0.78 if self.state == "down" else 1)


# --- Mobile Application ---
class SumerianApp(App):
    def __init__(self, state, root_dir, **kwargs):
        super().__init__(**kwargs)
        self.state = state
        self.gui = read_json(root_dir / "config" / "gui.json")
        self.colors = self.gui["colors"]
        self.settings = state.settings
        self.current_page = "City"
        self.archive_filter = "All"
        self.archive_offset = 0
        self.discovery_tab = "Research"
        self.legacy_tab = "Achievements"
        self.civilization_tab = "Eras"
        self.notice = ""
        self.sound = AudioFeedback(root_dir, self.gui["sound"])
        self._notice_elapsed = 0.0
        self._autosave_elapsed = 0.0
        self._last_population = state.population

    def build(self):
        self.title = self.settings["app_name"]
        if platform not in ("android", "ios"):
            Window.size = self.settings["desktop_preview"]
        Window.clearcolor = get_color_from_hex(self.colors["background"])
        Window.softinput_mode = self.settings["display"]["softinput_mode"]
        self.screen = BoxLayout(orientation="vertical", padding=dp(self.settings["screen_padding_dp"]),
                                spacing=dp(self.settings["spacing_dp"]))
        Clock.schedule_interval(self._tick, 1 / self.settings["ticks_per_second"])
        if self.state.offline_summary:
            self.notice = "OFFLINE: " + ", ".join(f"+{int(amount)} {resource}" for resource, amount in self.state.offline_summary.items())
        Window.bind(size=self._on_viewport_change)
        self.render()
        return self.screen

    def _on_viewport_change(self, *_):
        if hasattr(self, "screen"):
            Clock.unschedule(self._render_viewport)
            Clock.schedule_once(self._render_viewport, 0)

    def _render_viewport(self, *_):
        self.render()

    def _layout(self):
        return viewport_layout(Window.width / dp(1), Window.height / dp(1), self.gui)

    def label(self, value, size="body", color="text", **kwargs):
        label = Label(text=str(value), font_size=dp(self.gui["font_size"][size]),
                      color=get_color_from_hex(self.colors[color]), halign="center", valign="middle", **kwargs)
        label.bind(size=lambda instance, _: setattr(instance, "text_size", instance.size))
        return label

    def button(self, text, action, accent=False, **kwargs):
        font_size = kwargs.pop("font_size", dp(self.gui["font_size"]["body"]))
        button = RoundedButton(self.colors["secondary" if accent else "button"],
                               self.gui["button_radius_dp"], text=text,
                               color=get_color_from_hex(self.colors["background"] if accent else self.colors["text"]),
                               font_size=font_size, **kwargs)
        button.bind(on_release=lambda *_: action())
        return button

    def _tick(self, delta):
        self._autosave_elapsed += delta
        if self._autosave_elapsed >= self.settings["autosave_seconds"]:
            self.state.save()
            self._autosave_elapsed = 0.0
        if self.notice:
            self._notice_elapsed += delta
            limit = (self.gui["feedback"]["achievement_duration_seconds"] if self.notice.startswith("ACHIEVEMENT")
                     else self.gui["feedback"]["toast_duration_seconds"])
            if self._notice_elapsed >= limit:
                self.notice = ""
                self._notice_elapsed = 0.0
                self.render()
        unlocked = self.state.advance(delta)
        if unlocked:
            self._feedback("achievement", "ACHIEVEMENT: " + ", ".join(unlocked))
            self.state.save()
        if unlocked or self._last_population != self.state.population or (self.current_page == "Discover" and self.discovery_tab == "Explore"):
            self.render()
        elif hasattr(self, "resource_label"):
            self.resource_label.text = self._resource_text()

    # --- Feedback ---
    def _feedback(self, kind, message):
        self.notice = message
        self._notice_elapsed = 0.0
        self.sound.play(kind)
        if kind in ("achievement", "build", "research") and hasattr(self, "world_view"):
            self.world_view.scene.celebrate()

    def _tap(self):
        unlocked = self.state.tap()
        self._feedback("achievement" if unlocked else "tap", "ACHIEVEMENT: " + ", ".join(unlocked) if unlocked else "+ Barley harvested")
        self.state.save()
        self.render()

    def _build(self, name):
        successful, unlocked = self.state.build(name)
        self._feedback("achievement" if unlocked else "build" if successful else "error",
                       "ACHIEVEMENT: " + ", ".join(unlocked) if unlocked else "Building constructed" if successful else "Not enough resources")
        self.state.save()
        self.render()

    def _select_world(self, identifier):
        data = self.state.buildings_data.get(identifier)
        if data:
            self.notice = f"{data['name']}: {self.state.buildings[identifier]} built"
        else:
            self.notice = self.gui["world_labels"].get(identifier, identifier.title())
        self.render()

    def _assign(self, name, delta):
        success, unlocked = self.state.assign_worker(name, delta)
        self.notice = ("ACHIEVEMENT: " + ", ".join(unlocked) if unlocked else
                       "Workforce updated" if success else "Assignment unavailable")
        self.state.save()
        self.render()

    # --- Civilization Actions ---
    def _civilization_action(self, method, identifier=None):
        success, unlocked = getattr(self.state, method)(identifier) if identifier is not None else getattr(self.state, method)()
        self._feedback("achievement" if unlocked else "research" if success else "error",
                       "ACHIEVEMENT: " + ", ".join(unlocked) if unlocked else "Progress recorded" if success else "Requirements not met")
        if success:
            self.state.save()
        self.render()

    def _legacy_tab(self, choice):
        self.legacy_tab = choice
        self.render()

    def _civilization_tab(self, choice):
        self.civilization_tab = choice
        self.render()

    # --- Discovery Actions ---
    def _research(self, identifier):
        success, unlocked = self.state.research(identifier)
        self._feedback("achievement" if unlocked else "research" if success else "error",
                       "ACHIEVEMENT: " + ", ".join(unlocked) if unlocked else
                       "Research completed" if success else "Requirements not met")
        if success:
            self.state.save()
        self.render()

    def _expedition(self, identifier):
        success = self.state.start_expedition(identifier)
        self._feedback("research" if success else "error",
                       "Expedition started" if success else "Requirements not met or expedition active")
        if success:
            self.state.save()
        self.render()

    def _discovery_tab(self, tab):
        self.discovery_tab = tab
        self.render()

    def _resource_text(self):
        entries = [f"{key.title()}: {int(value):,}/{int(self.state.capacity(key)):,}" for key, value in self.state.resources.items()]
        pivot = (len(entries) + 1) // self.gui["resource_rows"]
        return "    ".join(entries[:pivot]) + "\n" + "    ".join(entries[pivot:])

    def _page(self, page):
        self.current_page = page
        self.notice = ""
        self.render()

    def render(self):
        self._last_population = self.state.population
        previous_scroll = self.scroll.scroll_y if hasattr(self, "scroll") else 1
        previous_camera = self.world_view.scroll_x if hasattr(self, "world_view") else 0
        self.screen.clear_widgets()
        spacing = dp(self.settings["spacing_dp"])
        layout = self._layout()
        header = Panel(self.colors["panel"], self.gui["corner_radius_dp"], orientation="vertical",
                       size_hint_y=None, height=dp(layout["header_dp"]), padding=spacing)
        header.add_widget(self.label(self.settings["title"], "title"))
        header.add_widget(self.label(self.settings["subtitle"], "small", "muted"))
        self.resource_label = self.label(self._resource_text(), "small", "secondary")
        header.add_widget(self.resource_label)
        self.screen.add_widget(header)

        if self.notice:
            self.screen.add_widget(self.label(self.notice, "small", "success", size_hint_y=None, height=dp(self.gui["feedback"]["toast_height_dp"])))

        scroll = ScrollView(do_scroll_x=False, bar_width=dp(3))
        content = BoxLayout(orientation="vertical", size_hint_y=None, spacing=spacing, padding=[0, spacing])
        content.bind(minimum_height=content.setter("height"))
        if self.current_page == "City":
            self.city(content)
            Clock.schedule_once(lambda *_: setattr(self.world_view, "scroll_x", previous_camera), 0)
        elif self.current_page == "Build":
            self.buildings_view(content)
        elif self.current_page == "People":
            self.people_view(content)
        elif self.current_page == "Discover":
            self.discovery_view(content)
        else:
            self.legacy_view(content)
        scroll.add_widget(content)
        self.scroll = scroll
        Clock.schedule_once(lambda *_: setattr(scroll, "scroll_y", previous_scroll), 0)
        self.screen.add_widget(scroll)

        footer = BoxLayout(size_hint_y=None, height=dp(layout["footer_dp"]), spacing=spacing)
        for page in self.gui["progression_page_names"]:
            footer.add_widget(self.button(layout["navigation"][page], lambda chosen=page: self._page(chosen), accent=self.current_page == page,
                                          font_size=dp(self.gui["font_size"]["small"])))
        self.screen.add_widget(footer)

    def city(self, content):
        content.add_widget(self.label(f"YOUR RIVERSIDE SETTLEMENT  |  {self.state.population}/{self.state.housing_capacity()} CITIZENS", "heading", size_hint_y=None, height=dp(48)))
        content.add_widget(self.label("Swipe to explore. Tap buildings to inspect.", "small", "muted", size_hint_y=None, height=dp(34)))
        self.world_view = WorldViewport(self.state.root, self.state, on_select=self._select_world)
        if self._layout()["scene_dp"] is not None:
            self.world_view.height = dp(self._layout()["scene_dp"])
        content.add_widget(self.world_view)
        content.add_widget(self.label("THE TWO RIVERS  |  A CITY IN THE MAKING", "small", "secondary",
                                      size_hint_y=None, height=dp(self.gui["scene_caption_height_dp"])))
        grid = GridLayout(cols=self._layout()["columns"], size_hint_y=None, spacing=dp(self.settings["spacing_dp"]))
        grid.bind(minimum_height=grid.setter("height"))
        for key, data in self.state.buildings_data.items():
            quantity = self.state.buildings[key]
            card = Panel(self.colors["card"], self.gui["corner_radius_dp"], orientation="vertical",
                         size_hint_y=None, height=dp(self.gui["card_height_dp"]), padding=dp(8))
            card.add_widget(self.label(data["name"], "heading"))
            card.add_widget(self.label(data["description"], "small", "muted"))
            card.add_widget(self.label(f"Built: {quantity}", "body", "secondary"))
            staffed = self.state.workforce().get(key, 0)
            output = (f"+{staffed * data['rate']:.1f} {data['produces']}/s" if data.get("produces")
                      else "Housing or storage")
            card.add_widget(self.label(output, "small", "text"))
            grid.add_widget(card)
        content.add_widget(grid)
        content.add_widget(self.button("HARVEST BARLEY  +" + str(self.settings["base_tap_yield"]), self._tap,
                                       accent=True, size_hint_y=None, height=dp(self.settings["min_touch_dp"])))

    def buildings_view(self, content):
        content.add_widget(self.label("BUILD YOUR CITY", "heading", size_hint_y=None, height=dp(50)))
        for key, data in self.state.buildings_data.items():
            card = Panel(self.colors["panel"], self.gui["corner_radius_dp"], orientation="vertical",
                         size_hint_y=None, height=dp(self.gui["card_height_dp"]), padding=dp(8))
            card.add_widget(self.label(data["name"] + "  ·  Level " + str(self.state.buildings[key]), "heading"))
            detail = ", ".join(f"{amount:g} {resource}/s" for resource, amount in data.get("consumes", {}).items())
            card.add_widget(self.label("Uses: " + detail if detail else data["description"], "small", "muted"))
            price = ", ".join(f"{item}: {amount}" for item, amount in self.state.cost(key).items())
            card.add_widget(self.button("BUILD  " + price, lambda chosen=key: self._build(chosen), accent=True))
            content.add_widget(card)

    def people_view(self, content):
        content.add_widget(self.label(f"CITIZENS  {self.state.population}/{self.state.housing_capacity()}",
                                      "heading", size_hint_y=None, height=dp(54)))
        content.add_widget(self.label("Build homes to grow. Feed families bread and barley.",
                                      "small", "muted", size_hint_y=None, height=dp(44)))
        assigned = self.state.workforce()
        content.add_widget(self.label(f"Working: {sum(assigned.values())}  |  Available: {self.state.population - sum(assigned.values())}",
                                      "body", "secondary", size_hint_y=None, height=dp(40)))
        for key, data in self.state.buildings_data.items():
            if not data.get("produces"):
                continue
            card = Panel(self.colors["panel"], self.gui["corner_radius_dp"], orientation="vertical",
                         size_hint_y=None, height=dp(112), padding=dp(8))
            card.add_widget(self.label(f"{data['name']}  {assigned.get(key, 0)}/{self.state.buildings[key]} staffed",
                                       "body"))
            actions = BoxLayout(spacing=dp(8))
            actions.add_widget(self.button("-", lambda chosen=key: self._assign(chosen, -1)))
            actions.add_widget(self.label(f"Pinned: {self.state.assignments.get(key, 0)}", "small"))
            actions.add_widget(self.button("+", lambda chosen=key: self._assign(chosen, 1), accent=True))
            card.add_widget(actions)
            content.add_widget(card)

    # --- Research, Expeditions, Artifacts ---
    def discovery_view(self, content):
        content.add_widget(self.label("DISCOVER MESOPOTAMIA", "heading", size_hint_y=None,
                                      height=dp(self.gui["progression_heading_height_dp"])))
        tabs = BoxLayout(size_hint_y=None, height=dp(self.settings["min_touch_dp"]), spacing=dp(6))
        for tab in ("Research", "Explore", "Artifacts"):
            tabs.add_widget(self.button(tab, lambda chosen=tab: self._discovery_tab(chosen),
                                        accent=self.discovery_tab == tab))
        content.add_widget(tabs)
        if self.discovery_tab == "Research":
            content.add_widget(self.label(f"KNOWLEDGE  {len(self.state.researched)}/{len(self.state.research_data)}",
                                          "body", "secondary", size_hint_y=None, height=dp(38)))
            for item in self.state.research_data:
                complete = item["id"] in self.state.researched
                card = Panel(self.colors["panel"], self.gui["corner_radius_dp"], orientation="vertical",
                             size_hint_y=None, height=dp(self.gui["progression_card_height_dp"]), padding=dp(8))
                card.add_widget(self.label(("LEARNED  " if complete else "RESEARCH  ") + item["name"], "body",
                                           "success" if complete else "text"))
                card.add_widget(self.label(item["description"], "small", "muted"))
                requirement = ", ".join(item["requires"]) or "None"
                cost = ", ".join(f"{key}: {amount}" for key, amount in item["cost"].items())
                card.add_widget(self.label("Requires: " + requirement.replace("_", " "), "small", "secondary"))
                if not complete:
                    card.add_widget(self.button("RESEARCH  " + cost, lambda chosen=item["id"]: self._research(chosen),
                                                accent=True))
                content.add_widget(card)
        elif self.discovery_tab == "Explore":
            active = self.state.active_expedition
            status = (f"Expedition: {active.replace('_', ' ')}  |  {int(self.state.expedition_remaining)}s left"
                      if active else "No expedition active")
            content.add_widget(self.label(status, "body", "secondary", size_hint_y=None, height=dp(42)))
            for item in self.state.expedition_data:
                card = Panel(self.colors["panel"], self.gui["corner_radius_dp"], orientation="vertical",
                             size_hint_y=None, height=dp(self.gui["progression_card_height_dp"]), padding=dp(8))
                card.add_widget(self.label(item["name"], "body"))
                card.add_widget(self.label(item["description"], "small", "muted"))
                card.add_widget(self.label("Needs: " + (", ".join(item["requires"]) or "None"), "small", "secondary"))
                cost = ", ".join(f"{key}: {amount}" for key, amount in item["cost"].items())
                card.add_widget(self.button("EXPLORE  " + cost, lambda chosen=item["id"]: self._expedition(chosen),
                                            accent=True))
                content.add_widget(card)
        else:
            content.add_widget(self.label(f"ARTIFACTS  {len(self.state.artifacts)}/{len(self.state.artifact_data)}",
                                          "body", "secondary", size_hint_y=None, height=dp(42)))
            for item in self.state.artifact_data:
                found = item["id"] in self.state.artifacts
                card = Panel(self.colors["card"], self.gui["corner_radius_dp"], orientation="vertical",
                             size_hint_y=None, height=dp(100), padding=dp(8))
                card.add_widget(self.label(item["name"] if found else "Undiscovered artifact", "body",
                                           "success" if found else "text"))
                card.add_widget(self.label(item["description"] if found else "Explore to uncover its story",
                                           "small", "muted"))
                content.add_widget(card)

    # --- Civilization Interface ---
    def legacy_view(self, content):
        tabs = BoxLayout(size_hint_y=None, height=dp(self.settings["min_touch_dp"]))
        for item in self.gui["legacy_tabs"]:
            tabs.add_widget(self.button(item, lambda choice=item: self._legacy_tab(choice),
                                        accent=self.legacy_tab == item))
        content.add_widget(tabs)
        if self.legacy_tab == "Achievements":
            self.achievements_view(content)
        else:
            self.civilization_view(content)

    def civilization_view(self, content):
        content.add_widget(self.label(self.state.era()["name"].upper(), "heading", size_hint_y=None, height=dp(48)))
        content.add_widget(self.label(f"Royal renown: {self.state.renown}  |  Legacy rank: {self.state.legacy_rank()}",
                                      "body", "secondary", size_hint_y=None, height=dp(44)))
        tabs = BoxLayout(size_hint_y=None, height=dp(self.settings["min_touch_dp"]))
        for item in self.gui["civilization_tabs"]:
            tabs.add_widget(self.button(item, lambda choice=item: self._civilization_tab(choice),
                                        accent=self.civilization_tab == item))
        content.add_widget(tabs)
        if self.civilization_tab == "Eras":
            entries = self.state.era_data
        elif self.civilization_tab == "Monuments":
            entries = self.state.monument_data
        else:
            entries = self.state.quest_data
        for index, item in enumerate(entries):
            card = Panel(self.colors["panel"], self.gui["corner_radius_dp"], orientation="vertical",
                         size_hint_y=None, height=dp(self.gui["progression_card_height_dp"]), padding=dp(8))
            card.add_widget(self.label(item["name"], "heading"))
            card.add_widget(self.label(item["description"], "small", "muted"))
            if self.civilization_tab == "Eras":
                complete = index <= self.state.era_index
                allowed = index == self.state.era_index + 1
                action = lambda: self._civilization_action("advance_era")
                status = "CURRENT / COMPLETED" if complete else "LOCKED" if not allowed else "ADVANCE"
            elif self.civilization_tab == "Monuments":
                complete = item["id"] in self.state.monuments
                action = lambda ident=item["id"]: self._civilization_action("construct_monument", ident)
                status = "CONSTRUCTED" if complete else "BUILD MONUMENT"
            else:
                complete = item["id"] in self.state.completed_quests
                action = lambda ident=item["id"]: self._civilization_action("claim_quest", ident)
                progress = min(item["target"], self.state.counters.get(item["event"], 0))
                card.add_widget(self.label(f"Progress: {int(progress)}/{item['target']}", "small", "secondary"))
                status = "COMPLETED" if complete else "CLAIM COMMISSION"
            if not complete:
                cost = ", ".join(f"{key}: {amount}" for key, amount in item["cost"].items())
                card.add_widget(self.button(status + ("  " + cost if cost else ""), action, accent=True))
            else:
                card.add_widget(self.label(status, "small", "success"))
            content.add_widget(card)

    # --- Archive Navigation ---
    def _archive_filter(self, category):
        self.archive_filter = category
        self.archive_offset = 0
        self.render()

    def _archive_more(self):
        self.archive_offset += self.gui["archive_page_size"]
        self.render()

    def achievements_view(self, content):
        total = len(self.state.achievement_data)
        count = len(self.state.unlocked)
        content.add_widget(self.label(f"LEGACY ARCHIVE   {count}/{total}   |   {self.state.legacy_points()} points",
                                      "heading", size_hint_y=None, height=dp(54)))
        content.add_widget(self.label(f"Collections: {len(self.state.completed_collections)}/{len(self.state.collection_data)}"
                                      f"    |    Relics: {len(self.state.cosmetics)}",
                                      "small", "secondary", size_hint_y=None, height=dp(36)))
        filter_scroll = ScrollView(size_hint_y=None, height=dp(self.gui["archive_filter_height_dp"]),
                                   do_scroll_y=False, bar_width=dp(2))
        filters = BoxLayout(orientation="horizontal", size_hint_x=None, spacing=dp(6))
        filters.bind(minimum_width=filters.setter("width"))
        for category in self.gui["archive_filters"]:
            filters.add_widget(self.button(category, lambda choice=category: self._archive_filter(choice),
                                           accent=self.archive_filter == category,
                                           size_hint_x=None, width=dp(max(72, len(category)*11))))
        filter_scroll.add_widget(filters)
        content.add_widget(filter_scroll)
        if self.archive_filter == "All":
            content.add_widget(self.label("COLLECTIONS", "heading", size_hint_y=None, height=dp(42)))
            for collection in self.state.collection_data:
                progress, target = self.state.collection_progress(collection)
                completed = collection["id"] in self.state.completed_collections
                card = Panel(self.colors["card"], self.gui["corner_radius_dp"], orientation="vertical",
                             size_hint_y=None, height=dp(self.gui["archive_collection_height_dp"]), padding=dp(8))
                card.add_widget(self.label(("COMPLETE  " if completed else "COLLECTION  ") + collection["name"], "body",
                                           "success" if completed else "text"))
                card.add_widget(self.label(collection["description"], "small", "muted"))
                card.add_widget(self.label(f"{progress}/{target}  |  Reward: {collection['reward_cosmetic'].replace('_',' ').title()}",
                                           "small", "secondary"))
                content.add_widget(card)
        matching = [item for item in self.state.achievement_data
                    if self.archive_filter == "All" or item.get("category") == self.archive_filter]
        matching.sort(key=lambda item: (item["id"] not in self.state.unlocked,
                                        -min(1, self.state.achievement_progress(item)[0] / item["target"])))
        visible = matching[:self.archive_offset + self.gui["archive_page_size"]]
        content.add_widget(self.label(f"ACHIEVEMENTS  {len(visible)}/{len(matching)}", "heading",
                                      size_hint_y=None, height=dp(42)))
        for achievement in visible:
            achieved = achievement["id"] in self.state.unlocked
            hidden = achievement.get("hidden", False) and not achieved
            progress, target = self.state.achievement_progress(achievement)
            card = Panel(self.colors["panel"], self.gui["corner_radius_dp"], orientation="vertical",
                         size_hint_y=None, height=dp(self.gui["archive_card_height_dp"]), padding=dp(8))
            card.add_widget(self.label(("UNLOCKED  " if achieved else "SECRET  " if hidden else "LOCKED  ") +
                                       ("???" if hidden else achievement["name"]), "body",
                                       "success" if achieved else "text"))
            card.add_widget(self.label("Undiscovered milestone" if hidden else achievement["description"],
                                       "small", "muted"))
            card.add_widget(self.label("Hidden progress" if hidden else
                                       f"{int(progress):,}/{target:,}  |  {achievement['tier']}  |  {achievement['points']} pts",
                                       "small", "secondary"))
            cosmetic = achievement.get("reward_cosmetic")
            if cosmetic and not hidden:
                card.add_widget(self.label("Relic: " + cosmetic.replace("_", " ").title(), "small", "secondary"))
            content.add_widget(card)
        if len(visible) < len(matching):
            content.add_widget(self.button("SHOW MORE ACHIEVEMENTS", self._archive_more, accent=True,
                                           size_hint_y=None, height=dp(self.settings["min_touch_dp"])))

    def on_pause(self):
        self.state.save()
        return True

    def on_stop(self):
        self.state.save()
        Window.unbind(size=self._on_viewport_change)
