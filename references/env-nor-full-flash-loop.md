# env_nor 全片烧录后无限循环

## 症状
全片烧录（NOR_ALL.bin）首次启动，串口持续输出：
```
[env]ERROR: crc error in section user: expect 0xe1174f33, got 0xffffffff!
[env]ERROR: crc error in section user-backup: expect 0xe1174f33, got 0xffffffff!
[env]ERROR:erase error at 0x8000.ret:-22
```
无限重复，但设备内核其他子系统继续运行。

## 根因
`kernel/linux/drivers/t32_t33/env_nor/layout.h` 定义了 factory 分区内的 section 布局：
- `user` 节：offset 0x8000, size 0x2000 (8KB)
- `user-backup` 节：offset 0x3000, size 0x2000 (8KB)

`env.c` 中 `write_to_flash()` 擦除时地址对齐到 `mtd->erasesize`。EN25QX128A flash 使用 **64KB erase blocks**：
- `addr = 0x8000 & ~(0x10000 - 1)` = `0x0000`
- `mtd_erase(mtd, addr=0, len=64KB)`
- factory 分区仅 56K (0x0-0xE000) → 64KB 擦除超出分区边界 → `-EINVAL`

环境驱动无法写入新数据 → RETRY 死循环。

## 影响范围
- 只在 **全片烧录（NOR_ALL.bin）后首次启动** 出现
- factory 分区被擦除 → CRC 校验失败 → 触发写回 → 写不回
- 分区级烧录 `rootfs system_b` （不擦 factory）不会触发
- 不影响内核其他子系统——设备仍在运行，只是 env 写失败

## 恢复方法
1. **断电重启**：重启后 env_nor 跳过初始化，用户态 `user_env -s` 可正常写入
2. **串口登录**：`killall -9 hilogd 2>/dev/null` 降噪后可用设备，但 env 写入仍不可用
3. 如需彻底修复：将 PRJ.h 中 factory 分区从 56K 扩大到 64KB（对齐到 erase block 边界）
