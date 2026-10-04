# OpenBeken for LSC 3224261 (LN882H + WS2805, 9 pixels)

[OpenBeken](https://github.com/openshwprojects/OpenBK7231T_App) firmware with a **WS2805**
LED strip driver (RGB+CCT, 5 channels per pixel) for the LSC 3224261 controller based on the
**LN882H** chip.
Default configuration: **9 pixels**, channel order BRGWC, IR receiver on P12, button on P21.
The microphone on P0 is not used.

## Repository contents

| File | Description |
|---|---|
| `autoexec.bat` | Startup script for LittleFS: pins, WS2805 with 9 pixels, TinyIR_NEC |
| `firmware/OpenLN882H_WS2805.ota.bin` | OTA image for an already running OpenBeken |
| `firmware/OpenLN882H_WS2805.factory.bin` | Full image for the LN882H UART flasher at 0x00000000 |
| `patch/OpenBeken_LN882H_WS2805.patch` | Changes against OpenBK7231T_App `458d0b7f` |
| `tools/build_ln882h_ws2805.py` | Build script |
| `tools/test_ws2805.py` | Tests of the C functions under ARM emulation (unicorn) |
| `manifest.json`, `SHA256SUMS.txt` | Pinned revisions and checksums |

## Flashing over an existing OpenBeken

1. Back up the settings and flash of your current OpenBeken.
2. In OTA update, upload `firmware/OpenLN882H_WS2805.ota.bin` and let the device reboot.
   This is an image with the LN882H header and a compressed application, not raw compiler output.
3. In LittleFS / Filesystem, upload `autoexec.bat` and reboot the device.
   If you already have your own startup script, merge its contents with this one.
4. In the console, run `WS2805_Status`. Expect `ready=1 bytes=45 DMA failures=0` and `CR1=0000C344`
   (45 = 9 pixels × 5 logical channels).
5. Try `LED_enableAll 1` and the RGB/brightness/temperature controls on the main page.

The `.factory.bin` image is for the LN882H UART flasher, starting at address 0x00000000
(bootloader, partition table, application; standard SDK layout for 2 MiB flash).
Do not upload it via OTA. The images contain no factory provisioning data or passwords.

To change the pixel count, edit the `WS2805_Init <count> BRGWC` line in `autoexec.bat` (1–255).

## Pins and button

| Function | OpenBeken pin | Role |
|---|---:|---|
| WS2805 DATA | P6 / PA6 | SM16703P_DIN (only the name of the shared pin role) |
| IR receiver | P12 / PA12 | IRRecv |
| Button with pull-up, active low | P21 / PB5 | Btn_SmartLED |

Short press toggles power, hold changes brightness, double click cycles colour and triple click
changes white temperature. `SetFlag 4 1` shows the RGB+CCT controls. Keep `PowerSave 0`:
LN882H power saving can alter the SPI, DMA and IR timer clocks.

## IR remote

NEC reception is enabled on P12. Open the log and press a button on the remote.
The line looks like `IR NEC 0xADDRESS 0xCOMMAND 0`; the last value is the repeat/hold flag.
No remote codes are preconfigured. Once you know them, add handlers to `autoexec.bat`, e.g.:

```text
AddEventHandler2 IR_NEC 0xADDRESS 0xCOMMAND LED_enableAll Toggle
```

For separate ON/OFF use `LED_enableAll 1` / `LED_enableAll 0`; a colour can be bound to
`led_basecolor_rgb FF0000`. Holding a button repeats the event, so it is better to map ON and
OFF to separate buttons. Flag 22 publishes received IR codes as JSON over MQTT.

If the remote is not NEC and nothing is decoded, stop `TinyIR_NEC` and start `IR` instead.
Do not run both receivers at the same time.

## First strip test

The SetPixel commands take logical **R G B C W** arguments, even though the wire order is BRGWC.
Call `WS2805_Start` after making changes:

```text
WS2805_SetPixel all 0 0 0 0 0
WS2805_SetPixel 0 64 0 0 0 0
WS2805_Start
```

If cold and warm white are swapped, use `WS2805_Init 9 BRGCW`, and change `autoexec.bat` to match.
After `stopDriver WS2805`, run `startDriver WS2805` and `WS2805_Init 9 BRGWC` again.

If the strip "freezes", first check the DATA and GND terminal screws. A loose terminal
caused exactly this symptom during development.

## Technical details

- WS2805 receives **6 bytes per pixel**: B, R, G, W, C and a zero padding byte
  (same as NeoPixelBus and the stock Tuya firmware). `WS2805_SetRaw` works with 5 bytes per pixel.
- SPI at 20 MHz in **1-line TX** mode (DATA held low between frames, P6 has a pull-down).
  0 = 350 ns high / 950 ns low, 1 = 650 ns high / 650 ns low, 1.30 µs cell.
- 320 µs reset after each frame; a 9-pixel frame takes about 882 µs.
- Transfers have a timeout. On failure, the driver disables the DMA channel, resets SPI0 and
  keeps DATA low.
- `PixelAnim` effects are supported and exposed to Home Assistant discovery when the WS2805
  driver is running. Out-of-range animation indexes are rejected.

### Diagnostics

`WS2805_Status` prints the SPI and GPIO registers and the first 5 logical bytes.
`WS2805_Duplex 1` switches SPI to full duplex, for comparison only; `WS2805_Duplex 0` is the default.
`WS2805_GPIOProbe` sends the current data once, bit-banged on GPIO P6 (max. 10 pixels).

## Building from source

```sh
git clone https://github.com/openshwprojects/OpenBK7231T_App.git
cd OpenBK7231T_App
git checkout 458d0b7f74806af0845c9e492ceee37dbf3f4ded
git apply ../openbk-lsc-3224261/patch/OpenBeken_LN882H_WS2805.patch
cp ../openbk-lsc-3224261/tools/*.py tools/
python tools/build_ln882h_ws2805.py --toolchain C:/path/to/gcc-arm-none-eabi-10.3-2021.10
```

Requires Git, Python, CMake, Ninja and GCC Arm 10.3-2021.10. The script fetches the SDK
(`84149f25`) and Berry at their pinned revisions. Output goes to `sdk/OpenLN882H/build-ws2805/bin`.

Tests: `pip install unicorn`, set `OBK_SOURCE` to the source tree and `ARM_GCC_BIN` to the
toolchain's `bin` directory, then run `python tools/test_ws2805.py`.
