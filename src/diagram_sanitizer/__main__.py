"""Allow running the package with `python -m diagram_sanitizer`."""

from .cli import main

if __name__ == "__main__":
    import sys
    sys.exit(main())
