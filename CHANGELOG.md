# Changelog
## 1.4.3 (2026-10-14)

### Fixed（install.sh 两处 + 发布闸门，与 qwiki-skill 同款）

- **`--target hermes,claude`（空格形式）从未生效**：解析只认 `--target=`，空格形式把值吞成空串后落进"非交互 = 装全部"分支——而 README / 用法行 / 脚本头部**三处文档全写的空格形式**。现两种形式都支持，且 `--target` 缺参数时直接报错退出（不再静默装全部）。
- **备份落在 skills 扫描根之内**：旧版备份写成 `<skills>/<name>.bak.<时间戳>`，而 agent 按「含 SKILL.md 的目录」发现技能、不看目录名 ⇒ 备份被当成**第二个同名技能**加载（重名歧义下静默跳过其一）。现备份落 `<tool 根>/skills-backup/`（扫描根之外），README 与脚本尾注同步。
- **挂上 pre-push 闸门（脱敏 + CHANGELOG 同步）**：`scripts/publish-check.py`（扫项目代号 / 内网 IP / MAC / 长 hash / 凭据 / 本机路径，自带 `--self-test`）+ `scripts/hooks/pre-push`；启用一次 `git config core.hooksPath scripts/hooks`。理由与脱敏规则同源：**靠人记必然回潮**，检查要做成"推送时自动拦"而不是"记得手动跑"。CHANGELOG 闸门名单 = SKILL.md / install.sh / scripts/ / references/。
- **脱敏：全量清理项目代号 / 内网 IP / MAC / 内网路径**（闸门首扫命中后执行）——正文、references、脚本注释与默认值一并处理：项目代号 → `<项目A>`…`<项目F>`（**大小写不敏感**，大写写法一并换）；IP / MAC → `<IP-n>` / `<MAC-n>`（**文件内编号唯一**，保住句内多机对比关系）；`/mnt/data/` → `<代码树>/`，本机家目录 → `<用户目录>/`；**脚本里的功能性默认值改为环境变量**（`TFTP_PROJECTS` / `DEVICE_IP` / `TFTP_GATEWAY`，未给时报错或显式跳过，不再写死内网值）；9 个文件名含代号的 references 改名（`hm6502-* → projA-*`、`hm6801-* → projE-*`），SKILL.md 引用清单同步。历史不回改（已公开的收不回，force push 也不行），本次只保证往后版本不再含。
- 版本 1.4.2 → 1.4.3

# CHANGELOG
## 1.4.2 (2026-09-28)

### Changed

- 回灌本机 Hermes 副本的实测修正：分区权威源更正为项目 `partitions.conf`（09-12）+ `gen_tftp_script.py` 烧录门禁与 CLI 更新 + CPSPR 5.15 根因闭环（reset.c 覆写 CPSPR）
- 版本 1.4.1 → 1.4.2


本文件记录版本历史。版本号定义在 SKILL.md frontmatter 的 `version` 字段（单一真相源）。

## 1.3.0 (2026-08-18)

### Fixed（审查修复）

- **description 精简至 100 字内**：去掉「<项目C> NAND 除外」（市场卡片 ≤100 字规格）
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

- 适用 <项目E>/<项目A>/<项目A>_b01/<项目B>/<项目D>（NOR 家族共享 mtdparts）；<项目C>（NAND）明确拒绝
- IP 编码模式 CPSPR `0xXXYY0909` 实测首试即触发；simple 模式固定 0x00000909 有 serverip 解析风险（1.1.0 关注）

## 1.4.0 (2026-08-28)

### Added（并入 adb-debug）

- 新增「ADB 调试（非烧录场景）」章节：连接建立、故障速查、断线恢复兜底通道、Ingenic 平台流程
- 并入 adb-debug 的脚本 serial-login-ip-adbd.py / serial-base64-push.py 与 2 个 references
- description 更新为「ADB 通道：TFTP 烧录 + ADB 调试」；triggers 补 ADB 调试类
- 版本 1.3.0 → 1.4.0

## 1.4.1 (2026-08-28)

### Added

- install.sh 新增 pi 安装目标（探测 `~/.pi/agent` → 安装到 `~/.pi/agent/skills/<skill>`，pi 自动发现）
- 版本 1.4.0 → 1.4.1
