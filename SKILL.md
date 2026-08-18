---
name: adb-tftp
description: Ingenic T32 NOR ADB TFTP 分区烧录：CPSPR 触发 U-Boot，回连免串口查IP。适配 HM6801/HM6502/HM6503/HM6402，HM6505 NAND 除外。
version: 1.2.0
category: devops
metadata:
  hermes:
    triggers: [adb烧录, cpspr, mai_auto_flash, ip-reset-and-wait, 分区烧录, hm6801烧录, hm6502烧录, hm6503烧录, hm6402烧录, gen_adbd_conf, user_env, prepare烧录环境]
---

# Ingenic ADB 通道 TFTP 烧录（adb-tftp）

> 用户指挥 AI，AI 替用户执行。给意图就干不反问：听到"烧录"直接按本 skill 流程执行，禁止先列串口步骤、禁止让用户手动输入。依赖缺失（adb/脚本/网络）→ 对话层引导用户确认后写入，不让用户敲命令。

## ⚡ 一键命令

```bash
# 分区级烧录（保留 env/log）
cd <项目根>
python3 <skill>/scripts/gen_tftp_script.py --project <项目> --output-dir out/image_<项目> rootfs system_b
bash <skill>/scripts/mai_auto_flash.sh "" <设备IP>:5555
```

| 项目 | 波特率 | TFTP 目录 |
|------|--------|-----------|
| HM6502 | 921600 | <项目根>/out/image_<项目> |
| HM6801 | 115200 | <项目根>/out/image_<项目> |

**安全前置提醒：** CPSPR 可能连续失败→3 次熔断转串口；`mai_auto_flash.sh` 必须用 original mode（传 NIC），simple mode 的 serverip 解析错误。坑 / 反模式 / 排障速查全量在 `references/troubleshooting.md`。

## 脚本行为要点（2026-08-04 更新）

- `gen_tftp_script.py`：`ALL_ERASE_SIZE` 改为 `PARTITIONS["algo"].offset+size` 推导，改 algo 分区时擦除范围自动跟随；分区表已更新为 2026-07-17 后布局（sysB 6080k@0x800000、algo 1024k@0xDF0000、factory 0xEF0000）。
- `mai_auto_flash.sh`：IP 编码模式 CPSPR `0x97060909` 首试即可触发进 TFTP 模式（U-Boot 正确解码 serverip=主机 IP）。**必须用 original mode（传 NIC 参数）**：`mai_auto_flash.sh enp2s0 <ADB_SERIAL>`。simple mode（单参数）固定 CPSPR 0x00000909，U-Boot 解析 server IP 错误（实测解析出 <错误网段IP>）→ TFTP T T T T 失败 → autoboot fallback 回 Linux（2026-08-04 实测）。
- **ADB 预检**：`adb devices` 空别急判不通——设备在内核时经串口 `ifconfig`+`netstat -tnl|grep 5555` 查 IP/adbd → `adb connect <IP>:5555` → 若 `offline` 则 `adb kill-server` 重连即好（ADB server 状态不对常致 offline）。
- **烧后重连**：env 保留但 DHCP 可能换 IP；扫 /23 的 5555，多台设备按 `cat /proc/uptime` 辨识刚烧的（uptime 最短）。

## ⚡ 快速参考

**适用项目（NOR flash + 共享 mtdparts）：** HM6801 / HM6502 / HM6502_B01 / HM6503 / HM6402
  证据：`device/soc/ingenic/uboot/t32_t33/include/configs/PRJ.h` 第 640 行明确
  `CONFIG_HM6502 || CONFIG_HM6502_B01 || CONFIG_HM6503 || CONFIG_HM6801 || CONFIG_HM6402` 共用
  同一份 `BOOTARGS_SFCNOR_PARTITION`。产物文件名结构 (`rootfs.img` / `kernel_system_a.image`
  / `kernel_system_b.image` / `algo.img` / `env.bin` / `<项目>_NOR_ALL.bin`) 完全一致。

**不适用：**
- **HM6505** —— NAND flash 平台，`nand erase.chip + nand write` 命令族，偏移量数量级完全
  不同（例：slot A rootfs 在 0x0100000，slot B system 在 0x4100000）。用它专属的
  `device/soc/ingenic/pkg_tool/hm6505/auto_update_tftp.txt`，走串口通道刷。
