# ADB 通道 TFTP 烧录排障（troubleshooting）

> 定位：本文件承载 SKILL.md 主流程之外的全部**坑 / 反模式 / 决策原因**。
> SKILL.md 只留干净主流程；遇到问题按症状查本文件（A 模式分层，2026-08-04 拆分）。

## 反模式（操作前预防）

| 反模式 | 后果 | 正确做法 |
|--------|------|---------|
| ADB 断了硬用本 skill | mai_auto_flash.sh 无法写 CPSPR，reboot 也发不出去 | 回退到串口通道 |
| `mai_auto_flash.sh <serial>` simple 模式报 `error: device not found` | 设备未通过定制 adb 注册名称（如 `<项目>_dev01`），`adb devices` 只显示 `IP:5555` 格式 | 用 IP 编码模式：`mai_auto_flash.sh "" <IP>:5555`，或先配 adbd_report.conf 注册设备名 |
| PRJ.h 修改了分区表但烧录时没更新 uboot | build 重编 U-Boot 产生新 SPL 公钥签名新 FIT。旧 U-Boot 的 SPL 公钥不匹配，启动报 `FIT RSA signature verify failed (SPL key)`. | 改了 PRJ.h 后必须**联动烧录** uboot + rootfs + system_b（以及所有偏移变化的分区）。`gen_tftp_script.py` 的硬编码偏移也需手动更新。 |
| tftpd-hpa systemd 服务没关就跑本 skill | 端口 69 被占，临时 in.tftpd 起不来，报错含糊 | 前置准备第 1 步 disable systemd 服务；日常烧录会 pkill 兜底 |
| 不指定 adb serial 多设备烧 | mai_auto_flash.sh 里 `adb shell` 命中错误设备（甚至变砖别人的机器） | 多设备必须传 serial |
| server_ip 未更新就烧 | 设备烧完不回连，`ip-reset-and-wait` 超时 | 换主机或主机 IP 变了 → 重推 `/data/adbd_report.conf` |
| 用标准 Android SDK 的 adb | `ip-reset-and-wait: unknown command` | 编译并覆盖 `/usr/bin/adb`（前置准备第 2 步） |
| **把本 skill 用到 HM6505** | HM6505 是 NAND 平台，命令族和偏移完全不同，硬跑要么 U-Boot 直接报 unknown command，要么写坏 flash | HM6505 用串口通道走它自己的 auto_update_tftp.txt |
| 换未验证项目不核对 mtdparts | 假设分区表一样但实际不同，擦写偏移错位 -> 内核/rootfs 打飞 -> 变砖或反复 kernel panic | 换项目前 `fw_printenv bootargs` 或看 `device/soc/ingenic/pkg_tool/<项目>/auto_update_tftp.txt`。当前 NOR 家族 (HM6801/6502/6502_B01/6503/6402) 已由 PRJ.h 确认共用，其他新项目要重新核对。注意：U-Boot 优先读`env`里 bootargs，出厂可能留存旧错误值；全片烧（`all` 模式擦 0x0-0x1000000）会覆盖 env 分区，全擦后默认环境变量生效。 |
| `all` + 其他分区混传 | gen 脚本报错 `'all' cannot be combined` | `all` 单独用（整片烧 NOR_ALL.bin） |
| 编译后忘了 `make pack_firmware` | out/image_<项目>/ 里镜像是旧的，烧了也没变化 | 编译流程要 `make && make pack_firmware`；bootloader 改动加 `make pack_all` |
| 工作目录不是项目根就跑 | out/image_<项目>/ 路径不对，TFTP server 起在错误目录，找不到镜像 | 先 `cd <项目根>` 再调用 |
| `rm -rf out/image_xxx` 后重编但**没重启 TFTP server** | 进程持有旧 inode，服务的是已删除目录下的旧文件。烧录验证后设备上的 .ko 还是旧版 | 删 out/ 后必须重启 tftpd：`sudo pkill in.tftpd && sudo /usr/sbin/in.tftpd -l -s out/image_$PROJECT` |
| **从 system_a 手动引导时 `sf0 read` 大小参数超出分区边界**（如 `sf0 read 0x80a00000 0x290000 0x600000`，但 system_a 实际只有 0x570000=5568K） | U-Boot 读超分区边界后**串口完全无响应**（字符不回显、无 shell 提示符），进入硬死锁，必须物理断电恢复 | `sf0 read` 的 size 参数必须 **≤ 分区实际大小**。推荐各命令分步单独发送（不要 `&&` 链式），防止部分执行丢失串口控制权 |
| **CPSPR simple mode（单参数）** | 固定 0x00000909，U-Boot 解析 server IP 错误（实测解析出 <错误网段IP>）→ TFTP T T T T 失败 → autoboot fallback 回 Linux，白跑一轮 | 用 IP 编码模式：`mai_auto_flash.sh enp2s0 <ADB_SERIAL>`（编码主机 IP → CPSPR 0xXXYY0909）。失败特征：串口见 `T T T T` + `Retry count exceeded`（2026-08-04 实测） |

