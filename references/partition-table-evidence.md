# NOR flash 分区表证据链（HM6801/HM6502/HM6502_B01/HM6503/HM6402 共用）

## 证据 1：U-Boot 源码 mtdparts 定义

**文件：** `device/soc/ingenic/uboot/t32_t33/include/configs/PRJ.h`

第 640 行（CONFIG_FIT 分支，实际使用）：
```c
#if defined(CONFIG_HM6502) || defined(CONFIG_HM6502_B01) || defined(CONFIG_HM6503) || defined(CONFIG_HM6801) || defined(CONFIG_HM6402)
#define BOOTARGS_SFCNOR_PARTITION     " mtdparts=sfc0_nor:256k(boot),2368k(rootfs),5568k@0x290000(kernel_system_a),5568k@0x800000(kernel_system_b),1536k@0xD70000(algo),56k(factory),4k(env_a),4k(env_b),1024k(log)"
#else
#define BOOTARGS_SFCNOR_PARTITION     " mtdparts=sfc0_nor:256k(boot),2368k(rootfs),5568k@0x290000(kernel_system_a),5568k@0x800000(kernel_system_b),1536k@0xD70000(algo),56k(factory),4k(env_a),4k(env_b),1024k(log)"
#endif
```

`#if` 和 `#else` 分支实际相同，说明 NOR flash 家族当前统一使用这套布局。

> ⚠️ 注意：PRJ.h 中 mtdparts 定义的分区布局与 auto_update_tftp.txt 中的实际擦除范围不完全对应。
> auto_update_tftp.txt 的擦除范围是烧录时的实际操作范围，可能与 mtdparts 末尾分区边界不同。
> 以实际文件内容为准（见下表），不盲信文档或历史值。

## 证据 2：仓库自带 auto_update_tftp.txt

**目录：** `device/soc/ingenic/pkg_tool/`

| 项目 | 命令族 | 擦除范围 | 说明 |
|------|-------|---------|------|
| hm6502 | sf probe / erase / write | 0xf60000（默认）/ 0x1000000（全擦） | NOR 全片烧，默认保留尾部 ~640K |
| hm6502_b01 | sf probe / erase / write | 需确认实际文件 | 同构但偏移可能不同 |
| hm6503 | sf probe / erase / write | 需确认实际文件 | 同构但偏移可能不同 |
| hm6801 | sf probe / erase / write | 0x1000000（全16MB） | ⚠️ 临时全擦绕避 log 分区 KV 残留 bug |
| hm6505 | nand erase.chip + nand write | 逐分区 | **NAND 平台，独立布局** |

> **⚠️ 历史演变：** 2026-07-15 实测 hm6502 的 auto_update_tftp.txt 实际擦除范围已从旧值 `0xef0000`
> 变为 `0xf60000`。分区布局随项目演进而调整，擦除范围必须以**实际文件内容**为准，不盲信文档。
> HM6801 的 `0x1000000` 全擦是临时 bug 绕避（未烧录 MAC 地址，log 分区残留 KV 导致 SIGSEGV）。

NOR 四个项目的 auto_update_tftp.txt 结构同构，只有 `hm6XXX_NOR_ALL.bin` 文件名不同。
但擦除范围值可能因分区布局调整而不同，使用前必须 `cat` 确认实际内容。

## 证据 3：构建产物文件名一致

**HM6502 构建产物：** `<项目根>/out/image_<项目>/`
```
algo.img
env.bin
hm6502_NOR_ALL.bin
kernel_system_a.image
kernel_system_b.image
rootfs.img
system_a.img
system_b.img
u-boot-with-spl.bin
```

与 HM6801 构建产物结构完全一致，只有 `<项目>_NOR_ALL.bin` 前缀不同。因此 gen_tftp_script.py 用同一分区表 + 只替换 all-in-one 文件名即可。

## 证据 4：HM6505 是 NAND 完全不同

**文件：** `device/soc/ingenic/pkg_tool/hm6505/auto_update_tftp.txt`

关键片段：
```
nand erase.chip

tftpboot 0x80600000 u-boot-with-spl.bin
nand write 0x80600000 0x0 ${filesize}
tftpboot 0x80600000 rootfs.img
nand write 0x80600000 0x0100000 ${filesize}       ← slot A rootfs
tftpboot 0x80600000 uImage
nand write 0x80600000 0x0a00000 ${filesize}       ← slot A kernel (uImage 而非 kernel_system_x.image)
tftpboot 0x80600000 system_a.img
nand write 0x80600000 0x0d00000 ${filesize}
...
tftpboot 0x80600000 system_b.img
nand write 0x80600000 0x4100000 ${filesize}       ← slot B system 在 65MB 偏移
tftpboot 0x80600000 env.bin
nand write 0x80600000 0x6900000 ${filesize}       ← env 主
nand write 0x80600000 0x6940000 ${filesize}       ← env 备
```

**差异总结：**
- Flash 类型：NAND（`nand write`）vs NOR（`sf write`）
- 分区偏移量数量级：NAND 到 0x6900000+（105MB+），NOR 到 0xf60000~0x1000000（15-16MB）
- 内核镜像文件：NAND 用 `uImage`，NOR 用 `kernel_system_a.image` / `kernel_system_b.image`（FIT 格式）
- A/B 双 slot：NAND 是分开的 rootfs+uImage+system 三份 × 两 slot；NOR 是打包好的 kernel_system_x.image × 两 slot
- env 冗余：NAND 有双备份写偏移，NOR 也有 env_a/env_b 但都在同一 mtdparts

**结论：** HM6505 不能套用本 skill，必须走串口通道或直接用它专属的 auto_update_tftp.txt。

## CONFIG_FIT vs 非 FIT 布局

PRJ.h 第 645-647 行有一份 **非 FIT** 布局（当前项目未启用，仅保留为参考）：

```c
#else  // CONFIG_FIT 未定义时
#define BOOTARGS_SFCNOR_PARTITION     " mtdparts=sfc0_nor:256k(boot),2368k(rootfs),1856k(kernel_a),3712k(system_a),1856k(kernel_b),3712k(system_b),1536k@0xD70000(algo),56k(factory),4k(env_a),4k(env_b),1024k(log)"
```

这个把 kernel 和 system 分开成两个分区，产物文件名会是 `kernel_a.img` + `system_a.img`（不带 kernel_system 合并）。当前 HM6801/6502 系都是 FIT 模式，gen_tftp_script.py 也按 FIT 布局。**如果将来切回非 FIT，需要扩展 gen 脚本支持第二套布局。**

## 相关信息

- CPSPR 触发寄存器地址 0x10000034/38：来自 `flash_6801` 包中 `mai_auto_flash.sh`。已在 HM6801 和 HM6502 实测通用（2026-07-11）。
- 定制 adb `ip-reset-and-wait` 子命令：来自 `third_party/android_port/system/core/adb`。HM6501/HM6502/HM6801 都基于同一 android_port，命令通用。