- 设备离线 / adbd 挂死 / kernel panic / U-Boot 环境损坏 → 用串口通道 skill 兜底。

**首次使用（prepare -- 一次性环境准备）：**
```bash
SKILL=<skill>/scripts

# 1) 编译定制 adb（支持 ip-reset-and-wait，自动等设备回连）
cd <项目根>/third_party/android_port && mkdir -p pc && cd pc
cmake ../ && make -j8 && sudo cp adb /usr/bin/adb

# 2) 生成设备配置（adbd_report.conf + 固定 MAC）
cd /tmp
bash $SKILL/gen_adbd_conf_noninteractive.sh <设备名>   # 如 <项目>_dev01

# 3) 推送到设备（需先 adb connect）
adb connect <设备IP>:5555
adb push /tmp/adbd_report.conf /data/
adb shell user_env -s server <主机IP>
adb shell user_env -s mac <生成的MAC>
adb shell sync
```

**日常烧录：**
```bash
PROJECT=<项目>           # 或 hm6801 / hm6502_b01 / hm6503 / hm6402
SERIAL=<设备名>           # adbd_report.conf 里的 device_name（定制 adb 自动发现）
SKILL=<skill>/scripts
OUT=out/image_$PROJECT

# 1) 起 TFTP server（每 session 一次；systemd tftpd-hpa 请先 disable）
sudo pkill in.tftpd 2>/dev/null || true
sudo /usr/sbin/in.tftpd -l -s $OUT

# 2) 生成分区烧录脚本（默认 rootfs + system_b）
python3 $SKILL/gen_tftp_script.py --project $PROJECT --output-dir $OUT rootfs system_b

# 3) 触发烧录（推荐 IP 编码模式）
bash $SKILL/mai_auto_flash.sh "" $SERIAL           # IP 编码模式
# 或指定网卡：bash $SKILL/mai_auto_flash.sh enp2s0 $SERIAL

# 4) 等设备回来
adb ip-reset-and-wait $SERIAL          # 定制 adb 阻塞等待，自动发现回连

# 5) 验证
adb -s $SERIAL shell echo "flash complete"
```

## 通道选择

| 场景 | 用哪个通道 |
|------|-------------|
| 项目 NOR 家族且 ADB 在线，只想烧 rootfs+system_b | **本 skill**（快、静、可选分区） |
| 只烧单个分区（algo / system_a / env 等） | **本 skill** |
| 设备离线 / adbd 挂死 / 串口 kernel panic loop / 设备已在 U-Boot 提示符 | 串口通道（可复用本 skill 的 gen_tftp_script.py 生成分区级脚本） |
| HM6505（NAND 平台） | 串口通道 |
| 首次配置设备 / 新设备 | **本 skill** prepare 流程（gen_adbd_conf + user_env） |
| U-Boot 环境损坏、bootcmd 失效 | 串口通道 |
| 全片重刷 NOR_ALL.bin | 两者都行，串口通道更稳（不依赖 adbd） |

## 烧录原理

**主机不主动推，设备主动拉。** 流程：
1. (ADB 在线时) 主机 adb → 设备 `devmem` 写 CPSPR 寄存器（0x10000034/38），编码主机 IP 的第 3、4 段为 `0xXXYY0909`
2. 主机 adb → 设备 `reboot`
3. U-Boot 启动检测寄存器标志 → 进入 TFTP 模式
4. 设备从主机 TFTP server 拉 `auto_update_tftp.txt` 并逐分区烧写
5. 设备重启 → adbd 起来 → 主机 `ip-reset-and-wait` 解锁

> **⚠️ CPSPR 触发可能不稳定**：写成功 + reboot 发出但设备可能不进 TFTP（历史实测与连续失败分析见 `references/troubleshooting.md`）。连续失败 3 次熔断转串口通道；串口也不通时用「ADB 直写 mtd 分区」。

TFTP server **必须在 reboot 前就已运行**，否则设备在 U-Boot 里超时找不到脚本。

