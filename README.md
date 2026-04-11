# arch-sysup

**A GUI System Update Tool for Arch Linux**

arch-sysup is a lightweight graphical front-end for keeping your Arch Linux system fully up to date. It handles official repository packages via `pacman`, automatically detects whether you have `yay` or `paru` installed, and uses whichever AUR helper is available to update your AUR packages as well — all from a clean, simple Tkinter interface.

A background notifier service can also alert you when updates are available, so you always know when your system needs attention.

---

## Features

- Simple Tkinter graphical interface — no terminal required
- Updates official Arch packages via `pacman`
- Automatically detects and uses `yay` or `paru` for AUR package updates
- Manual "Sync DBs" button to refresh package databases (`pacman -Sy`)
- Displays live update output in a scrollable log window
- Background notifier service (`arch-sysup-notifier`) checks for available updates and sends a desktop notification
- Systemd user service for running the notifier automatically on login
- Desktop file included so it appears in your application launcher

---

## Dependencies

The following packages are required and will be pulled in automatically when installing via the PKGBUILD:

| Package | Purpose |
|---|---|
| `python` | Runtime for the application |
| `tk` | Tkinter toolkit for the GUI |
| `pacman` | Core package manager (should already be present) |
| `libnotify` | Desktop notifications for the notifier service |
| `pacman-contrib` | Provides the `checkupdates` command used to safely check for available updates |

**Optional (but recommended):**

| Package | Purpose |
|---|---|
| 'reflector' | if wanting to use the 'mirror' tab to configure and update |
| `yay` | AUR helper — used if present |
| `paru` | AUR helper — used if `yay` is not found |

> At least one AUR helper (`yay` or `paru`) should be installed if you want AUR packages updated. Without one, only official repository packages will be updated.

---

## Installation

### Via PKGBUILD (Recommended)

1. Create a new directory to keep things tidy:
   ```bash
   mkdir arch-sysup && cd arch-sysup
   ```

2. Download the PKGBUILD:
   ```bash
   curl -O https://raw.githubusercontent.com/broncbash/arch-sysup/main/PKGBUILD
   ```

3. Build and install the package:
   ```bash
   makepkg -si
   ```
   Enter your sudo password when prompted. `makepkg` will automatically pull in all required dependencies.

Once installed, **arch-sysup** will appear in your application launcher. You can also run it from a terminal with:
```bash
arch-sysup
```

---

## Update Notifier (Optional)

arch-sysup includes a background notifier that periodically checks for available updates and sends a desktop notification when updates are found.

To enable it as a systemd user service so it starts automatically on login:

```bash
systemctl --user enable --now arch-sysup.service
```

To check its status:
```bash
systemctl --user status arch-sysup.service
```

To disable it:
```bash
systemctl --user disable --now arch-sysup.service
```

---

## Usage

Launch arch-sysup from your application menu or run `arch-sysup` in a terminal. Click the **Update** button to begin the update process. Live output from `pacman` and your AUR helper will stream into the log window so you can follow along. When the update is complete, a summary will be shown.

If updates are not showing up as expected, use the **Sync DBs** button to refresh your local package databases.

---

## Notes

- arch-sysup will ask for your sudo password via a graphical prompt when elevated privileges are needed.
- AUR helper detection is automatic — `yay` takes priority over `paru` if both are installed.
- This project was built with assistance from Claude and Gemini as a fun personal project. Contributions and feedback are welcome!

---

## License

This project is provided as-is for personal use. Feel free to fork and modify it to suit your needs.
