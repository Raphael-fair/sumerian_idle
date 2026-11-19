# --- Imports ---
import json
from pathlib import Path


# --- Android Build Specification ---
def make_spec(config):
    android = config["android"]
    packaging = config["packaging"]
    pairs = {
        "title": android["title"],
        "package.name": android["package_name"],
        "package.domain": android["package_domain"],
        "source.dir": ".",
        "source.include_exts": ",".join(packaging["source_extensions"]),
        "source.exclude_dirs": ",".join(packaging["exclude_directories"]),
        "source.exclude_patterns": ",".join(packaging["exclude_patterns"]),
        "version": android["version"],
        "requirements": ",".join(android["requirements"]),
        "orientation": android["orientation"],
        "fullscreen": "1" if android["fullscreen"] else "0",
        "android.api": str(android["target_api"]),
        "android.accept_sdk_license": str(android["accept_sdk_license"]).lower(),
        "android.minapi": str(android["min_api"]),
        "android.archs": ",".join(android["architectures"]),
        "android.permissions": ",".join(android["permissions"]),
        "android.numeric_version": str(android["version_code"]),
    }
    if not all(android[key] for key in ("title", "package_name", "package_domain", "version")):
        raise ValueError("Android package metadata is incomplete")
    if android["min_api"] > android["target_api"]:
        raise ValueError("Minimum API cannot exceed target API")
    if "py" not in packaging["source_extensions"] or "json" not in packaging["source_extensions"]:
        raise ValueError("Python and JSON files must be included")
    return "[app]\n" + "".join(f"{key} = {value}\n" for key, value in pairs.items()) + "\n[buildozer]\nlog_level = 2\nwarn_on_root = 1\n"


def write_spec(root):
    root = Path(root)
    config = json.loads((root / "config" / "build.json").read_text(encoding="utf-8"))
    destination = root / config["packaging"]["output_spec"]
    destination.write_text(make_spec(config), encoding="utf-8")
    return destination
