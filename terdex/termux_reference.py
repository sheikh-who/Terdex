"""Curated Termux reference data for CLI and docs output."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List


@dataclass(frozen=True)
class TermuxEntry:
    """Single fact or tip describing a Termux behaviour."""

    name: str
    description: str

    def to_dict(self) -> Dict[str, str]:
        return {"name": self.name, "description": self.description}


@dataclass(frozen=True)
class TermuxSection:
    """Collection of related Termux information items."""

    key: str
    title: str
    summary: str
    entries: List[TermuxEntry]

    def to_dict(self) -> Dict[str, object]:
        return {
            "key": self.key,
            "title": self.title,
            "summary": self.summary,
            "entries": [entry.to_dict() for entry in self.entries],
        }


def _entries(pairs: Iterable[tuple[str, str]]) -> List[TermuxEntry]:
    return [TermuxEntry(name=name, description=description) for name, description in pairs]


TERMUX_REFERENCE: List[TermuxSection] = [
    TermuxSection(
        key="keyboard",
        title="Keyboard Shortcuts",
        summary=(
            "Volume down acts as Ctrl and Volume up acts as modifier keys so you can "
            "access traditional terminal shortcuts from touch devices."
        ),
        entries=_entries(
            [
                ("Ctrl+A", "Move to line start."),
                ("Ctrl+E", "Move to line end."),
                ("Ctrl+K", "Delete from cursor to end of line."),
                ("Ctrl+U", "Delete from cursor to start of line."),
                ("Ctrl+L", "Clear the current terminal view."),
                ("Ctrl+C", "Send SIGINT to stop the running process."),
                ("Ctrl+Z", "Suspend the active process."),
                ("Ctrl+D", "Log out or send EOF when input is empty."),
                ("Volume Up+E", "Send Escape when hardware key is unavailable."),
                ("Volume Up+T", "Send Tab for autocompletion."),
                (
                    "Volume Up+1…0",
                    "Access function keys F1–F10 for ncurses applications.",
                ),
                ("Volume Up+A/D/W/S", "Arrow key navigation left/right/up/down."),
            ]
        ),
    ),
    TermuxSection(
        key="extra-keys",
        title="Extra Keys Configuration",
        summary=(
            "Customise the extra keys row via ~/.termux/termux.properties and reload with "
            "`termux-reload-settings`."
        ),
        entries=_entries(
            [
                (
                    "extra-keys",
                    "Define custom rows, e.g. [['ESC','/','-','HOME','UP','END','PGUP'], …].",
                ),
                (
                    "extra-keys-style",
                    "Pick presets such as 'default', 'arrows-only', or 'all'.",
                ),
                (
                    "Popup macros",
                    "Use {key: ESC, popup: {macro: 'CTRL d', display: 'exit'}} to define swipe actions.",
                ),
                (
                    "termux-reload-settings",
                    "Apply configuration changes without restarting the app.",
                ),
            ]
        ),
    ),
    TermuxSection(
        key="package-management",
        title="Package Management",
        summary=(
            "Use `pkg` as the wrapper around apt to install, upgrade, and remove software "
            "within Termux without sudo."
        ),
        entries=_entries(
            [
                ("pkg install <pkg>", "Install a package after refreshing indexes."),
                ("pkg upgrade", "Update all installed packages; run regularly."),
                ("pkg uninstall <pkg>", "Remove a package while leaving config files."),
                ("pkg autoclean", "Delete outdated .deb files from cache."),
                ("pkg clean", "Clear all cached packages to free space."),
                (
                    "pkg list-all",
                    "List everything available across the enabled repositories.",
                ),
                (
                    "pkg search <query>",
                    "Search repositories for packages matching the query.",
                ),
                (
                    "Repository add-ons",
                    "Install *-repo packages (e.g. science-repo) for extra package sets.",
                ),
            ]
        ),
    ),
    TermuxSection(
        key="termux-api",
        title="Termux API",
        summary=(
            "Install the termux-api package plus the Android add-on to access device hardware "
            "from scripts (battery, sensors, clipboard, notifications, etc.)."
        ),
        entries=_entries(
            [
                ("termux-battery-status", "Print current battery state."),
                ("termux-clipboard-get/set", "Read or write clipboard text."),
                ("termux-notification", "Show custom Android notifications."),
                ("termux-toast", "Display a transient toast message."),
                ("termux-camera-photo", "Capture a photo to a specified path."),
                ("termux-location", "Fetch current location coordinates."),
                ("termux-media-player", "Play audio or video files."),
            ]
        ),
    ),
    TermuxSection(
        key="appearance",
        title="Appearance and Sessions",
        summary=(
            "Tweak UI behaviour through ~/.termux/termux.properties, including dark mode, fullscreen, and session shortcuts."
        ),
        entries=_entries(
            [
                ("use-black-ui", "Force dark UI elements in drawers and dialogs."),
                ("fullscreen", "Enable fullscreen terminal rendering."),
                (
                    "shortcut.create-session",
                    "Map Ctrl+T to open a new terminal session.",
                ),
                (
                    "shortcut.next-session/previous-session",
                    "Navigate between sessions with custom key combos.",
                ),
                (
                    "enforce-char-based-input",
                    "Work around keyboards that enforce word-based input.",
                ),
                (
                    "terminal-margin-horizontal",
                    "Adjust left/right padding (0–100 dp).",
                ),
            ]
        ),
    ),
    TermuxSection(
        key="desktop",
        title="Desktop Environments",
        summary=(
            "Install XFCE, LXQt, MATE, or Openbox within Termux and launch them through a VNC session for a full graphical desktop."
        ),
        entries=_entries(
            [
                (
                    "XFCE",
                    "pkg install xfce4, then set ~/.vnc/xstartup to run 'xfce4-session &' before starting the VNC server.",
                ),
                (
                    "LXQt",
                    "pkg install lxqt and use a minimal ~/.vnc/xstartup containing 'startlxqt &' to launch the session.",
                ),
                (
                    "MATE",
                    "Install the mate-* meta packages plus marco, then start VNC sessions with 'mate-session &' in ~/.vnc/xstartup.",
                ),
                (
                    "Recommended apps",
                    "Add lightweight browsers (netsurf or otter-browser) and terminals (xfce4-terminal, qterminal, mate-terminal) for each desktop.",
                ),
                (
                    "Openbox",
                    "Keep ~/.vnc/xstartup limited to the openbox-session launch and customise ${PREFIX}/etc/xdg/openbox/autostart for panels like PyPanel.",
                ),
            ]
        ),
    ),
    TermuxSection(
        key="x11",
        title="Termux X11 Packages",
        summary=(
            "Enable the x11-repo, use a VNC server for display output, and explore desktop packages or build scripts maintained by the community."
        ),
        entries=_entries(
            [
                ("Enable repository", "Run pkg install x11-repo to add the official X11 packages."),
                (
                    "VNC setup",
                    "Install tigervnc, start the server locally, and connect with a VNC viewer to render graphical apps.",
                ),
                (
                    "Xstartup basics",
                    "Keep ~/.vnc/xstartup minimal—usually just the desktop session command—to avoid conflicts.",
                ),
                (
                    "Build locally",
                    "Clone https://github.com/termux/x11-packages and use ./start-builder.sh then ./build-package.sh -a <arch> <package> to compile extras.",
                ),
                (
                    "Hardware notes",
                    "Hardware acceleration is generally unavailable by default when running X11 via VNC inside Termux.",
                ),
            ]
        ),
    ),
]


def lookup_section(key: str) -> TermuxSection | None:
    key_lower = key.lower()
    for section in TERMUX_REFERENCE:
        if section.key == key_lower:
            return section
    return None

