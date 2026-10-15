# Changelog

本文件记录版本历史。版本号定义在 SKILL.md frontmatter 的 `version` 字段（单一真相源）。

## 1.4.5 (2026-10-15)

### Fixed

- **发布闸门残留清零（本仓）**：历史条目里的真实代号写法改掩码（`HM####` / `BW####` / `hm####`）、内网代码树路径改为文字描述（保留事实，不删条目）；`references/` 里残留的厂商名、代号前缀残缺形态、人名来源注释、裸数字代号签名（含脚本补全里的旧脚本别名）一并泛化或移除。闸门口径见 `scripts/publish-check.py` 文件头，本机私用真名名单在未跟踪的 `scripts/publish-deny.local`。
- **交叉引用死链修复**：`references/ingenic-adb-connect.md` 6 处指向已并入他处的技能（`serial-debug`）的引用，改为指向串口通道兄弟 skill 的 `references/serial-debug-diagnostics.md`，或本 skill 自己的 `references/adb-recovery.md`；`references/adb-recovery.md` 的自我定位从已并入本 skill 的旧技能名改回本 skill；删掉指向未发布本机技能的整行。
- **`install.sh` 安装完成提示指向本仓不存在的脚本**（该脚本属串口通道仓）→ 改为本仓真实入口 `scripts/mai_auto_flash.sh`。
- **CHANGELOG 结构三项修复**：删除第二个 H1；把误排在 1.0.0 之后的 1.4.1 / 1.4.0 条目归位到 1.4.2 之后（恢复严格降序）；夹在条目之间的说明行移到文首。（1.0.0 条目里记的「五个 references」是当时的快照，不回改。）

### Changed

- **README 目录结构块与手动复制清单对齐实际仓库**：删掉 1.1.0 已删除的文件行；补全 3 个 references 与 2 个 scripts；手动复制改为只取 `SKILL.md` / `CHANGELOG.md` / `scripts` / `references`（与 `install.sh` 一致，不再整仓 `cp -r` 把 `.git` / `README.md` / `install.sh` / `LICENSE` 一起拷进 skills 目录）。
- **`references/` 旧布局数值更正收尾**：此前未提交的一批改动（FIT mtdparts / 擦除范围 / `sf0 read` 尺寸等示例数值更正为当前布局，并加「示例为旧布局、实际以项目 `partitions.conf` 为准」的顶部提示）随本版一并发布。
- **frontmatter 补 `author` / `license` 字段**（本仓含 MIT LICENSE 文件，文字口径与文件对齐）。
- 版本 1.4.4 → 1.4.5

## 1.4.4 (2026-10-15)

### Fixed
- **发布闸门 publish-check.py 三个洞同批修**（脱敏反复回潮的根因之一：闸门对真实标识零防护却一直报「干净」）：
  ① 代号正则大小写不敏感（旧版只认小写，`HM####` / `BW####` 整体漏）；
  ② 白名单改为**按匹配项豁免**（旧版 `if any(a in line for a in ALLOW): continue` 是整行豁免——一行里出现
  `<项目A>` 就给同行的真名背书；且原 7 个词对 12 条 pattern 全部零命中 = 纯死豁免）；
  ③ 词边界改用显式字符类（`\b` 在 str 模式下 `\w` 含汉字 ⇒「项目hm####」这类中文常见写法漏检，
  加不加空格决定报不报）。另补 PRJ0## / 裸数字代号 / MAC 连字符 / 凭据变体（`token=`、`Bearer`、中文「密码」后接全角冒号）/
  邮箱 六类形态。
- **`--self-test` 样本按已知缺陷类别扩容**（原 15 条只覆盖「正常裸值」一档，上述六类一条样本都没有）；
  自检与扫描共用同一份判定口径（`line_hits`），不再各写一套造成假绿。
- **`scripts/hooks/pre-push` 在推送路径上先跑 `--self-test`**（规则表被改坏时不得静默通过）；
  CHANGELOG 名单统一为超集（SKILL / SCHEMA / install.sh / templates / references / scripts，9 仓文本自此一致）；
  基点改为 `origin/main → gitee/main → 根提交` 三级回落（旧版无 `origin/main` 时回落到 `HEAD~1`，
  多笔提交一起推会只看最后一笔）。