## 故障排查（按症状）

| 症状 | 原因 | 处理 |
|------|------|------|
| `ip-reset-and-wait` 超时 120s | server_ip 不对 / 主机 IP 变了 / TFTP server 没起 / 设备烧完起不来 | 检查 `ps aux \| grep tftpd`、设备的 `/data/adbd_report.conf`、`ip -4 addr show <NIC>`；仍不通接串口看设备停哪 |
| **`all` 全片烧录后 `ip-reset-and-wait` 必超时** | 全片擦 0x0-0x1000000 包含 env 分区，adbd_report.conf 和 user_env（server_ip/mac/device_name）全丢。设备重启后 adbd 不知道 server IP，不主动上报心跳 | 串口恢复：①串口登录 ②`ifconfig eth0 <IP> netmask <MASK> up` ③`/bin/adbd --root &` ④`adb connect` ⑤重推 adbd_report.conf + 配置 user_env（前置准备第3步） ⑥`killall -9 adbd` 重启 adbd。之后恢复 ip-reset-and-wait 流程。**分区级烧录（rootfs system_b）不擦 env，无此问题** |
| `adb: unknown command ip-reset-and-wait` | 标准 Android SDK adb 无此子命令 | 用等 ADB 回来方式 B（adb 轮询）或方式 C（串口恢复） |
| 烧后 DHCP 换 IP，adb connect 原 IP 超时 | 设备重启后 DHCP 分配了新 IP | 串口登录 -> `ifconfig eth0` 查新 IP -> adb connect 新 IP；或直接设静态 IP（见等 ADB 回来方式 C） |
| `adb: no devices/emulators found` | ADB 已断线，或初始就没连 | 先跑 `adb devices` 确认，没连就走串口通道 |
| `Error: cannot get IPv4 address from interface` | 网卡名传错或该网卡没 IP | `ls /sys/class/net/`、`ip -4 addr show`，手动传对网卡 |
| 烧录后设备起不来 kernel panic | 分区镜像超尺寸、或改了 uboot 忘了 pack_all | 回串口通道全片重刷 |
| 烧录后设备停在 U-Boot 提示符，串口显示 `FIT RSA signature verify failed (SPL key) / Bad Data Hash` | build 重新打包的 `kernel_system_b.image` 内 rootfs sub-image RSA 签名不匹配 U-Boot SPL 固化密钥。内核部分（kernel sub-image）签名通过，但 rootfs（system sub-image）签名无效。常见于多次 build 重建后 | 从 system_a 手动引导恢复：`sf0 probe; sf0 read 0x80a00000 0x290000 0x570000; setenv bootargs ... system=0; bootm 0x80a00000`。或用旧版能启动的 kernel_system_b.image 重新烧录 system_b |
| `Error: project 'xxx' not supported` | gen_tftp_script.py 传了 hm6505 或未列入的项目 | HM6505 用串口通道；其他项目补进 SUPPORTED_PROJECTS 前先确认 mtdparts |
| `cp: cannot create regular file '/usr/bin/adb': Text file busy` | adb daemon 正在运行，文件被占用 | 先 `adb kill-server` 再 `sudo cp` 覆盖 |
| 推送 adbd_report.conf 后 `adb ip-devices` 为空 | adbd 不会自动重读 conf，需重启 adbd 进程 | `adb shell kill -9 $(adb shell pidof adbd)`，等 ~10s init 重拉后心跳上报 |
| `ip-reset-and-wait` 设备名不识别 | 设备名格式不在 simple 模式匹配范围（`hm[0-9]*`/`cam_*`/含`:`） | 确认 adbd_report.conf 中 device_name 与 mai_auto_flash.sh 传入的一致 |
| 烧录后设备回来但 IP 变了 | DHCP 重新分配了新 IP | 这正是 ip-reset-and-wait 的优势：通过心跳自动发现新 IP，无需手动查 |
| **CPSPR 连续多次触发都不进 TFTP** | CPSPR 写成功 + reboot 发出，但设备每次都正常启动旧固件，TFTP server 无请求。连续 3 次都如此。根因不明（可能 U-Boot 版本/编译配置差异导致 CPSPR 检测逻辑不生效） | 连续失败 3 次后停止重试，转串口通道。串口也不通时用 ADB 直写 mtd 分区。验证 CPSPR 是否生效：触发后查 TFTP server 日志，无请求 = 没进 TFTP |
| **`make pack_firmware` 后分区级 auto_update_tftp.txt 变成全量 NOR_ALL.bin 版本** | pack_firmware 从源码 `device/soc/ingenic/pkg_tool/<项目>/auto_update_tftp.txt` 复制覆盖产物目录。如果源码版是全量 NOR_ALL.bin 模式，之前 gen_tftp_script.py 生成的分区级脚本被覆盖 | pack_firmware 之后重新运行 `gen_tftp_script.py ... rootfs system_b` 覆盖回去。或改源码版 auto_update_tftp.txt 为分区级（持久化） |
| 全片烧录首次启动后串口持续刷 `[env]ERROR: crc error in section user / erase error at 0x8000` | factory 分区 56K 与 flash 64KB erase block 不兼容 | 断电重启即可恢复。env 写失败不影响其他子系统 |
| `sudo` 无密码卡住 | 用户 sudo 需要密码 | 配 NOPASSWD 或改为交互式先输密码 |
| 多设备场景 CPSPR 写到了错误设备 | 忘了 `-s <serial>` | 立刻断电对应设备防止破坏；后续所有 adb 命令必须带 serial |
| 分区级烧录看到 `/proc/cmdline` 显示 `system_b: 4141056@0x974200`，偏移不对齐 | 这是**设计意图，不是 bug** —— FIT 内部 rootfs 偏移，内核只读挂载不需要对齐。**不要 fw_setenv 修改**，保持原样就对了。`gen_tftp_script.py` `system_b` 关键字本来就是烧 FIT 整块到 0x800000，完全匹配设计 |
| 串口日志刷屏看不到回显 | 进程由 init 监管，`killall` 后立刻被拉起 | 用 python 读取后过滤噪点：排除所有含 `IndHandle/MikeInit/IPCMain/MI IPC/StatReport/...` 等关键字行，只保留命令输出 |
| `ip-reset-and-wait` 找到设备但 ADB 状态为 `offline` | 烧录后重启，adbd 与主机 ADB 密钥协商异常（rootfs 刷新后密钥不一致） | ① `adb kill-server` ② `adb connect <IP>:5555` 重试。如果仍 offline，串口登录后 `killall -9 adbd` 让 init 重拉 adbd，等 ~5s 再 `adb connect`。重拉后约 10s 设备恢复 |

