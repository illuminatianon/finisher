import subprocess
import sys
import os

os.environ["PYTHONPATH"] = "src"

# this assumes you already bumped __version__ in __init__.py
# optional: extract version and pass it into exe metadata

# make sure dist/ is clean
subprocess.run(["rm", "-rf", "build", "dist", "__pycache__"], check=True)

# run pyinstaller
subprocess.run([
    "pyinstaller",
    "--onefile",
    "--noconsole",
    "--icon=icon.ico",
    "--name=finisher",
    "launcher.py"
], check=True)

print("build complete: dist/finisher")