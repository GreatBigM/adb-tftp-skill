#!/usr/bin/env python3
"""Generate U-Boot tftp update script for Ingenic T32 family NOR flash projects.

Supported projects (共用同一份 mtdparts, source: uboot/t32_t33/include/configs/PRJ.h)：
    HM6801 / HM6502 / HM6502_B01 / HM6503 / HM6402

NOT supported (partition table differs)：
    HM6505  ← NAND flash, 用 device/soc/ingenic/pkg_tool/hm6505/auto_update_tftp.txt

Usage:
    gen_tftp_script.py [--project <name>] [--output-dir <dir>] <partition>...
    gen_tftp_script.py [--project <name>] [--output-dir <dir>] all      # 擦到 algo 末尾，保留 factory/env/log
    gen_tftp_script.py [--project <name>] [--output-dir <dir>] full     # 真全片：16MB 整颗擦写（含参数区）

Partitions (NOR family, from PRJ.h BOOTARGS_SFCNOR_PARTITION @ CONFIG_FIT):
    uboot       U-Boot bootloader          (0x000000, 256KB)
    rootfs      Root filesystem             (0x040000, 2.5MB, 2368K)
    system_a    Kernel + system A (factory) (0x290000, 5.7MB, 5568K)  [FIT: dtb+kernel+squashfs]
    system_b    Kernel + system B (user)    (0x800000, 5.7MB, 5568K)  [FIT: dtb+kernel+squashfs]

    ⚠️ system_a/system_b 分区烧的是 FIT image (kernel_system_x.image, 整块 5824K).
       FIT 内 embedded squashfs 通过 kernel CMDLINE 里的 `4141056@0x974200`
       (取决于项目) 就地映射为 mtd3 只读挂载. 这个未 sector 对齐的偏移是 rootfs
       零拷贝启动的设计, 不是 bug——不要试图按 CMDLINE 语义直接烧 system_b.img
       到 0x974200 (擦写会因未对齐失败). 用本脚本 `system_b` 即为烧整块 FIT.
    algo       AI algorithm models         (0xDF0000, 1.0MB, 1024K)
    factory     Factory calibration         (0xEF0000, 56KB)
    env_a       Env A                       (0xEFE000, 4KB)
    env_b       Env B                       (0xEFF000, 4KB)
    log         Log partition (jffs2)       (0xF00000, 1MB)

Notes:
    - --project only affects the NOR_ALL.bin filename when 'all' is used;
      partition offsets are identical across the family.
    - Default output-dir file: <dir>/auto_update_tftp.txt
    - Compatible with old flag name: still accepts symlink invocation as gen_tftp_script_6801.py.
"""

# ⚠️⚠️ 分区表过时警告（2026-09-12 反思 cron 加，勿删）════════════════════════════
# 本文件 PARTITIONS 表最后同步 = 2026-07-18，**已与当前布局不一致**（勿直接用于 hm6502* 分区级烧录）。
#
# 唯一真相源 = <项目>/test/factory_test/PackAllBin/partition_layout/partitions.conf
#   段 1 [hm6502 hm6503 hm6402 hm6801 hm6802]（2026-09-07 起）：
#     boot 0x000000/256K, rootfs 0x040000/2368K, sysA 0x290000/6080K,
#     sysB 0x880000/6080K, algo 0xE70000/1024K, factory 0xF70000/56K,
#     env_a 0xF7E000/4K, env_b 0xF7F000/4K, log 0xF80000/512K
#     → 擦除上限 ALL_ERASE_SIZE = 0xF70000
#   段 2 [hm6502_b01]：sysA 0x270000/5888K, sysB 0x830000/5888K, algo 0xDF0000/1536K
#     → 单一硬编码表天然无法表达两个段，这是「必须改为读 conf」的根本原因
#
# 正确用法：`python3 partition_layout.py apply-flash <product> --write`
#   （自动跟随 conf 生成 auto_update_tftp.txt；pack_all.sh 内亦先跑 check）
# 待办（需人工/编码任务）：把 PARTITIONS 改为解析 partitions.conf，彻底消除第二真相源。
# ═══════════════════════════════════════════════════════════════════════════════

import sys
import os
import argparse

LOAD_ADDR = "0x80600000"