CPSPR 寄存器地址（0x10000034/38）已在 HM6801 和 HM6502 实测通用（2026-07-11 HM6502 端到端 all 全片烧成功）。HM6502_B01/HM6503/HM6402 首次使用建议先用 `all` 全片模式试烧一次（不依赖分区表，风险低），确认 CPSPR 触发通用后再分区级。

### ⚠️ 关于 CMDLINE 里 `system_b` 偏移大小

FIT 模式设备运行时 `/proc/cmdline` 会动态显示 system_b 的不同偏移（如 `4141056@0x974200(system_b)`）。
这是 U-Boot bootm 时**运行时动态改写的产物**，不是 flash 分区表。**不要按 CMDLINE 的偏移烧录。**

分区级烧录必须按 `PRJ.h` 的 `BOOTARGS_SFCNOR_PARTITION` 编译期定义。详见 `references/fit-mtdparts-rewrite.md`。

## NOR 家族分区表（HM6801/HM6502/HM6502_B01/HM6503/HM6402 共用）

**权威源：** `device/soc/ingenic/uboot/t32_t33/include/configs/PRJ.h`
`BOOTARGS_SFCNOR_PARTITION` (CONFIG_FIT 分支)：

> ⚠️ PRJ.h 中的 `BOOTARGS_SFCNOR_PARTITION` 可在开发过程中被修改（如调整 kernel/log 分区大小）。
> 以下分区表是当前最新提交的标准布局。如果 PRJ.h 被修改过，烧录前必须在 PRJ.h 中确认实际分区表。
>
> 🔧 **权威源 = `gen_tftp_script.py` 的 PARTITIONS 表**（改分区表时 `ALL_ERASE_SIZE` 自动跟随 algo 末尾）。下表若与脚本不一致以脚本为准。2026-07-17 改过分区：sysB 5568k→6080k@0x800000、algo 1536k→1024k@0xDF0000，factory/env/log 前移。

```  /* 标准布局 (HM6502/HM6503/HM6801/HM6402, 2026-07-17 后) */
sfc0_nor: 256k(boot), 2368k(rootfs),
          5568k@0x290000(kernel_system_a),
          6080k@0x800000(kernel_system_b),
          1024k@0xDF0000(algo),
          56k(factory), 4k(env_a), 4k(env_b),
          1024k(log)
```

| 分区名 | 偏移 | 大小 | 文件 | gen_tftp_script 关键字 | 备注 |
|--------|------|------|------|------------------------|------|
| boot (uboot) | 0x000000 | 256K | u-boot-with-spl.bin | `uboot` | ⚠️ 变砖风险，除非改了 U-Boot 否则不烧 |
| rootfs | 0x040000 | 2368K (≈2.3M) | rootfs.img | `rootfs` | 默认烧 |
| kernel_system_a | 0x290000 | 5568K (≈5.6M) | kernel_system_a.image | `system_a` | 出厂 slot |
| kernel_system_b | 0x800000 | 6080K (≈5.9M) | kernel_system_b.image | `system_b` | 默认烧（用户 slot） |
| algo | 0xDF0000 | 1024K (1M) | algo.img | `algo` | AI 模型 |
| factory | 0xEF0000 | 56K | (仅擦除) | `factory` | 出厂标定 |
| env_a | 0xEFE000 | 4K | env.bin | `env_a` / 别名 `env` | 主 env |
| env_b | 0xEFF000 | 4K | env.bin | `env_b` | 备份 env |
| log | 0xF00000 | 1024K | (仅擦除) | `log` / 别名 `data` | JFFS2 日志分区 |
| all | 0x000000 | 0xEF0000 (~14.94M) | `<项目>_NOR_ALL.bin` | `all` | 擦 [0,0xEF0000)：boot+rootfs+sysA+sysB+algo，**保留 factory/env/log** ⚠️ 见下方说明 |

**两个常见变体：**

| 项目 | 变体 | 差异 |
|------|------|------|
| HM6502_B01 | line 641 | `2240k(rootfs),5888k@0x270000(kernel_system_a),5888k@0x830000(kernel_system_b),512k(log)` |
| 旧标准（< 2026-07-17） | — | `2368k(rootfs),5568k@0x290000(kernel_system_a),5568k@0x800000(kernel_system_b),1536k@0xDB0000(algo),56k@0xF30000(factory),768k@0xF40000(log)` |