- **新增本机私用名单 `scripts/publish-deny.local`**（gitignore、不进仓）：人名 / 昵称 / 厂商 SDK 名 /
  内部 skill 名这类**无法正则枚举、也不该写进发布仓**的标识，在本机未跟踪文件里逐行列真名，闸门自动一并扫。

### 说明
- 口径全文见 `scripts/publish-check.py` 文件头（已知边界：长 hash 折行、全角句点 IP 不识别；该文件自身在
  `SKIP_FILES` 内，改它时需人工核对）。9 仓共用同一份闸门（md5 一致）——改一处必须批量同步。
- 版本 1.4.3 → 1.4.4

## 1.4.3 (2026-10-14)

### Fixed（install.sh 两处 + 发布闸门，与 qwiki-skill 同款）

- **`--target hermes,claude`（空格形式）从未生效**：解析只认 `--target=`，空格形式把值吞成空串后落进"非交互 = 装全部"分支——而 README / 用法行 / 脚本头部**三处文档全写的空格形式**。现两种形式都支持，且 `--target` 缺参数时直接报错退出（不再静默装全部）。
- **备份落在 skills 扫描根之内**：旧版备份写成 `<skills>/<name>.bak.<时间戳>`，而 agent 按「含 SKILL.md 的目录」发现技能、不看目录名 ⇒ 备份被当成**第二个同名技能**加载（重名歧义下静默跳过其一）。现备份落 `<tool 根>/skills-backup/`（扫描根之外），README 与脚本尾注同步。
- **挂上 pre-push 闸门（脱敏 + CHANGELOG 同步）**：`scripts/publish-check.py`（扫项目代号 / 内网 IP / MAC / 长 hash / 凭据 / 本机路径，自带 `--self-test`）+ `scripts/hooks/pre-push`；启用一次 `git config core.hooksPath scripts/hooks`。理由与脱敏规则同源：**靠人记必然回潮**，检查要做成"推送时自动拦"而不是"记得手动跑"。CHANGELOG 闸门名单 = SKILL.md / install.sh / scripts/ / references/。
- **脱敏：全量清理项目代号 / 内网 IP / MAC / 内网路径**（闸门首扫命中后执行）——正文、references、脚本注释与默认值一并处理：项目代号 → `<项目A>`…`<项目F>`（**大小写不敏感**，大写写法一并换）；IP / MAC → `<IP-n>` / `<MAC-n>`（**文件内编号唯一**，保住句内多机对比关系）；项目代码树路径 → `<代码树>/`，本机家目录 → `<用户目录>/`；**脚本里的功能性默认值改为环境变量**（`TFTP_PROJECTS` / `DEVICE_IP` / `TFTP_GATEWAY`，未给时报错或显式跳过，不再写死内网值）；9 个文件名含代号的 references 改名（`hm####-* → projA-*`、`hm####-* → projE-*`），SKILL.md 引用清单同步。历史不回改（已公开的收不回，force push 也不行），本次只保证往后版本不再含。
- 版本 1.4.2 → 1.4.3

## 1.4.2 (2026-09-28)

### Changed

- 回灌本机 Hermes 副本的实测修正：分区权威源更正为项目 `partitions.conf`（09-12）+ `gen_tftp_script.py` 烧录门禁与 CLI 更新 + CPSPR 5.15 根因闭环（reset.c 覆写 CPSPR）
- 版本 1.4.1 → 1.4.2

## 1.4.1 (2026-08-28)

### Added

- install.sh 新增 pi 安装目标（探测 `~/.pi/agent` → 安装到 `~/.pi/agent/skills/<skill>`，pi 自动发现）
- 版本 1.4.0 → 1.4.1

## 1.4.0 (2026-08-28)

### Added（并入 adb-debug）

- 新增「ADB 调试（非烧录场景）」章节：连接建立、故障速查、断线恢复兜底通道、Ingenic 平台流程
- 并入 adb-debug 的脚本 serial-login-ip-adbd.py / serial-base64-push.py 与 2 个 references
- description 更新为「ADB 通道：TFTP 烧录 + ADB 调试」；triggers 补 ADB 调试类
- 版本 1.3.0 → 1.4.0

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
