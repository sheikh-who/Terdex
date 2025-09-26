# Termux Quick Reference

Terdex ships with a built-in `terdex termux` command that summarises the
everyday shortcuts and configuration tweaks needed to stay productive on a
touch-first Android device. This guide mirrors that reference in a markdown
format so you can browse it offline or extend it for local documentation.

## Keyboard Shortcuts

- Volume down doubles as **Ctrl**, allowing classic shortcuts:
  - `Ctrl+A` / `Ctrl+E` move to the start or end of the line.
  - `Ctrl+K` / `Ctrl+U` delete to the end or start of the line.
  - `Ctrl+L` clears the terminal.
  - `Ctrl+C` stops the current process, `Ctrl+Z` suspends it, and `Ctrl+D` sends EOF.
- Volume up acts as an alternate modifier:
  - `Volume Up+E` emits **Esc** and `Volume Up+T` emits **Tab**.
  - `Volume Up+1` through `Volume Up+0` provide function keys **F1–F10**.
  - Arrow keys are available via `Volume Up+A/D/W/S`.

## Extra Keys Configuration

Customise the additional keys row by editing `~/.termux/termux.properties`:

- `extra-keys-style = default` switches between presets such as `default`,
  `arrows-only`, and `all`.
- `extra-keys = [['ESC','/','-','HOME','UP','END','PGUP'], ['TAB','CTRL','ALT','LEFT','DOWN','RIGHT','PGDN']]`
  defines multi-row layouts.
- Pop-up macros allow swipe gestures, e.g.
  `{key: ESC, popup: {macro: "CTRL d", display: "exit"}}`.
- Run `termux-reload-settings` after editing to apply changes immediately.

## Package Management Basics

Termux wraps `apt` with the `pkg` helper; stick to this toolchain to avoid
permission issues:

- `pkg install <package>` installs new software (and triggers an `apt update` when needed).
- `pkg upgrade` refreshes every installed package; run it regularly.
- `pkg uninstall <package>` removes software while keeping configuration files.
- Clean caches with `pkg autoclean` (outdated archives) or `pkg clean` (all caches).
- Explore repositories through `pkg list-all`, search with `pkg search <query>`,
  and enable optional collections via packages like `science-repo` or `x11-repo`.

## Termux API Essentials

Install the Termux:API Android add-on and the `termux-api` package to script device
hardware safely. Popular commands include:

- `termux-battery-status` for battery metrics.
- `termux-clipboard-get` / `termux-clipboard-set` to bridge the clipboard.
- `termux-notification` for rich Android notifications.
- `termux-toast` to display quick toasts.
- `termux-camera-photo` to capture images directly to a file.
- `termux-location` for coarse or fine location data.
- `termux-media-player` to play audio or video.

## Appearance and Session Tweaks

Additional options inside `~/.termux/termux.properties` help tailor the UI:

- `use-black-ui=true` forces dark drawers and dialogs.
- `fullscreen=true` maximises the terminal (combine with
  `use-fullscreen-workaround=true` on devices that hide the extra keys row).
- `shortcut.create-session=ctrl + t` opens a new terminal session via `Volume Down+T`.
- `shortcut.next-session` / `shortcut.previous-session` bind navigation between panes.
- `enforce-char-based-input=true` works around keyboards that inject words instead of characters.
- `terminal-margin-horizontal=6` adjusts horizontal padding to avoid clipped edges.

## Desktop Environments

Run full graphical desktops through a local VNC server. Keep `~/.vnc/xstartup`
minimal—just the command that launches the desktop session—and manage the rest
via each environment's autostart hooks.

- **XFCE:** `pkg install xfce4` then populate `~/.vnc/xstartup` with
  `#!/data/data/com.termux/files/usr/bin/sh` and `xfce4-session &`.
  Add tools like `netsurf` or `xfce4-terminal` for a friendlier desktop.
- **LXQt:** Install with `pkg install lxqt` and configure
  `startlxqt &` in the xstartup file. Pair with `otter-browser` and `qterminal`.
- **MATE:** Install `pkg install mate-* marco` and start the session with
  `mate-session &`. Bring in `netsurf` or `mate-terminal` as needed.
- **Openbox:** Launch using `openbox-session &` in `~/.vnc/xstartup` and manage
  panels or wallpaper via `${PREFIX}/etc/xdg/openbox/autostart`
  (e.g. launching `pypanel` or setting the background).

## Termux X11 Packages

The community-maintained X11 repository unlocks additional desktop packages.

- Enable the repository with `pkg install x11-repo` (Android 7+).
- Use `pkg install tigervnc` and connect with your favourite VNC viewer to see
  graphical output.
- Keep `~/.vnc/xstartup` trimmed to just the session launch command to avoid
  conflicting daemons.
- Build or customise packages by cloning
  `https://github.com/termux/x11-packages`, running `./start-builder.sh`, and
  executing `./build-package.sh -a <arch> <package>`.
- Note that hardware acceleration is typically unavailable within these VNC
  environments, so expect software rendering.

Consult the official [Termux Wiki](https://wiki.termux.com/) for deeper dives.
