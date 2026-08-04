# FIT RSA 签名验证失败分析

## 症状

烧录新编译的 `kernel_system_b.image` 后，设备启动到 U-Boot 时输出：

```
## Loading kernel from FIT Image at 80a00000 ...
   Verifying Hash Integrity ... sha1,rsa2048:rsa_private_key+ OK
## Loading system from FIT Image at 80a00000 ...
   ...
   Verifying Hash Integrity ... sha1,rsa2048:rsa_private_key
FIT RSA verify with SPL key failed: -13
Bad Data Hash
## 'system' subimage verify/load failed (-13)
Could not find a valid filesystem
[bootm_find_other] bootm_find_filesystem error!
PRJ009#
```

- **kernel sub-image**（1.6MB lzma）→ 签名通过 ✅
- **system sub-image**（3.9MB rootfs squashfs）→ 签名失败 ❌
- 设备停在 U-Boot 提示符，无法进入 Linux

## 根因

`kernel_system_b.image` 是 **FIT (Flattened Image Tree)** 格式，包含：
1. kernel sub-image — Linux 内核二进制
2. system sub-image — rootfs squashfs + .ko 模块
3. DTB config 节点
4. 各 sub-image 的 RSA-2048 SHA1 签名

`build.sh hm6502` 执行全量编译时重新生成 rootfs squashfs，size/content 变化后签名失效。原因是：

- Docker 编译环境中的 RSA 签名密钥与 **U-Boot SPL 中硬编码的公钥**不匹配
- 每次 `build.sh` 全量编译，cmake 的 `make all` 会用当前环境的密钥重新签名
- 如果签名密钥不是产品级密钥（如用开发环境中的测试密钥），签名不通过

## 恢复方法

### 方法 A: 从 system_a 手动引导（推荐，最快的恢复路径）

system_a 是出厂 slot，未被分区级烧录覆盖。U-Boot 下执行：

```
sf0 probe
sf0 read 0x80a00000 0x290000 0x570000
setenv bootargs console=ttyS1,1500000n8 mem=85M@0x0 rmem=43M@0x5500000 init=/linuxrc rootfstype=squashfs root=/dev/mtdblock1 ro mtdparts=sfc0_nor:256k(boot),2368k(rootfs),5568k@0x290000(kernel_system_a),5568k@0x800000(kernel_system_b),1536k@0xD70000(algo),56k(factory),4k(env_a),4k(env_b),1024k(log) system=0
bootm 0x80a00000
```

注意：`sf0 read` 的 size 参数必须用分区实际大小 0x570000（不是 bootcmd 里的 0x600000）。

### 方法 B: 烧录旧版能启动的 kernel_system_b.image

如果还保留旧版 `kernel_system_b.image`（签名正确的版本），重新分区级烧录 system_b。

### 方法 C: SwapAB（交换 slot 标识）

如果 system_a 的根因是内容旧但能启动，可以用 SwapAB 二进制让设备永久从 system_a 启动：

```bash
# ADB 可用时
adb push out/image_hm6502/SwapAB /tmp/
adb shell chmod +x /tmp/SwapAB
adb shell /tmp/SwapAB
adb shell reboot
```

## 如何避免

在烧录前验证 kernel_system_b.image 的签名是否匹配：

1. 编译后用 `dumpimage -l kernel_system_b.image` 查看 FIT 内容
2. 对比新 image 的 system sub-image 大小是否和旧版能启动的一致
3. 首次用新编译的 image 烧录时，必须通过串口监控 boot 输出
4. 如果反复出现 RSA 签名失败，说明 build 环境的签名密钥与 U-Boot SPL 不匹配，需修复 build 流程

## 交叉引用

- FIT 镜像格式详细分析（mtdparts 动态改写）：`references/fit-mtdparts-rewrite.md`
- 分区表证据：`references/partition-table-evidence.md`