**注意：** `all` 擦 [0, 0xEF0000)，**保留 factory/env/log**——env 含网络/ADB 配置，故 `all` 模式 adbd 配置仍在，但 DHCP 可能换 IP，需扫 5555 + 按 uptime 辨识重连。
  - 若确实擦了 env（如手动 `sf erase 0xEFE000 ...`），则需串口恢复：登录 → 设静态 IP → 启 adbd → 重配 adbd_report.conf → 重启 adbd

**factory 分区对齐问题：** factory 分区 56K 与 flash 64KB erase block 不兼容。`env_nor` 驱动的 `user` 节（偏移 0x8000/32K 位于 factory 内）擦除时对齐到 64KB block 边界 → 需擦 64KB 但 factory 只有 56K → 超边界 → `mtd_erase` 返回 `-EINVAL` → 驱动无限循环。这是硬件设计问题，不影响正常使用（仅在全片烧首次启动时触发）。若需彻底修复，将 factory 扩大到 64KB。

**默认分区 = `rootfs system_b`** ——
- 不动 env → 保留网络/ADB/系统配置
- 不动 log → 保留日志（HM6801 曾因 log 分区残留 KV 数据触发 SIGSEGV，如遇到用 `all` 全片擦）
- 不动 uboot → 避免变砖
- 不动 system_a → 保留出厂 slot，可作恢复出厂用

### ⚠️ 分区表可在 PRJ.h 中修改

以上分区表是当前标准布局。`PRJ.h` 中 `BOOTARGS_SFCNOR_PARTITION` 可被修改（如调整 kernel/log 大小）。
此时：
- `gen_tftp_script.py` 硬编码偏移**不再匹配**，必须手动生成自定义 `auto_update_tftp.txt`
- **U-Boot SPL 密钥与新 FIT 签名绑定** → 改了 PRJ.h 后 build 会重编 U-Boot，新 SPI 密钥签名新 FIT。
  旧 U-Boot 的密钥不匹配，启动报 `FIT RSA signature verify failed`。必须联动烧录 uboot + kernel_system_b

**验证：** 烧录后串口监控 boot 输出。若签名失败，从 system_a 手动引导（见 `references/troubleshooting.md`）。

## 前置准备（一次性）

### 1. tftpd-hpa 装二进制但关服务

```bash
sudo apt install tftpd-hpa
sudo systemctl stop tftpd-hpa
sudo systemctl disable tftpd-hpa   # 避免和临时 in.tftpd 抢 69 端口
ls /usr/sbin/in.tftpd
```

> 与串口通道的差异：串口通道用 systemd 常驻服务 + 固定 TFTP_DIRECTORY；本 skill 每 session 起临时 in.tftpd 指向当前项目 out 目录。两者不能同时用，日常烧录步骤会 `pkill in.tftpd`。

### 2. 定制 adb（支持 ip-reset-and-wait）

标准 Android SDK 的 adb 没有 `ip-reset-and-wait` 子命令，必须编译项目自带版本：

```bash
cd <项目根>/third_party/android_port
mkdir pc && cd pc
cmake ../
make -j8
adb kill-server                    # 必须先停 adb daemon，否则 "Text file busy"
sudo cp adb /usr/bin/adb
adb ip-reset-and-wait --help   # 验证
```

### 3. 设备 adbd_report.conf + 固定 MAC（一键配置）

使用 skill 自带的 `gen_adbd_conf_noninteractive.sh` 一键生成配置：

```bash
cd /tmp
bash <skill>/scripts/gen_adbd_conf_noninteractive.sh <设备名> [网卡名]
# 输出格式：
#   CONF_FILE=adbd_report.conf
#   HOST_IP=<主机IP>
#   MAC=02:ab:cd:ef:12:34
#   NIC=enp2s0
#   DEVICE_NAME=<设备名>
```

脚本会：
1. 自动获取主机网卡 IP
2. 生成 `adbd_report.conf`（server_ip + device_name + monitor_iface）
3. 基于主机 IP + 设备名生成确定性本地单播 MAC（相同输入始终产生相同 MAC）

生成后推送到设备（需 ADB 已连接）：

