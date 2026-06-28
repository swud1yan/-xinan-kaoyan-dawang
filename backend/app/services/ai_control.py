"""Global AI on/off switch."""
_ai_enabled = True


def ai_enabled() -> bool:
    return _ai_enabled


def disable_ai():
    global _ai_enabled
    _ai_enabled = False


def enable_ai():
    global _ai_enabled
    _ai_enabled = True
