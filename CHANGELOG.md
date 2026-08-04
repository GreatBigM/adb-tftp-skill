# CHANGELOG

本文件记录版本历史。版本号定义在 SKILL.md frontmatter 的 `version` 字段（单一真相源）。

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
