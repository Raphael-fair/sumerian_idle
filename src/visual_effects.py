# --- Imports ---
import math
import random

# --- Particle Mathematics ---
def particle_position(origin, velocity, elapsed, gravity):
    return (origin[0] + velocity[0] * elapsed,
            origin[1] + velocity[1] * elapsed - gravity * elapsed * elapsed / 2)


def night_strength(elapsed, cycle_seconds, maximum):
    return maximum * (1 - math.cos(2 * math.pi * (elapsed % cycle_seconds) / cycle_seconds)) / 2


def make_burst(origin, effect, seed=None):
    rng = random.Random(seed)
    particles = []
    for _ in range(min(effect["spark_count"], effect["max_particles"])):
        angle = rng.uniform(0, 2 * math.pi)
        speed = effect["spark_speed_dp"] * rng.uniform(.45, 1)
        particles.append((origin, (math.cos(angle) * speed, math.sin(angle) * speed),
                          rng.choice(effect["spark_colors"])))
    return particles
