# --- Imports ---
import copy
import json
import math
import os
import tempfile
import time
from pathlib import Path


# --- Configuration ---
def read_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


# --- State Engine ---
class GameState:
    def __init__(self, root, save_path=None, clock=None):
        self.root = Path(root)
        self.settings = read_json(self.root / "config" / "settings.json")
        self.buildings_data = read_json(self.root / "data" / "buildings.json")
        self.achievement_data = read_json(self.root / "data" / "achievements.json")
        self.collection_data = read_json(self.root / "data" / "collections.json")
        self.research_data = read_json(self.root / "data" / "research.json")
        self.expedition_data = read_json(self.root / "data" / "expeditions.json")
        self.artifact_data = read_json(self.root / "data" / "artifacts.json")
        self.era_data = read_json(self.root / "data" / "eras.json")
        self.monument_data = read_json(self.root / "data" / "monuments.json")
        self.quest_data = read_json(self.root / "data" / "royal_quests.json")
        self.clock = clock or time.time
        self.save_path = Path(save_path) if save_path else Path.home() / self.settings["save_file"]
        self.resources = copy.deepcopy(self.settings["starting_resources"])
        self.buildings = copy.deepcopy(self.settings["starting_buildings"])
        self.population = self.settings["starting_population"]
        self.assignments = copy.deepcopy(self.settings["starting_assignments"])
        self.population_timer = 0.0
        self.food_timer = 0.0
        self.counters = {}
        self.unlocked = []
        self.completed_collections = []
        self.cosmetics = []
        self.researched = []
        self.artifacts = []
        self.era_index = 0
        self.monuments = []
        self.completed_quests = []
        self.renown = 0
        self.active_expedition = None
        self.expedition_remaining = 0.0
        self.last_update = self.clock()
        self.offline_summary = {}
        self.load()
        elapsed = min(max(0, self.clock() - self.last_update), self.settings["offline_cap_seconds"])
        if elapsed >= self.settings["offline_report_threshold_seconds"]:
            before = self.resources.copy()
            self.advance(elapsed, offline=True)
            self.offline_summary = {key: round(self.resources[key] - before[key], 2)
                                    for key in self.resources if self.resources[key] > before[key]}
        elif elapsed > 0:
            self.advance(elapsed)
        self.last_update = self.clock()

    def capacity(self, resource):
        base = self.settings["storage_limits"].get(resource, 0)
        granaries = self.buildings.get("granary", 0)
        return round(base * self.settings["storage_upgrade_multiplier"] ** granaries, 6)

    def _add(self, resource, amount):
        available = max(0, self.capacity(resource) - self.resources.get(resource, 0))
        actual = min(max(0, amount), available)
        self.resources[resource] = self.resources.get(resource, 0) + actual
        return actual

    def housing_capacity(self):
        return (self.settings["population_base_capacity"] +
                self.buildings.get("house", 0) * self.settings["housing_capacity_per_home"])

    def workforce(self):
        jobs = [name for name, data in self.buildings_data.items() if data.get("produces")]
        assigned = {name: min(self.buildings.get(name, 0), max(0, int(self.assignments.get(name, 0))))
                    for name in jobs}
        occupied = sum(assigned.values())
        if occupied > self.population:
            for name in reversed(self.settings["workforce_default_priority"]):
                freed = min(occupied - self.population, assigned.get(name, 0))
                assigned[name] -= freed
                occupied -= freed
                if occupied <= self.population:
                    break
        remaining = max(0, self.population - occupied)
        for name in self.settings["workforce_default_priority"]:
            if name not in assigned or name in self.assignments:
                continue
            vacant = max(0, self.buildings.get(name, 0) - assigned[name])
            fill = min(remaining, vacant)
            assigned[name] += fill
            remaining -= fill
        return assigned

    def assign_worker(self, name, change):
        if name not in self.buildings_data or not self.buildings_data[name].get("produces"):
            return False, []
        if change not in (-1, 1):
            return False, []
        current = self.workforce().get(name, 0)
        if change < 0 and current <= 0:
            return False, []
        if change > 0 and (current >= self.buildings[name] or
                           sum(self.assignments.values()) >= self.population):
            return False, []
        self.assignments[name] = current + change
        if change > 0:
            self.counters["worker_assigned"] = self.counters.get("worker_assigned", 0) + 1
        return True, self.check_achievements()

    def _citizen_needs(self, dt):
        self.food_timer += dt
        interval = self.settings["citizen_food_interval_seconds"]
        while self.food_timer >= interval:
            self.food_timer -= interval
            portions = min(self.resources["bread"],
                           self.population * self.settings["citizen_food_per_person"])
            self.resources["bread"] -= portions
            self.counters["citizens_fed"] = self.counters.get("citizens_fed", 0) + portions
        self.population_timer += dt
        interval = self.settings["growth_interval_seconds"]
        if self.population_timer >= interval:
            self.population_timer %= interval
            if (self.population < self.housing_capacity() and
                    self.resources["bread"] >= self.settings["growth_bread_cost"] and
                    self.resources["barley"] >= self.settings["growth_barley_cost"]):
                self.resources["bread"] -= self.settings["growth_bread_cost"]
                self.resources["barley"] -= self.settings["growth_barley_cost"]
                self.population += 1
                self.counters["citizen_born"] = self.counters.get("citizen_born", 0) + 1

    # --- Discoveries and Expeditions ---
    def _research_item(self, identifier):
        return next((entry for entry in self.research_data if entry["id"] == identifier), None)

    def _expedition_item(self, identifier):
        return next((entry for entry in self.expedition_data if entry["id"] == identifier), None)

    def _can_pay(self, cost):
        return all(self.resources.get(key, 0) >= amount for key, amount in cost.items())

    def _pay(self, cost):
        for key, amount in cost.items():
            self.resources[key] -= amount

    def research(self, identifier):
        item = self._research_item(identifier)
        if not item or identifier in self.researched:
            return False, []
        if any(key not in self.researched for key in item["requires"]) or not self._can_pay(item["cost"]):
            return False, []
        self._pay(item["cost"])
        self.researched.append(identifier)
        self.counters["research_completed"] = len(self.researched)
        return True, self.check_achievements()

    def start_expedition(self, identifier):
        item = self._expedition_item(identifier)
        if not item or self.active_expedition is not None:
            return False
        if any(key not in self.researched for key in item["requires"]) or not self._can_pay(item["cost"]):
            return False
        self._pay(item["cost"])
        self.active_expedition = identifier
        self.expedition_remaining = float(item["duration_seconds"])
        return True

    def _advance_expedition(self, seconds):
        if self.active_expedition is None:
            return
        self.expedition_remaining = max(0, self.expedition_remaining - seconds)
        if self.expedition_remaining > 0:
            return
        item = self._expedition_item(self.active_expedition)
        self.active_expedition = None
        self.expedition_remaining = 0.0
        for resource, amount in item["rewards"].items():
            self._add(resource, amount)
        self.counters["expedition_completed"] = self.counters.get("expedition_completed", 0) + 1
        artifact = item["artifact"]
        if artifact not in self.artifacts:
            self.artifacts.append(artifact)
            self.counters["artifact_discovered"] = len(self.artifacts)
            self.counters["discovery_" + artifact] = 1

    # --- Civilization Progression ---
    def era(self):
        return self.era_data[self.era_index]

    def era_available(self, item):
        return (item["requires_era"] == self.era()["id"] and
                all(key in self.researched for key in item["requires_research"]) and
                all(self.buildings.get(key, 0) >= count for key, count in item["requires_buildings"].items()) and
                self._can_pay(item["cost"]))

    def advance_era(self):
        if self.era_index + 1 >= len(self.era_data):
            return False, []
        item = self.era_data[self.era_index + 1]
        if not self.era_available(item):
            return False, []
        self._pay(item["cost"])
        self.era_index += 1
        self.counters["era_advanced"] = self.era_index
        return True, self.check_achievements()

    def construct_monument(self, identifier):
        item = next((item for item in self.monument_data if item["id"] == identifier), None)
        if (not item or identifier in self.monuments or
                next((index for index, era in enumerate(self.era_data) if era["id"] == item["era"]), 999) > self.era_index or
                any(key not in self.researched for key in item["requires_research"]) or
                not self._can_pay(item["cost"])):
            return False, []
        self._pay(item["cost"])
        self.monuments.append(identifier)
        self.counters["monument_" + identifier] = 1
        self.counters["monuments_built"] = len(self.monuments)
        return True, self.check_achievements()

    def claim_quest(self, identifier):
        item = next((item for item in self.quest_data if item["id"] == identifier), None)
        if (not item or identifier in self.completed_quests or
                next((index for index, era in enumerate(self.era_data) if era["id"] == item["era"]), 999) > self.era_index or
                self.counters.get(item["event"], 0) < item["target"] or
                not self._can_pay(item["cost"])):
            return False, []
        self._pay(item["cost"])
        self.completed_quests.append(identifier)
        self.renown += item["renown"]
        for resource, amount in item["rewards"].items():
            self._add(resource, amount)
        self.counters["quest_" + identifier] = 1
        self.counters["quests_completed"] = len(self.completed_quests)
        return True, self.check_achievements()

    def legacy_rank(self):
        return self.renown // self.settings["legacy_renown_per_rank"]

    def _research_multiplier(self, building):
        return (1 + sum(item["bonus_rate"] for item in self.research_data
                       if item["id"] in self.researched and item["bonus_building"] in (building, "all")) +
                sum(item["bonus_rate"] for item in self.era_data[1:self.era_index + 1]) +
                sum(item["bonus_rate"] for item in self.monument_data if item["id"] in self.monuments) +
                self.legacy_rank() * self.settings["legacy_renown_bonus_per_rank"])

    def production_rates(self):
        rates = {}
        for name, count in self.workforce().items():
            data = self.buildings_data[name]
            if data.get("produces") and count:
                resource = data["produces"]
                rates[resource] = rates.get(resource, 0) + count * data["rate"] * self._research_multiplier(name)
        return rates

    def advance(self, seconds, offline=False):
        seconds = max(0, float(seconds))
        if seconds <= 0:
            return []
        step = self.settings["simulation_step_seconds"]
        remaining = seconds
        while remaining > 0:
            dt = min(step, remaining)
            for name, count in self.workforce().items():
                if count <= 0:
                    continue
                data = self.buildings_data[name]
                product = data.get("produces")
                if not product or data["rate"] <= 0:
                    continue
                requested = count * data["rate"] * self._research_multiplier(name) * dt
                possible = max(0, self.capacity(product) - self.resources[product])
                for ingredient, amount in data.get("consumes", {}).items():
                    if amount > 0:
                        possible = min(possible, self.resources[ingredient] * data["rate"] / amount)
                produced = min(requested, possible)
                if produced <= 0:
                    continue
                for ingredient, amount in data.get("consumes", {}).items():
                    used = amount * produced / data["rate"]
                    self.resources[ingredient] = max(0, self.resources[ingredient] - used)
                    self.counters["materials_consumed"] = self.counters.get("materials_consumed", 0) + used
                self._add(product, produced)
                event = "produce_" + product
                self.counters[event] = self.counters.get(event, 0) + produced
                if offline:
                    self.counters["offline_production"] = self.counters.get("offline_production", 0) + produced
            self._citizen_needs(dt)
            self._advance_expedition(dt)
            remaining -= dt
            if remaining < 1e-9:
                break
        self.last_update = self.clock()
        return self.check_achievements()

    def tap(self):
        self._add("barley", self.settings["base_tap_yield"])
        self.counters["tap"] = self.counters.get("tap", 0) + 1
        return self.check_achievements()

    def cost(self, name):
        count = self.buildings[name]
        growth = self.settings["building_cost_growth"] ** count
        return {resource: int(math.ceil(amount * growth)) for resource, amount in self.buildings_data[name]["cost"].items()}

    def build(self, name):
        if name not in self.buildings_data:
            return False, []
        price = self.cost(name)
        if any(self.resources.get(resource, 0) < amount for resource, amount in price.items()):
            return False, []
        for resource, amount in price.items():
            self.resources[resource] -= amount
        self.buildings[name] += 1
        self.counters["build"] = self.counters.get("build", 0) + 1
        event = "build_" + name
        self.counters[event] = self.counters.get(event, 0) + 1
        return True, self.check_achievements()

    # --- Archive Progress ---
    def achievement_progress(self, achievement):
        current = max(0, self.counters.get(achievement["event"], 0))
        target = achievement["target"]
        return min(current, target), target

    def legacy_points(self):
        unlocked = set(self.unlocked)
        completed = set(self.completed_collections)
        return (sum(item.get("points", 0) for item in self.achievement_data if item["id"] in unlocked) +
                sum(item.get("points", 0) for item in self.collection_data if item["id"] in completed))

    def collection_progress(self, collection):
        unlocked = set(self.unlocked)
        return sum(key in unlocked for key in collection["required"]), len(collection["required"])

    def check_achievements(self):
        new = []
        unlocked = set(self.unlocked)
        for achievement in self.achievement_data:
            if achievement["id"] in unlocked:
                continue
            if self.counters.get(achievement["event"], 0) >= achievement["target"]:
                self.unlocked.append(achievement["id"])
                unlocked.add(achievement["id"])
                new.append(achievement["name"])
                for resource, amount in achievement.get("reward", {}).items():
                    self._add(resource, amount)
                cosmetic = achievement.get("reward_cosmetic")
                if cosmetic and cosmetic not in self.cosmetics:
                    self.cosmetics.append(cosmetic)
        for collection in self.collection_data:
            if collection["id"] in self.completed_collections:
                continue
            if all(key in unlocked for key in collection["required"]):
                self.completed_collections.append(collection["id"])
                cosmetic = collection.get("reward_cosmetic")
                if cosmetic and cosmetic not in self.cosmetics:
                    self.cosmetics.append(cosmetic)
                new.append(collection["name"] + " collection")
        return new

    def save(self):
        self.last_update = self.clock()
        data = {"version": 1, "resources": self.resources, "buildings": self.buildings,
                "counters": self.counters, "unlocked": self.unlocked, "last_update": self.last_update,
                "completed_collections": self.completed_collections, "cosmetics": self.cosmetics,
                "population": self.population, "assignments": self.assignments,
                "population_timer": self.population_timer, "food_timer": self.food_timer,
                "researched": self.researched, "artifacts": self.artifacts,
                "active_expedition": self.active_expedition,
                "expedition_remaining": self.expedition_remaining,
                "era_index": self.era_index, "monuments": self.monuments,
                "completed_quests": self.completed_quests, "renown": self.renown}
        self.save_path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, path = tempfile.mkstemp(dir=self.save_path.parent, prefix=".uruk_", suffix=".tmp")
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(data, handle, indent=2)
            os.replace(path, self.save_path)
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def load(self):
        if not self.save_path.is_file():
            return
        try:
            data = read_json(self.save_path)
            if data.get("version") != 1:
                return
            self.buildings.update({key: max(0, int(value)) for key, value in data["buildings"].items()
                                   if key in self.buildings})
            self.resources.update({key: min(self.capacity(key), max(0, float(value)))
                                   for key, value in data["resources"].items() if key in self.resources})
            self.counters = {key: max(0, float(value)) for key, value in data["counters"].items()}
            valid = {item["id"] for item in self.achievement_data}
            self.unlocked = list(dict.fromkeys(value for value in data["unlocked"] if value in valid))
            collection_ids = {item["id"] for item in self.collection_data}
            self.completed_collections = list(dict.fromkeys(
                value for value in data.get("completed_collections", []) if value in collection_ids))
            cosmetic_ids = ({item.get("reward_cosmetic") for item in self.achievement_data} |
                            {item.get("reward_cosmetic") for item in self.collection_data})
            self.cosmetics = list(dict.fromkeys(
                value for value in data.get("cosmetics", []) if value in cosmetic_ids and value))
            # Reconcile rewards for pre-Phase-6 achievement saves without duplicating unlocks.
            for item in self.achievement_data:
                reward = item.get("reward_cosmetic")
                if item["id"] in self.unlocked and reward and reward not in self.cosmetics:
                    self.cosmetics.append(reward)
            for collection in self.collection_data:
                if collection["id"] in self.completed_collections:
                    reward = collection.get("reward_cosmetic")
                    if reward and reward not in self.cosmetics:
                        self.cosmetics.append(reward)
            self.era_index = max(0, min(len(self.era_data) - 1, int(data.get("era_index", 0))))
            monument_ids = {item["id"] for item in self.monument_data}
            self.monuments = list(dict.fromkeys(item for item in data.get("monuments", []) if item in monument_ids))
            quest_ids = {item["id"] for item in self.quest_data}
            self.completed_quests = list(dict.fromkeys(item for item in data.get("completed_quests", []) if item in quest_ids))
            self.renown = sum(item["renown"] for item in self.quest_data if item["id"] in self.completed_quests)
            valid_research = {item["id"] for item in self.research_data}
            self.researched = list(dict.fromkeys(item for item in data.get("researched", []) if item in valid_research))
            valid_artifacts = {item["id"] for item in self.artifact_data}
            self.artifacts = list(dict.fromkeys(item for item in data.get("artifacts", []) if item in valid_artifacts))
            active = data.get("active_expedition")
            self.active_expedition = active if self._expedition_item(active) else None
            self.expedition_remaining = (min(float(data.get("expedition_remaining", 0)),
                                             self._expedition_item(active)["duration_seconds"])
                                         if self.active_expedition else 0.0)
            if self.active_expedition:
                self.expedition_remaining = max(0.0, self.expedition_remaining)
            self.population = max(0, min(self.housing_capacity(), int(data.get("population", self.population))))
            saved_assignments = data.get("assignments", {})
            self.assignments = {name: max(0, min(self.buildings[name], int(count)))
                                for name, count in saved_assignments.items()
                                if name in self.buildings and self.buildings_data[name].get("produces")}
            self.population_timer = max(0, float(data.get("population_timer", 0))) % self.settings["growth_interval_seconds"]
            self.food_timer = max(0, float(data.get("food_timer", 0))) % self.settings["citizen_food_interval_seconds"]
            self.last_update = min(float(data["last_update"]), self.clock())
        except (OSError, ValueError, TypeError, KeyError, OverflowError):
            return