```bash
adb -s <设备名> push /tmp/adbd_report.conf /data/
adb -s <设备名> shell user_env -s server <主机IP>
adb -s <设备名> shell user_env -s mac <生成的MAC>
adb -s <设备名> shell sync
adb -s <设备名> shell user_env -g    # 验证
```

**一次性配置**：除非刷了 env 分区，否则只需配置一次。主机 IP 变了需重新执行。（固定 MAC 的决策原因见 `references/troubleshooting.md`）

**⚠️ 推送 conf 后必须重启 adbd**：设备 adbd 不会自动重新读取 `/data/adbd_report.conf`。
推送配置后执行 `adb shell kill -9 $(adb shell pidof adbd)`，init 会重拉 adbd，
新 adbd 启动后约 10 秒内通过心跳向主机上报设备名和 IP，主机 `adb ip-devices` 可看到。
在重拉前 `ip-devices` 和 `ip-reset-and-wait` 都找不到设备名。

## 完整执行流程

### Step 0: 烧录前分区校验（PRJ.h 修改后必做）

当 `device/soc/ingenic/uboot/t32_t33/include/configs/PRJ.h` 中 `BOOTARGS_SFCNOR_PARTITION` 被修改时，烧录前必须校验所有产物大小 ≤ 新分区大小，并确认偏移连续性。重点关注 **kernel_system_b**（最接近分区上限）和 **env.bin**（40K 离线备用文件不直接烧，忽略误报）。

### Step 1: 环境检查

必须存在：
- `<项目根>/build/Makefile`
- `<项目根>/out/image_<项目>/`（含 rootfs.img / kernel_system_b.image / <项目>_NOR_ALL.bin 等）
- `/usr/sbin/in.tftpd`
- adb（定制版推荐，标准 Android SDK 也可 -- 等 ADB 回来有 fallback 路径）
- 串口可用（`/dev/ttyUSB0` 等，DHCP 换 IP 或 ADB 不通时需要串口恢复）
- 当前工作目录 = 项目根

### Step 2: 编译（可选）

**仅当用户明确说"编译/make/build/构建"时执行**，否则跳过：

```bash
cd build && sudo make
```

失败立即停止，不进后续步骤。

### Step 3: TFTP server（每 session 一次）

```bash
# 检查是否已有指向本项目 out 的 tftpd
ps aux | grep "in.tftpd" | grep "out/image_$PROJECT" | grep -v grep

# 没有则起
sudo pkill in.tftpd 2>/dev/null || true
sudo /usr/sbin/in.tftpd -l -s out/image_$PROJECT
```

### Step 4: 生成 auto_update_tftp.txt

```bash
python3 <skill>/scripts/gen_tftp_script.py \
    --project $PROJECT \
    --output-dir out/image_$PROJECT \
    rootfs system_b
```

产物：`out/image_<项目>/auto_update_tftp.txt`

### Step 5: 触发烧录

```bash
# 推荐：IP 编码模式（编码主机 IP）
bash <skill>/scripts/mai_auto_flash.sh "" $SERIAL
# 或指定网卡
bash <skill>/scripts/mai_auto_flash.sh enp2s0 $SERIAL
```

- simple 模式：只传设备名（如 `<项目>_dev01`），CPSPR 固定 `0x00000909` ⚠️ serverip 解析错误风险
- IP 编码模式：传 NIC + serial，CPSPR 编码主机 IP 为 `0xXXYY0909`
- 两种模式底层一致：`devmem 0x10000038 32 0x5a5a && devmem 0x10000034 32 <VALUE> && devmem 0x10000038 32 0xa5a5 && reboot`

### Step 6: 等 ADB 回来

**方式 A: 定制 adb（推荐，需前置准备第 2 步已完成）**

```bash
adb ip-reset-and-wait <adb_serial>
# 成功输出：OK <name> <ip> <port>
# 默认 120s 超时（正常 ~20s：reboot + 烧录 + DHCP + adbd）
```

**方式 B: 标准 adb 轮询（无定制 adb 时）**

定制 adb 不可用时（`adb: unknown command ip-reset-and-wait`），用标准 adb 轮询重连：

```bash
# 尝试原 IP 重连（30s 内通常回来）
for i in $(seq 1 20); do
    adb connect <原IP>:5555 2>/dev/null | grep -q connected && {
        echo "设备已回来 (${i}x3s)"; break
    }
    sleep 3
done
```

