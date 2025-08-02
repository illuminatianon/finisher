import sys
import re
from pathlib import Path

version = sys.argv[1]
init_path = Path("src/finisher/__init__.py")

text = init_path.read_text()
text = re.sub(r'__version__\s*=\s*["\'].*?["\']', f'__version__ = "{version}"', text)
init_path.write_text(text)

print(f"updated __version__ to {version}")
