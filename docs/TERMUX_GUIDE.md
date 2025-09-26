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

Consult the official [Termux Wiki](https://wiki.termux.com/) for deeper dives.
