# adb-tftp-skill

Ingenic T32 家族 NOR flash 设备的 **ADB 通道 TFTP 烧录** skill（Hermes / Claude Code / Codex / ZCode 通用）。

## 这是什么

设备 ADB 在线时，通过 ADB 写 CPSPR 寄存器触发 U-Boot 进入 TFTP 模式，实现**分区级烧录**（rootfs + system_b），比串口通道更快更静，且支持只烧单个分区。

适用项目（NOR flash + 共享 mtdparts）：**<项目E> / <项目A> / <项目A>_b01 / <项目B> / <项目D>**
不适用：<项目C>（NAND 平台，走串口通道）

## 一键安装

```bash
# Hermes / Claude Code / Codex 全装（交互选择目标）
curl -fsSL https://gitee.com/GreatBigM/adb-tftp-skill/raw/main/install.sh -o /tmp/install.sh && bash /tmp/install.sh

# 指定目标
curl -fsSL https://gitee.com/GreatBigM/adb-tftp-skill/raw/main/install.sh | bash -s -- --target hermes,claude,zcode

# 全部目标（含 ZCode）
curl -fsSL https://gitee.com/GreatBigM/adb-tftp-skill/raw/main/install.sh | bash -s -- --all
```

等价于手动复制，不经过安全扫描。重复执行 = 更新（自动备份旧版 + 版本对比）。

海外备选镜像：`https://github.com/GreatBigM/adb-tftp-skill`

### 手动复制（备选）

```bash
git clone --depth 1 https://gitee.com/GreatBigM/adb-tftp-skill.git /tmp/adb-tftp-skill
mkdir -p ~/.hermes/skills/adb-tftp && cp -r /tmp/adb-tftp-skill/{SKILL.md,CHANGELOG.md,scripts,references} ~/.hermes/skills/adb-tftp/   # Hermes
mkdir -p ~/.claude/skills/adb-tftp && cp -r /tmp/adb-tftp-skill/{SKILL.md,CHANGELOG.md,scripts,references} ~/.claude/skills/adb-tftp/    # Claude Code
mkdir -p ~/.codex/skills/adb-tftp  && cp -r /tmp/adb-tftp-skill/{SKILL.md,CHANGELOG.md,scripts,references} ~/.codex/skills/adb-tftp/     # Codex
mkdir -p ~/.zcode/skills/adb-tftp  && cp -r /tmp/adb-tftp-skill/{SKILL.md,CHANGELOG.md,scripts,references} ~/.zcode/skills/adb-tftp/     # ZCode
```

> 只拷这四项（与 `install.sh` 的拷贝清单一致）：整仓 `cp -r` 会把 `.git` / `README.md` / `install.sh` / `LICENSE` 一起塞进 skills 目录。

> 注意：`hermes skills install` 会被安全扫描拦截（skill 涉及 `devmem`/`reboot`/`sudo` 等命令触发 dangerous 误报），一键脚本/手动复制是合规替代路径。

## 快速开始（AI 替你执行）

用户只需说"给 <项目> 烧录 rootfs + system_b"，AI 按 skill 流程执行：

```bash
cd <项目根>
# 1. 起 TFTP server
sudo pkill in.tftpd 2>/dev/null || true
sudo /usr/sbin/in.tftpd -l -s out/image_<项目>
# 2. 生成分区烧录脚本
python3 <skill>/scripts/gen_tftp_script.py --project <项目> --output-dir out/image_<项目> rootfs system_b
# 3. 触发烧录（IP 编码模式，编码主机 IP 到 CPSPR）
bash <skill>/scripts/mai_auto_flash.sh enp2s0 <设备IP>:5555
# 4. 等设备回连（定制 adb）或轮询/串口恢复
adb ip-reset-and-wait <设备名>
```

> ⚠️ **必须用 IP 编码模式**（`mai_auto_flash.sh <NIC> <serial>`）。simple 模式（单参数）固定 CPSPR 0x00000909，U-Boot 解析 server IP 错误 → TFTP T T T T 失败（2026-08-04 实测）。

## 前置准备（一次性）

1. **定制 adb**（支持 `ip-reset-and-wait`）：编译项目内 `third_party/android_port` → 覆盖 `/usr/bin/adb`
2. **设备 adbd_report.conf + 固定 MAC**：`gen_adbd_conf_noninteractive.sh` 一键生成 → 推送 + `user_env` 配置
3. **TFTP server**：`tftpd-hpa` 装二进制但 disable systemd 服务（避免抢 69 端口）

## 目录结构

```
adb-tftp-skill/
├── SKILL.md                     ← 主文档（含完整流程/分区表/反模式/故障排查）
├── install.sh                   ← 一键安装/更新（多 agent 目标）
├── CHANGELOG.md                 ← 版本历史
├── scripts/
│   ├── gen_tftp_script.py       ← 生成分区级 auto_update_tftp.txt
│   ├── mai_auto_flash.sh        ← CPSPR 触发烧录（IP 编码模式）
│   ├── gen_adbd_conf_noninteractive.sh  ← 生成 adbd_report.conf + 固定 MAC
│   ├── serial-login-ip-adbd.py  ← ADB 连不上时的串口兜底登录
│   └── serial-base64-push.py    ← 无网络时串口 base64 推文件
└── references/
    ├── partition-table-evidence.md   ← NOR 分区表证据链
    ├── fit-mtdparts-rewrite.md       ← FIT mtdparts 动态改写机制
    ├── fit-rsa-signature-issue.md    ← FIT RSA 签名失败分析
    ├── env-nor-full-flash-loop.md    ← env_nor 全片烧录循环问题
    ├── ingenic-adb-connect.md        ← Ingenic 平台：串口盲打 → 查 IP → ADB 连接
    ├── adb-recovery.md               ← ADB「device 但命令失败」恢复（HTTP wget / base64 推）
    └── troubleshooting.md            ← 坑 / 反模式 / 排障速查
```

## 相关资源

- 串口通道（设备离线/ADB 挂死时兜底）：`serial-tftp`（serial-tftp-skill 仓库）
- 分区表权威源：`device/soc/ingenic/uboot/t32_t33/include/configs/PRJ.h` 的 `BOOTARGS_SFCNOR_PARTITION`
