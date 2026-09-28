# Arm Create firmware for Tufty 2350

This folder is a backup of the custom firmware from the Arm Create developer conference. It only runs on the **Tufty 2350**, the color-screen badge in Pimoroni's Badgeware line.

Do not flash these files onto Badger, Blinky, or the older Tufty 2040. Those are different boards. This image was built for `pimoroni_tufty2350`, and the program, the screen, and the files on the badge are laid out for that board.

- Product site: [badgewa.re](https://badgewa.re/)
- Badgeware API: [badgewa.re/docs](https://badgewa.re/docs)
- Stock firmware and updates: [github.com/pimoroni/tufty2350](https://github.com/pimoroni/tufty2350)
- Buy the board: [shop.pimoroni.com/products/tufty-2350](https://shop.pimoroni.com/products/tufty-2350)

Tufty is one of three Badgeware badges. The other two use different screens and different firmware:

- [Badger](https://github.com/pimoroni/badger2350) — 2.7" 264×176 e-paper
- [Blinky](https://github.com/pimoroni/blinky2350) — white LED matrix

## Tufty 2350

These are the board specs from Pimoroni. The chip reading from this badge matches the Tufty 2350: an RP2350 in a QFN80 package, which is the RP2350B, and 16 MB of flash.

| | |
| --- | --- |
| Display | 2.8" full-color IPS LCD, 320×240, adjustable backlight |
| Light sensor | Phototransistor (this is specific to Tufty) |
| Microcontroller | RP2350B, dual Arm Cortex-M33, 520 KB on-chip SRAM. Pimoroni lists it at 250 MHz |
| Storage | 16 MB QSPI flash (XiP) |
| Extra RAM | 8 MB PSRAM |
| Wireless | Raspberry Pi RM2 (CYW43439): 2.4 GHz 802.11 b/g/n Wi-Fi, Bluetooth 5.2 |
| Battery | 3.7 V 1000 mAh LiPo, charged over USB-C. Charger is an MCP73831 at 455 mA. Protector is an XB6096I2S |
| Clock | PCF85063A real-time clock, used to wake from sleep |
| Case | Polycarbonate, orange back (Badgeware calls this colorway Mandarin). 84 mm wide, 76 mm tall, 20 mm deep, including the case |
| Case lights | 4-zone mono LEDs on the back |
| Front buttons | Five: Up, Down, A/Left, B/Action, C/Right |
| Edge buttons | HOME/BOOT, and RESET (also sleep and disk mode) |
| Ports | USB-C for charge, program, and disk mode. Qw/ST (Qwiic / STEMMA QT) I2C port. SWD debug port |
| Software | MicroPython, with the Badgeware API |
| Lanyard | Included, labeled "Sciuridae Consultant" |

Stock instructions, from the [Tufty 2350 repo](https://github.com/pimoroni/tufty2350): turn the badge over so the back faces you. BOOT is the button toward the far left. RESET is just to the right of BOOT, on the left-hand edge.

## This image is the with-filesystem kind

Pimoroni ships two files for each stock release. The latest stock release right now is [v3.1.1](https://github.com/pimoroni/tufty2350/releases/tag/v3.1.1).

| Stock file | What it does on a Tufty 2350 |
| --- | --- |
| `tufty-vX.X.X-micropython.uf2` | Replaces the firmware only. Apps and pictures already on the badge stay put. |
| `tufty-vX.X.X-micropython-with-filesystem.uf2` | Replaces the firmware and installs the factory apps and files. |

This backup is the second kind, but it is the Arm Create build, not the stock v3.1.1 file. The version string is `bw-1.28.0-3`, built August 25, 2026, with Pico SDK 2.3.0.

Flash `tufty-bw-1.28.0-3-micropython-with-filesystem.uf2` when you want this conference badge back, firmware and files together. Flashing the stock `with-filesystem` UF2 from the Pimoroni repo will wipe these apps and pictures and put the factory set back.

## What was read off this badge

Taken with picotool 2.3.1 while the badge was in BOOTSEL. The full 16 MB read was checked against the chip. picotool reported `OK`.

- Board id: `pimoroni_tufty2350`
- Chip: RP2350, revision A4, package QFN80
- Firmware: MicroPython `bw-1.28.0-3`, ARM Secure image, USB REPL
- Firmware addresses: `0x10000000`–`0x10152520`
- A 1 MB read-only ROMFS sits at `0x10200000`–`0x10300000`
- Badge files sit in a FAT filesystem labeled `TUFTY`, at `0x10300000`–`0x11000000` (13 MB). Sector size is 4096 bytes
- There is no RP2350 partition table. The whole chip is one unpartitioned flash image

The FAT volume holds the apps and pictures. That is why the with-filesystem image is the one that brings the folders back. A firmware-only UF2 stops at the program and leaves that region alone.

## Files in this folder

| File | What it is |
| --- | --- |
| `tufty-bw-1.28.0-3-micropython-with-filesystem.uf2` | Drag this onto the RP2350 drive. It is the whole 16 MB flash chip (family ID `absolute`), so the firmware, apps, and pictures all go back together. |
| `tufty-bw-1.28.0-3-micropython-with-filesystem.bin` | The same 16 MB image as a raw `.bin`, for `picotool load`. It loads at `0x10000000`. |
| `TUFTY\` | Those badge folders extracted so you can look at the apps and pictures on a computer. |
| `SHA256.txt` | Checksums for the two image files. |
| `picotool-info.txt` | The picotool report from the backup. |

`INDEX.HTM` and `INFO_UF2.TXT` are the two files the RP2350 boot drive shows. They are not the firmware.

Pictures in `TUFTY\`:

- Shared art in `ASSETS\`: `TUFTY.PNG`, `background.png`, `CARDS.PNG`, `ICONS.PNG`, `SKULL.PNG`, `SQUIRREL.GIF`, `ARMMARK.SVG`, and `squirrel-sprites\`
- Gallery pages in `APPS\GALLERY\IMAGES\EN\` and `APPS\GALLERY\IMAGES\CN\`
- App icons and sprites under `APPS\BADGE`, `APPS\cricket_hop`, `APPS\SNAKE`, and `APPS\TUFTY`

`SECRETS.PY` and `PROFILE.PY` are the Wi-Fi and name-badge settings. In this backup they are still blank: no SSID, password, name, company, job title, or social handle. `LANGUAGE` is `cn`, which only selects the Chinese gallery artwork. There is no `profile.png`.

## Install picotool on Windows

You need picotool to read the chip or to flash the `.bin`. Dragging the `.uf2` onto the RP2350 drive does not need it.

1. Download `picotool-2.3.1-x64-win.zip` from the Raspberry Pi pico-sdk-tools release [v2.3.1-0](https://github.com/raspberrypi/pico-sdk-tools/releases/tag/v2.3.1-0).
2. Unzip it and keep the whole `picotool` folder. `picotool.exe` has to stay next to the other files in that folder.
3. Put that folder on your user Path:

```powershell
$picodir = "$env:USERPROFILE\.local\pico\picotool-2.3.1\picotool"
New-Item -ItemType Directory -Force -Path (Split-Path $picodir) | Out-Null
# Unzip picotool-2.3.1-x64-win.zip so picotool.exe is in $picodir
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -notlike "*$picodir*") {
  [Environment]::SetEnvironmentVariable("Path", "$picodir;$userPath", "User")
}
[Environment]::SetEnvironmentVariable("picotool_DIR", $picodir, "User")
```

4. Close PowerShell, open a new window, and run:

```powershell
picotool version
```

You want `picotool v2.3.1`. The commands in this file match that version. On the machine where this backup was made, picotool is already at `%USERPROFILE%\.local\pico\picotool-2.3.1\picotool\picotool.exe`.

## Put Tufty in BOOTSEL

The boot drive is named **RP2350** on this board. Pimoroni's stock steps are:

1. Plug Tufty into the computer with a USB-C cable that carries data. A charge-only cable will power the badge and will not show a drive.
2. Turn the badge over so the back faces you.
3. Press and hold **BOOT** (HOME/BOOT), the button toward the far left.
4. Briefly tap **RESET**, just to the right of BOOT.
5. Let go of BOOT.

File Explorer should show a removable drive named **RP2350**. On that drive you will only see `INDEX.HTM` and `INFO_UF2.TXT`. The apps and pictures are not loose files there. They are in the flash image.

## Flash this image

Tufty has to be in BOOTSEL, with the RP2350 drive on screen. These files are for a Tufty 2350 only.

### Drag the UF2

Copy `tufty-bw-1.28.0-3-micropython-with-filesystem.uf2` onto the root of the RP2350 drive. Do not drop it into a subfolder.

The file is about 32 MB because a UF2 stores 256 bytes of flash in each 512-byte block. It covers `0x10000000` through `0x10FFFF00`, which is the entire 16 MB chip: firmware, the ROMFS, and the TUFTY filesystem. When the copy finishes, the RP2350 drive goes away and the badge reboots. Windows often reports that the drive disappeared. That is the flash completing, not a failed copy.

### Or flash the bin with picotool

From this folder:

```powershell
picotool info
picotool load -v -x ".\tufty-bw-1.28.0-3-micropython-with-filesystem.bin"
```

`picotool info` should see an RP2350. `-v` reads the flash back and checks the write. `-x` reboots into the program when the write is done. Do not pass an offset. A `.bin` from this backup already starts at `0x10000000`.

A full write plus the check takes a couple of minutes.

After this flash you do not also copy `TUFTY\` by hand. The folders and pictures are already in the image.

## Open the folders and pictures

Stock Tufty firmware calls this disk mode, and the [Tufty repo](https://github.com/pimoroni/tufty2350) says the drive shows up as **Tufty2350**. This Arm Create image's filesystem volume is labeled **TUFTY**, so look for that name too.

1. Let the badge boot. Do not hold BOOT.
2. Plug in USB if you unplugged it.
3. Turn the badge over. Double-tap **RESET** (the button to the right of BOOT).
4. A drive appears. On it you should see `MAIN.PY`, `APPS`, `ASSETS`, `BRANDING.PY`, `PROFILE.PY`, and `SECRETS.PY`. Gallery pictures are in `APPS\GALLERY\IMAGES`.
5. Eject the drive from Windows when you are done copying. The badge reboots into the menu. You can also tap RESET once to leave disk mode.

Copy the backup folders onto the badge by hand only if you flashed a firmware-only UF2 and the files are missing:

1. Double-tap RESET so the drive appears.
2. Open `TUFTY` from this backup.
3. Copy the contents onto the root of that drive: `MAIN.PY`, `APPS`, `ASSETS`, and the other files next to them. Do not copy the `TUFTY` folder itself onto the drive. That nests a second `TUFTY` folder and the badge will not see the apps.

Wi-Fi for this image is the same idea as stock Badgeware: edit `secrets.py` on that drive, then eject it. The API those apps call is documented at [badgewa.re/docs](https://badgewa.re/docs).

## If picotool cannot see Tufty

The RP2350 drive can show up while picotool still says no BOOTSEL device was found. Install WinUSB for the boot interface only:

1. Download [Zadig](https://zadig.akeo.ie/) and run it as administrator.
2. Open Options, then List All Devices.
3. Choose **RP2 Boot (Interface 1)**.
4. Set the driver on the right to **WinUSB**, not libusb-win32.
5. Install it.

Do not replace the driver on the mass-storage interface. That removes the RP2350 drive. Unplug the badge, enter BOOTSEL again, and run `picotool info`.

If no drive appears at all, try another USB port and another data cable, and hold BOOT while you tap RESET.

## Read a Tufty again

Do this in BOOTSEL, before you flash something else over the chip. `save -a` is the whole flash chip. `save` without `-a` keeps the program only, and you would lose the apps and pictures from the backup.

```powershell
picotool info -a
picotool save -a -v .\tufty-bw-1.28.0-3-micropython-with-filesystem.bin
picotool uf2 convert --family absolute --platform rp2350 .\tufty-bw-1.28.0-3-micropython-with-filesystem.bin .\tufty-bw-1.28.0-3-micropython-with-filesystem.uf2
```

## Checksums

```
tufty-bw-1.28.0-3-micropython-with-filesystem.bin
0EA16153920D58F0E16D19E931EDAF37210069947C5DF1A3953E36365717B055

tufty-bw-1.28.0-3-micropython-with-filesystem.uf2
2CC8E37C3E1DE376748D263D3E002F04C19079D7D7C6CDFFF6ECB7789BAB0C80
```

```powershell
Get-FileHash -Algorithm SHA256 .\tufty-bw-1.28.0-3-micropython-with-filesystem.uf2
```