注意：DHCP 重启后可能换 IP，方式 B 超时后转方式 C。

**方式 C: 串口恢复（ADB 完全不通时）**

烧录后设备 DHCP 换 IP 或 adbd 异常时，通过串口手动恢复：

1. 串口登录（波特率见设备 /proc/cmdline 的 console= 参数，**不要盲信 skill 文档值**）
   - **以 `adb shell cat /proc/cmdline | grep console` 的实际值为准**，文档值可能过时或因固件版本不同而变化
   - 串口交互必须用 `\r`（CR）而非 `\n`（LF）。stty raw 模式下 getty/login 只认 `\r`
2. 设静态 IP（DHCP 多轮重启后可能不分配 IP）
   ```
   ifconfig eth0 <同网段IP> netmask 255.255.254.0 up
   ```
3. 主机 adb connect 新 IP
   ```bash
   adb connect <新IP>:5555
   ```

串口日志洪流过滤：用 NOISE 关键字列表过滤行（IndHandle/MikeInit/IPCMain/MI IPC/StatReport/AudioTrack/AudioMixer/mible_/rpc/hexdump 等），只保留命令输出。

> **关键**: 串口交互必须用 `\r`（CR）而非 `\n`（LF）。stty raw 模式下 getty/login 只认 `\r`。

### Step 7: 验证

```bash
adb -s <adb_serial> shell echo "flash complete"
adb -s <adb_serial> shell cat /proc/version   # 确认内核时间戳新
```

**烧录后首次启动必须通过串口监控 boot 输出。** 检查以下关键字：
- `FIT RSA signature verify failed` → 内核 FIT 签名不匹配，设备停在 U-Boot 提示符，需恢复
- `Bad Data Hash` → 同上
- 正常启动标志 + `login:` → 正常启动 ✅

如果 FIT RSA 签名失败，恢复方法：
1. U-Boot 提示符下手动从 **system_a**（出厂 slot，未被覆盖）引导
2. 或重新烧录旧版能用的 kernel_system_b.image
3. 或修复 build 的 FIT 签名流程

system_a 手动引导命令（U-Boot 提示符下）：
```
sf0 probe
sf0 read 0x80a00000 0x290000 0x570000
setenv bootargs console=ttyS1,1500000n8 mem=85M@0x0 rmem=43M@0x5500000 init=/linuxrc rootfstype=squashfs root=/dev/mtdblock1 ro mtdparts=sfc0_nor:256k(boot),2368k(rootfs),5568k@0x290000(kernel_system_a),5568k@0x800000(kernel_system_b),1536k@0xD70000(algo),56k(factory),4k(env_a),4k(env_b),1024k(log) system=0
bootm 0x80a00000
```
注意：`sf0 read` 的 size 参数必须用分区实际大小 0x570000，不要用 bootcmd 中的 0x600000（会读到 system_b 区域）。

## 参数速查

### `mai_auto_flash.sh [NIC] [ADB_SERIAL]` 或 `mai_auto_flash.sh <ADB_SERIAL>`

两种调用模式：

| 模式 | 调用 | CPSPR 值 | 适用场景 |
|------|------|----------|----------|
| simple | `mai_auto_flash.sh <serial>` | 固定 0x00000909 | 已配 adbd_report.conf，设备名含 `:` 或 `cam_`/`hm_` 前缀 ⚠️ serverip 解析错误风险 |
| IP 编码 | `mai_auto_flash.sh [NIC] [serial]` | 0xXXYY0909（编码主机 IP） | 传统模式，NIC 留空则自动检测 |

| 场景 | 调用 |
|------|------|
| IP 编码模式（推荐） | `mai_auto_flash.sh "" <IP>:5555` |
| 单设备 + 指定网卡 | `mai_auto_flash.sh enp2s0 <IP>:5555` |
| 多设备 + 默认网卡 | `mai_auto_flash.sh "" cam_front_01` |
| 多设备 + 指定网卡 | `mai_auto_flash.sh eth0 cam_front_01` |

网卡自动检测：`/sys/class/net/` 下第一个 `en*` 或 `eth*`，兜底 `eth0`。