## ADB 直写 mtd 分区的关键陷阱（最后手段通道）

| 陷阱 | 后果 | 正确做法 |
|------|------|---------|
| **先 flash_eraseall 再犹豫** | 分区已擦除但没写入，设备重启即 kernel panic 变砖 | 擦除前确认镜像已 push 且 MD5 校验通过，擦写一步到位不中断 |
| **用 `cat` 代替 `dd` 写 /dev/mtd** | cat 写 NOR flash 不可靠，MD5 校验不匹配（实测：cat 写入后读回 MD5 与源不一致） | **必须用 `dd if=<file> of=/dev/mtdN bs=4096`**，不能用 cat 重定向 |
| **不验证直接重启** | 写入可能不完整，重启后 kernel panic | 写入后必须读回 MD5 校验，确认与源文件一致再重启 |
| **flashcp applet 不存在** | `which flashcp` 找到路径但执行报 `applet not found`（busybox 符号链接但无此 applet） | 用 `flash_eraseall` + `dd` 组合替代 flashcp |
| **设备无 head/sort/cut 等 applet** | 验证命令管道失败 | 用 `dd ... | md5sum` 或 `adb shell cat /dev/mtdN > /tmp/dump` 在主机端验证 |

### auto_update_tftp.txt 被 pack_firmware 覆盖

