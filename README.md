![OpenWrt on IgniteNet SunSpot AC Wave2](assets/banner.webp)

# OpenWrt on IgniteNet SunSpot AC Wave2

Installing OpenWrt on the IgniteNet SunSpot AC Wave2 (SS-W2-AC2600, Accton EAP1024A-V2)
**from the stock firmware over SSH**, without opening the case or using a serial console.

The board is supported by OpenWrt (`ipq806x/generic`, profile `ignitenet_ss-w2-ac2600`).
This guide uses the device's dual-boot layout: OpenWrt goes into the unused firmware slot and
the stock firmware stays untouched in the other one.

Tested with OpenWrt 25.12.5. Firmware images are on the [Releases](../../releases/latest)
page (unmodified official builds).

> **Unofficial guide.** You do this at your own risk. Take the full backup in step 2 before
> writing anything.

## Hardware

| Component | Details |
|---|---|
| Model | IgniteNet SunSpot AC Wave2 (SS-W2-AC2600), OEM Accton EAP1024A-V2 |
| SoC | Qualcomm IPQ8064, dual-core Krait 300 (ARMv7) up to 1.4 GHz, NSS cores |
| RAM | 256 MiB DDR3 |
| SPI-NOR | 16 MiB Winbond W25Q128FW: SBL1-3, U-Boot (`APPSBL`), U-Boot env (`APPSBLENV`), `ART` |
| NAND | 128 MiB: `rootfs1` (64 MiB) and `rootfs2` (64 MiB), one firmware slot each |
| Wi-Fi | 2x Qualcomm Atheros QCA9984, 4x4 MU-MIMO (5 GHz up to 160 MHz, 2.4 GHz) |
| Ethernet | 2x GbE: `eth0` (PoE in, 802.3at), `eth1` |
| Stock firmware | IgniteNet v2.1.1, OpenWrt-based, Linux 3.14.77 |

`ART` (`mtd12`) holds the Wi-Fi calibration of your unit. It cannot be recovered from
anywhere else: back it up.

## Stock firmware access

| Setting | Value |
|---|---|
| LAN IP | `192.168.2.1` |
| SSH | `root` / `11111111` |

The stock Dropbear needs legacy algorithms:

```sh
ssh -o KexAlgorithms=+diffie-hellman-group14-sha1 -o HostKeyAlgorithms=+ssh-rsa root@192.168.2.1
```

## How the dual boot works

U-Boot picks the slot from the `active` environment variable (`1` = `rootfs1`, `2` = `rootfs2`),
reads the `kernel` UBI volume from it and boots it with `bootmfit`. On the test unit the stock
firmware ran from `rootfs2` and `rootfs1` was unused. Check yours with `fw_printenv active` before you start.

There is a boot counter (`bootlimit=3`). If a slot fails to boot three times, `altbootcmd` runs:

- if `changed=0`: switch `active` to the other slot, set `changed=1` and reset. This is the
  automatic fallback to stock.
- otherwise: run the vendor recovery, which **erases the whole NAND** (`nand erase.chip`) and
  tries to load the stock `.img` over TFTP from `192.168.1.120`.

So reset `changed` and `bootcount` to `0` before switching slots (step 4). Then a bad OpenWrt
boot falls back to stock instead of wiping the NAND.

## Installation

The steps below assume stock runs from `rootfs2` (`active=2`), so OpenWrt goes to `rootfs1`
(`mtd0`). If your unit runs from `rootfs1`, swap the slots.

### 1. Download the image

`openwrt-25.12.5-ipq806x-generic-ignitenet_ss-w2-ac2600-squashfs-nand-factory.bin` from the
[Releases](../../releases/latest) page or from
[downloads.openwrt.org](https://downloads.openwrt.org/releases/25.12.5/targets/ipq806x/generic/).
Check it against `sha256sums`.

### 2. Back up the flash

Dump every MTD partition to your PC over SSH, straight to disk:

```sh
ssh -o KexAlgorithms=+diffie-hellman-group14-sha1 -o HostKeyAlgorithms=+ssh-rsa \
    root@192.168.2.1 "cat /dev/mtd12ro" > mtd12_ART.bin
```

Do this for all partitions in `/proc/mtd` (`mtd0` to `mtd25` on the test unit), or use
[`tools/backup_mtd.py`](tools/backup_mtd.py), which dumps all of them and checks each one
against an MD5 computed on the device:

```sh
python3 tools/backup_mtd.py --host 192.168.2.1 --out backup_mtd
```

Also save the U-Boot environment: `fw_printenv > uboot_env.txt`.

### 3. Write OpenWrt into the unused slot

Copy the factory image to `/tmp` on the device, then:

```sh
ubiformat /dev/mtd0 -y -f /tmp/openwrt-25.12.5-ipq806x-generic-ignitenet_ss-w2-ac2600-squashfs-nand-factory.bin
```

This creates the `kernel`, `rootfs` and `rootfs_data` UBI volumes in `rootfs1`. `rootfs2`
(stock) is not touched.

### 4. Arm the fallback and switch slots

```sh
fw_setenv changed 0
fw_setenv bootcount 0
fw_setenv active 1
sync
reboot
```

U-Boot now boots OpenWrt from `rootfs1`. OpenWrt comes up at `192.168.1.1`.

## After installation

Standard OpenWrt defaults:

| Setting | Value |
|---|---|
| LAN IP | `192.168.1.1` |
| Login | `root`, no password |
| Wi-Fi | disabled |
| Web UI | LuCI |

The PC was on `192.168.2.x` for the stock firmware. To keep reaching the router there too,
add a second LAN address:

```sh
uci add_list network.lan.ipaddr='192.168.2.1/24'
uci commit network
service network reload
```

Set a root password, then enable Wi-Fi with a password and your own country code.

## Repository layout

| Path | Contents |
|---|---|
| `tools/backup_mtd.py` | dumps all MTD partitions over SSH and verifies them with MD5 |

## License

This guide is licensed under [CC BY 4.0](LICENSE). [`tools/`](tools) is licensed under the
[MIT license](LICENSE-tools). The firmware images in Releases are
unmodified official OpenWrt 25.12.5 builds, licensed under GPL-2.0. Source code:
[openwrt/openwrt @ v25.12.5](https://github.com/openwrt/openwrt/tree/v25.12.5), official
downloads: [downloads.openwrt.org](https://downloads.openwrt.org/releases/25.12.5/targets/ipq806x/generic/).
