"""Provider registry."""

from .ntfy import NtfyNotifier
from .pushover import PushoverNotifier

PROVIDERS = {
    NtfyNotifier.name: NtfyNotifier,
    PushoverNotifier.name: PushoverNotifier,
}


def build_notifiers(config):
    """Build fresh clients from the effective config so settings changes
    apply immediately."""
    return {name: cls(config.get(name, {})) for name, cls in PROVIDERS.items()}