`make pack_firmware` 会从源码 `device/soc/ingenic/pkg_tool/<项目>/auto_update_tftp.txt` 复制到产物目录，**覆盖**之前用 `gen_tftp_script.py` 生成的分区级脚本。

如果需要分区级烧录（rootfs + system_b），必须在 `make pack_firmware` **之后**重新运行 `gen_tftp_script.py`，否则 TFTP 烧录会用全量 NOR_ALL.bin 脚本（擦 env 分区，导致 ADB 配置丢失）。

```bash
# 正确顺序
make pack_firmware                          # 先打包（会用源码 auto_update_tftp.txt 覆盖）
python3 gen_tftp_script.py ... rootfs system_b  # 再生成分区级脚本覆盖回去
```

## 决策原因（为什么这样）

### CPSPR 触发不稳定（历史实测分析）

- 实测中 CPSPR 写成功 + reboot 发送成功，但设备可能直接进了 U-Boot 提示符而非 TFTP 模式。根因不确定（可能 U-Boot 版本差异）。
- 2026-07-16 实测：CPSPR 触发 3 次都成功写了寄存器 + 发了 reboot，但每次设备都正常启动到 Linux（旧固件），从未进入 TFTP 模式。TFTP server 日志无任何请求记录。**CPSPR 失败时设备不会卡死，而是正常启动旧系统**，所以可以用 `adb devices` + 扫描 DHCP 段确认设备回来了，然后重试。但连续失败 3 次以上时应转串口通道，不要无限重试。
- 最终可靠方案：CPSPR 触发后立即接串口监控 boot 输出。5s 内没有 TFTP 下载活动 -> 串口介入手动配 IP + `mai_tftp`。
- 串口不通时的困境：如果串口物理层不通（设备 echo 到 ttyS1 但主机 /dev/ttyUSB0 收到 0 bytes），CPSPR 又失败，则 TFTP 烧录完全无法进行。此时只能：①修复串口线 ②或用 ADB+flash_eraseall+dd 方式直接写 mtd 分区（见 SKILL.md「ADB 直写 mtd 分区」章节）。

### 为什么需要固定 MAC

随机 MAC 会导致 DHCP IP 池快速耗尽，设备无法获取 IP。
通过 `user_env` 将固定 MAC 写入设备的 env 分区，U-Boot 烧录模式和 Linux 启动时
都会使用这个 MAC 进行 DHCP，避免 IP 池浪费。

### `/proc/cmdline` 的 system_b 偏移是设计意图

FIT 模式设备运行时 `/proc/cmdline` 会动态显示 system_b 的不同偏移（如 `4141056@0x974200(system_b)`）。
这是 U-Boot bootm 时**运行时动态改写的产物**，不是 flash 分区表。**不要按 CMDLINE 的偏移烧录，也不要 fw_setenv 修改。**
分区级烧录必须按 `PRJ.h` 的 `BOOTARGS_SFCNOR_PARTITION` 编译期定义。详见 `fit-mtdparts-rewrite.md`。
