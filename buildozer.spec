[app]
title = Sumerian Idle
package.name = sumerianidle
package.domain = org.uruk
source.dir = .
source.include_exts = py,json,png,svg,wav
source.exclude_dirs = tests,__pycache__,.venv,.git
source.exclude_patterns = *.pyc,*.pyo,*.zip
version = 1.0.0
requirements = python3,kivy
orientation = portrait
fullscreen = 0
android.api = 35
android.minapi = 23
android.archs = arm64-v8a,armeabi-v7a
android.permissions = 
android.numeric_version = 10

[buildozer]
log_level = 2
warn_on_root = 1