# Partition table shared by HM6801/HM6502/HM6502_B01/HM6503/HM6402
# Source: device/soc/ingenic/uboot/t32_t33/include/configs/PRJ.h  (BOOTARGS_SFCNOR_PARTITION, FIT branch)
#   sfc0_nor:256k(boot),2368k(rootfs),5824k@0x290000(kernel_system_a),
#            5824k@0x840000(kernel_system_b),1024k@0xDF0000(algo),
#            56k(factory),4k(env_a),4k(env_b),1024k(log)
# Updated 2026-07-17: sysB 5568k→6080k, algo 1536k→1024k@0xDF0000 (commit c1f3552)
# Updated 2026-07-18: A/B 对称——redistribution 已借的 512k 均分 256/256，
#                    sysA 5568k→5824k、sysB 6080k→5824k 且 offset 0x800000→0x840000
#                    (openspec change hm6502-partition-ab-symmetric)。algo/log 不变。
PARTITIONS = {
    "uboot":    {"offset": 0x000000, "size": 0x040000, "file": "u-boot-with-spl.bin"},
    "rootfs":   {"offset": 0x040000, "size": 0x250000, "file": "rootfs.img"},
    "system_a": {"offset": 0x290000, "size": 0x570000, "file": "kernel_system_a.image"},
    "system_b": {"offset": 0x800000, "size": 0x570000, "file": "kernel_system_b.image"},
    "algo":     {"offset": 0xD70000, "size": 0x180000, "file": "algo.img"},
    "factory":  {"offset": 0xEF0000, "size": 0x00E000, "file": None},
    "env_a":    {"offset": 0xEFE000, "size": 0x001000, "file": "env.bin"},
    "env_b":    {"offset": 0xEFF000, "size": 0x001000, "file": "env.bin"},
    "log":      {"offset": 0xF00000, "size": 0x100000, "file": None},
    # Legacy alias: some flows treated env_a as "env"
    "env":      {"offset": 0xEFE000, "size": 0x001000, "file": "env.bin"},
    # Legacy alias: some flows referred to log as "data" (userdata-like)
    "data":     {"offset": 0xF00000, "size": 0x100000, "file": None},
}

# All-in-one image erase size: 从分区表推导 (algo 末尾 = factory/env/log 起点),
# 改分区表时自动跟随，避免硬编码漏同步。= PARTITIONS["algo"].offset + .size
ALL_ERASE_SIZE = PARTITIONS["algo"]["offset"] + PARTITIONS["algo"]["size"]

# 整颗 NOR 容量：同样从分区表推导（log 末尾），不硬编码 16MB。
# 用于 `full` 模式——真全片擦写，连 factory/env/log 参数区一起抹。
NOR_TOTAL_SIZE = PARTITIONS["log"]["offset"] + PARTITIONS["log"]["size"]

SUPPORTED_PROJECTS = ["hm6801", "hm6502", "hm6502_b01", "hm6503", "hm6402"]

PARTITION_ORDER = ["full", "uboot", "rootfs", "system_a", "system_b", "algo",
                   "factory", "env_a", "env_b", "log", "env", "data"]

BASH_COMPLETION = r'''
_gen_tftp_script() {
    local cur opts
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    opts="all full uboot rootfs system_a system_b algo factory env_a env_b log env data"
    COMPREPLY=( $(compgen -W "${opts}" -- "${cur}") )
    return 0
}
complete -F _gen_tftp_script gen_tftp_script.py
complete -F _gen_tftp_script ./gen_tftp_script.py
complete -F _gen_tftp_script gen_tftp_script_6801.py
'''

ZSH_COMPLETION = r'''
_gen_tftp_script() {
    local -a opts
    opts=(all full uboot rootfs system_a system_b algo factory env_a env_b log env data)
    _describe 'partition' opts
}
compdef _gen_tftp_script gen_tftp_script.py
compdef _gen_tftp_script ./gen_tftp_script.py
compdef _gen_tftp_script gen_tftp_script_6801.py
'''


def print_completion(shell):
    if shell == "bash":
        print(BASH_COMPLETION.strip())
    elif shell == "zsh":
        print(ZSH_COMPLETION.strip())
    else:
        print(f"Error: unsupported shell '{shell}', use 'bash' or 'zsh'")
        sys.exit(1)
    sys.exit(0)


def usage():
    print(__doc__.strip())
    sys.exit(1)


def gen_all(project):
    all_bin = f"{project}_NOR_ALL.bin"
    lines = []
    lines.append("# <- this is for comment / total file size must be less than 4KB")
    lines.append(f"tftpboot {LOAD_ADDR} {all_bin}")
    lines.append("")
    lines.append("sf probe")
    lines.append(f"sf erase 0x0 0x{ALL_ERASE_SIZE:x}")
    lines.append(f"sf write {LOAD_ADDR} 0x0 0x{ALL_ERASE_SIZE:x}")
    lines.append("")
    lines.append("reset")
    lines.append("% <- this is end of file symbol")
    return lines


