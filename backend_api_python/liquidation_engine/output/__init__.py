"""
output/__init__.py

TerminalDisplay is imported lazily so backend code can import
``output.state_snapshot`` (JSON-safe, no CLI deps) without pulling in
colorama. CLI usage (`from output import TerminalDisplay`) still works.
"""

__all__ = ["TerminalDisplay"]


def __getattr__(name):
    if name == "TerminalDisplay":
        from output.terminal_display import TerminalDisplay
        return TerminalDisplay
    raise AttributeError(f"module 'output' has no attribute {name!r}")
