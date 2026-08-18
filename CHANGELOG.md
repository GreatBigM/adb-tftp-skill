# CHANGELOG

本文件记录版本历史。版本号定义在 SKILL.md frontmatter 的 `version` 字段（单一真相源）。

## 1.3.0 (2026-08-18)

### Fixed（审查修复）

- **description 精简至 100 字内**：去掉「HM6505 NAND 除外」（市场卡片 ≤100 字规格）
- **死链改引**：交叉引用 `ingenic-basic-tftp-flash`（不存在的技能）→ `serial-tftp`（现串口通道技能）
- 版本 1.2.0 → 1.3.0

## 1.2.0 (2026-08-18)

### Added

- **ZCode 安装目标**：`install.sh` 支持 ZCode（探测 `~/.zcode` → 安装到 `~/.zcode/skills/adb-tftp`），README 补 `--target zcode` 示例与手动复制路径，发布页一键命令即可装到 ZCode

### Fixed

- **默认分支统一 main**：仓库分支由 `master` 改为 `main` 并推送双远端（此前发布页 `raw/main/install.sh` 404，一键命令失效）

### Changed

- 随 1.2.0 一并推送此前未推送的 description 精简提交（市场卡片 ≤100 字规格）

## 1.1.0 (2026-08-04)

### Changed

- **A 模式分层（构成审查修复）**：坑 / 反模式 / 排障速查 / 决策原因全量从 SKILL.md 迁入 `references/troubleshooting.md`，SKILL.md 瘦身 561→485 行，只留干净主流程（对齐 gen/review v1.4.0 A 模式，与 serial-tftp v1.5.0 同构）
- **删除主题越界文件** `references/mips-ftrace-config.md`：内核 ftrace 配置主题与烧录无关，归属 `kernel-tracing-ftrace-config` skill（该处已有更完整分析，无独有内容）
- 顶部「关键陷阱」行收窄为「安全前置提醒」并指向 troubleshooting.md

### 审查来源

2026-08-04 构成审查（hermes-skill-review v1.4.0）P1×2：A 模式分层违反 / 定位分歧文件；P2×3（commit 标签 v1.0.1、安装目录带 .git、.gitignore 缺失）中后两项本次一并处理。

## 1.0.0 (2026-08-04)

### Added（首发）

- **ADB 通道 TFTP 烧录全流程**：CPSPR 触发 → U-Boot TFTP 模式 → 分区级烧录（rootfs/system_b/single 分区）→ ip-reset-and-wait 自动回连
- **一次性 prepare 流程**：编译定制 adb（ip-reset-and-wait）+ gen_adbd_conf（adbd_report.conf + 确定性固定 MAC）+ user_env 配置
- **三个脚本**：
  - `gen_tftp_script.py` — 生成分区级 auto_update_tftp.txt（PARTITIONS 表单一真相源，ALL_ERASE_SIZE 自动跟随）
  - `mai_auto_flash.sh` — CPSPR 触发（simple / IP 编码双模式）
  - `gen_adbd_conf_noninteractive.sh` — 一键生成 adbd_report.conf + 固定 MAC
- **五个 references**：分区表证据链 / FIT mtdparts 改写 / FIT RSA 签名 / MIPS ftrace / env_nor 循环
- **完整反模式 + 故障排查表**：CPSPR 连续失败转串口、DHCP 换 IP、pack_firmware 覆盖、ADB 直写 mtd 兜底等

### 要点

- 适用 HM6801/HM6502/HM6502_B01/HM6503/HM6402（NOR 家族共享 mtdparts）；HM6505（NAND）明确拒绝
- IP 编码模式 CPSPR `0xXXYY0909` 实测首试即触发；simple 模式固定 0x00000909 有 serverip 解析风险（1.1.0 关注）