def gen_full(project, output_dir=None):
    """真·全片烧录：擦除整颗 NOR（含 factory / env_a / env_b / log 参数区）并回写完整 NOR_ALL.bin。

    与 all 的区别：all 的擦除上限是 ALL_ERASE_SIZE（algo 末尾 = 0xEF0000），**保留**
    factory/env/log；full 擦写 NOR_TOTAL_SIZE（16MB 整颗），参数区一并抹掉。

    ⚠️ 后果：factory 内的 RF 校准数据、env（boot 槽选择/adbd 上报配置）、log 均丢失，
       烧后需重做产测校准并重配 env。仅在明确要求“全擦”时使用。
    """
    all_bin = f"{project}_NOR_ALL.bin"
    if output_dir:
        path = os.path.join(output_dir, all_bin)
        if os.path.isfile(path):
            real = os.path.getsize(path)
            if real != NOR_TOTAL_SIZE:
                print(f"Error: {all_bin} is {real} bytes but NOR total is {NOR_TOTAL_SIZE} — "
                      f"全片擦写长度与镜像不符，拒烧（防烧坏）", file=sys.stderr)
                sys.exit(1)
    lines = []
    lines.append("# <- this is for comment / total file size must be less than 4KB")
    lines.append("# FULL-CHIP: erases factory/env/log too — calibration data WILL be lost")
    lines.append(f"tftpboot {LOAD_ADDR} {all_bin}")
    lines.append("")
    lines.append("sf probe")
    lines.append(f"sf erase 0x0 0x{NOR_TOTAL_SIZE:x}")
    lines.append(f"sf write {LOAD_ADDR} 0x0 0x{NOR_TOTAL_SIZE:x}")
    lines.append("")
    lines.append("reset")
    lines.append("% <- this is end of file symbol")
    return lines


def gen_partitions(parts):
    lines = []
    lines.append("# <- this is for comment / total file size must be less than 4KB")

    sorted_parts = sorted(parts, key=lambda p: PARTITION_ORDER.index(p))

    for part in sorted_parts:
        info = PARTITIONS[part]
        if info["file"]:
            lines.append(f"tftpboot {LOAD_ADDR} {info['file']}")
            lines.append("")
            lines.append("sf probe")
            lines.append(f"sf erase 0x{info['offset']:x} 0x{info['size']:x}")
            lines.append(f"sf write {LOAD_ADDR} 0x{info['offset']:x} 0x{info['size']:x}")
        else:
            lines.append("sf probe")
            lines.append(f"sf erase 0x{info['offset']:x} 0x{info['size']:x}")
        lines.append("")

    lines.append("reset")
    lines.append("% <- this is end of file symbol")
    return lines


def detect_project(output_dir):
    """Try to auto-detect project name from output_dir path, e.g. out/image_hm6502 -> hm6502."""
    if not output_dir:
        return None
    base = os.path.basename(os.path.abspath(output_dir)).lower()
    # match 'image_<project>' or trailing project name
    for proj in SUPPORTED_PROJECTS:
        if proj in base:
            return proj
    return None


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        usage()

    if sys.argv[1] == "--completion":
        if len(sys.argv) < 3:
            print("Usage: gen_tftp_script.py --completion bash|zsh")
            sys.exit(1)
        print_completion(sys.argv[2])

    output_dir = None
    project = None
    positional = []
    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == "--output-dir" and i + 1 < len(sys.argv):
            output_dir = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == "--project" and i + 1 < len(sys.argv):
            project = sys.argv[i + 1].lower()
            i += 2
        else:
            positional.append(sys.argv[i])
            i += 1

    if not positional:
        usage()

    args = [a.lower() for a in positional]

    if project is None:
        project = detect_project(output_dir) or "hm6801"
        if "all" in args:
            print(f"[gen_tftp_script] --project not given, guessed '{project}' from output-dir",
                  file=sys.stderr)

    if project not in SUPPORTED_PROJECTS:
        print(f"Error: project '{project}' not supported by this script.")
        print(f"  Supported: {', '.join(SUPPORTED_PROJECTS)}")
        print(f"  HM6505 uses NAND, not supported here — 请用 device/soc/ingenic/pkg_tool/hm6505/auto_update_tftp.txt")
        sys.exit(1)

    if "full" in args:
        if len(args) > 1:
            print("Error: 'full' cannot be combined with other partitions")
            sys.exit(1)
        print("[gen_tftp_script] WARNING: FULL-CHIP mode — factory(RF 校准)/env/log 将被抹除，不可逆",
              file=sys.stderr)
        lines = gen_full(project, output_dir)
    elif "all" in args:
        if len(args) > 1:
            print("Error: 'all' cannot be combined with other partitions")
            sys.exit(1)
        lines = gen_all(project)
    else:
        for a in args:
            if a not in PARTITIONS:
                print(f"Error: unknown partition '{a}'")
                print(f"  Valid: all, {', '.join(PARTITION_ORDER)}")
                sys.exit(1)
        lines = gen_partitions(args)

    output = "\n".join(lines) + "\n"

    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out", f"image_{project}")
    out_file = os.path.join(output_dir, "auto_update_tftp.txt")
    os.makedirs(output_dir, exist_ok=True)
    with open(out_file, "w") as f:
        f.write(output)

    print(output, end="")
    print(f"\n=> Written to {out_file}  (project={project})")


if __name__ == "__main__":
    main()
