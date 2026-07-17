# Firmware

Copy the locally compiled file here:

```text
jn5189dk6_zigbee_router_bm.bin
```

Generate checksums before release:

```sh
sha256sum jn5189dk6_zigbee_router_bm.bin > SHA256SUMS
md5sum jn5189dk6_zigbee_router_bm.bin > MD5SUMS
```

Review the NXP SDK license before redistributing the compiled binary. A safer public release contains the patch, build instructions, and checksums, but no binary.