### `gen_adbd_conf_noninteractive.sh <DEVICE_NAME> [NIC]`

非交互式生成 adbd_report.conf + 确定性 MAC。输出 KEY=VALUE 格式便于脚本解析。

```bash
bash gen_adbd_conf_noninteractive.sh <设备名>
# CONF_FILE=adbd_report.conf
# HOST_IP=<主机IP>
# MAC=02:a1:b2:c3:d4:e5
# NIC=enp2s0
# DEVICE_NAME=<设备名>
```

生成后需推送到设备并配置 user_env（见前置准备第 3 步）。

### `gen_tftp_script.py`

```
gen_tftp_script.py [--project <name>] [--output-dir DIR] <partition>...
gen_tftp_script.py [--project <name>] [--output-dir DIR] all
```

- `--project` 缺省时按 `--output-dir` 路径中的 `image_<项目>` 自动识别，识别不到默认 `hm6801`
- 支持项目：`hm6801` / `hm6502` / `hm6502_b01` / `hm6503` / `hm6402`
- `hm6505` 会明确报错拒绝
- `all` 不能和其他分区混用（生成整片擦写脚本，用 `<项目>_NOR_ALL.bin`）
- 兼容：`gen_tftp_script_6801.py` 是同一脚本的软链接

## ADB 直写 mtd 分区（CPSPR + 串口都失败时的最后手段）

当 CPSPR 触发不进 TFTP 且串口不通时，可通过 ADB 直接写 mtd 分区。**此方法有风险，仅在 TFTP 通道完全不可用时使用。**

### 前提

- ADB 在线（设备正常运行，adbd 可用）
- 设备有 `flash_eraseall`（busybox applet）和 `dd`（busybox applet）
- 镜像文件已 push 到设备 /tmp

### 流程

```bash
# 1. push 镜像
adb push out/image_$PROJECT/rootfs.img /tmp/rootfs.img
adb push out/image_$PROJECT/kernel_system_b.image /tmp/kernel_system_b.image

# 2. 确认 mtd 分区映射
adb shell cat /proc/mtd
# 典型: mtd1=rootfs, mtd3=system_b

# 3. 擦除 + 写入（每个分区：先擦后写）
adb shell 'flash_eraseall -q /dev/mtd1 && dd if=/tmp/rootfs.img of=/dev/mtd1 bs=4096'
adb shell 'flash_eraseall -q /dev/mtd3 && dd if=/tmp/kernel_system_b.image of=/dev/mtd3 bs=4096'

# 4. 验证（读回 MD5 比对）
adb shell 'dd if=/dev/mtd1 bs=4096 count=<blocks> 2>/dev/null | md5sum'
# 与主机 md5sum rootfs.img 比对

# 5. 重启
adb shell reboot
```

> 关键陷阱与 `pack_firmware` 覆盖问题见 `references/troubleshooting.md`。

## 交叉引用

- 串口通道兜底：`ingenic-basic-tftp-flash` skill（同 category devops）
- U-Boot mai_tftp 命令详解、擦除范围演化史、NOR_ALL.bin 布局：见串口通道 skill
- 定制 adb 源码位置：`third_party/android_port`（项目内）
- 分区表证据链（PRJ.h mtdparts / 仓库 auto_update_tftp.txt / HM6505 NAND 差异）：见 `references/partition-table-evidence.md`
- FIT 镜像 mtdparts 动态改写机制（system_b 运行时生成原理 + 源码证据链）：见 `references/fit-mtdparts-rewrite.md`
- FIT RSA 签名验证失败分析（症状、根因、恢复方法、如何避免）：见 `references/fit-rsa-signature-issue.md`
- 坑 / 反模式 / 排障速查 / 决策原因：见 `references/troubleshooting.md`
- env_nor 全片烧录后无限循环问题分析：见 `references/env-nor-full-flash-loop.md`

## 支持文件清单

- 脚本：`scripts/gen_tftp_script.py`、`scripts/mai_auto_flash.sh`、`scripts/gen_adbd_conf_noninteractive.sh`
- 参考：`references/partition-table-evidence.md`、`references/fit-mtdparts-rewrite.md`、`references/fit-rsa-signature-issue.md`、`references/env-nor-full-flash-loop.md`、`references/troubleshooting.md`
