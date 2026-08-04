# FIT 镜像 mtdparts 动态改写机制

## 问题现象

HM6502 等设备运行时 `/proc/cmdline` 显示：
```
mtdparts=sfc0_nor:256k(boot),2368k(rootfs),5568k@0x290000(kernel_system_a),4141056@0x974200(system_b),...
```
但 PRJ.h 编译期定义只有 `kernel_system_a` / `kernel_system_b`，没有 `system_b`。
偏移 `0x974200` 也不是分区对齐的。这不是 bug，是 U-Boot bootm 阶段动态改写。

## 完整启动链

```
U-Boot bootm kernel_system_b.image (FIT 合并镜像: dtb + kernel + squashfs)
  │
  ├─ bootm_find_filesystem() 解析 FIT 内部结构
  │   ├─ 读 bootargs (含 PRJ.h 静态 mtdparts: ...kernel_system_b@0x800000...)
  │   ├─ 解析 system=1 -> old="kernel_system_b", new="system_b"
  │   ├─ offset = images.fs_addr - base  (squashfs 在 FIT 内的偏移, 如 0x174200)
  │   └─ mtdparts_offset(cmdline, old, new, fs_len, offset, out)
  │       └─ 找到 "kernel_system_b" 条目, 改写为:
  │          new_size @ (part_off + sub_offset) (new_name)
  │          = fs_len @ (0x800000 + 0x174200) ("system_b")
  │          = 4141056 @ 0x974200 (system_b)
  │
  ├─ setenv("bootargs", new_cmdline)  ← 改写后的 cmdline 传给内核
  │
  └─ 内核启动, 创建 mtdblock 设备:
      mtdblock3 = system_b @ 0x974200, size=4141056 (纯 squashfs)
      │
      ├─ root=/dev/mtdblock1 ro rootfstype=squashfs
      │   ↑ rootfs (2368K) = 最小 busybox init 层 (含 insmod_sfc_top, rcS)
      │
      └─ insmod_sfc_top (rootfs 内):
          ├─ 读 /proc/cmdline 的 system=0/1
          ├─ system=1 -> SYSTEM_PARTITION=system_b
          ├─ partition_analysis -p sfc0_nor -a system_b  ← 按名字查 mtdparts 索引
          └─ mount -t squashfs /dev/mtdblock${index} /system -o ro
              ↑ mtdblock3 从 0x974200 开始 = 纯 squashfs 头, mount 成功
```

## 为什么必须动态改写

两个不可静态化的原因：

### 1. squashfs 在 FIT 内的偏移不固定
FIT 镜像结构 = [dtb][kernel][squashfs]。squashfs 起始偏移取决于前面 kernel+dtb 的大小，
每次编译都可能变。PRJ.h 无法预知这个偏移，只能运行时由 bootm 解析 FIT 结构后计算。

### 2. mtdblock 设备按 mtdparts 条目对齐
内核根据 mtdparts 字符串创建 mtdblock 设备。不改写时 mtdblock3 覆盖整个 5568K@0x800000
（kernel+dtb+squashfs 混在一起），mount squashfs 会失败（开头是 kernel 不是 squashfs 头）。
改写后 mtdblock3 精确指向 squashfs 起始，mount 直接成功。

### 3. partition_analysis 按名字查找
rootfs 的 insmod_sfc_top 脚本用 `partition_analysis -p sfc0_nor -a system_b` 按名字查分区。
如果没有 `system_b` 这个名字，查不到索引，/system 挂不上。
动态改写同时创造了这个名字。

## 源码证据

### PRJ.h 静态定义 (line 643)
```c
#define BOOTARGS_SFCNOR_PARTITION \
  " mtdparts=sfc0_nor:256k(boot),2368k(rootfs)," \
  "5568k@0x290000(kernel_system_a)," \
  "5568k@0x800000(kernel_system_b)," \  ← 只有 kernel_system_b, 5568K 整块
  "1536k@0xD70000(algo),56k(factory),4k(env_a),4k(env_b),1024k(log)"
```
路径: `device/soc/ingenic/uboot/t32_t33/include/configs/PRJ.h`

### cmd_bootm.c 常量定义 (line 349-356)
```c
#define SYSTEM_BOOT "system="
#define KERNEL_SYSTEM_A "kernel_system_a"
#define KERNEL_SYSTEM_B "kernel_system_b"
#define SYSTEM_A "system_a"
#define SYSTEM_B "system_b"
```

### cmd_bootm.c bootm_find_filesystem() (line 482-557)
```c
commandline = getenv("bootargs");
system_p = strstr(commandline, SYSTEM_BOOT);
system = simple_strtol(system_p + strlen(SYSTEM_BOOT), NULL, 10);

if (system == 0) {
    old_partition = KERNEL_SYSTEM_A;  // "kernel_system_a"
    new_partition = SYSTEM_A;         // "system_a"
} else {
    old_partition = KERNEL_SYSTEM_B;  // "kernel_system_b"
    new_partition = SYSTEM_B;         // "system_b"
}

offset = images.fs_addr - base;  // squashfs 在 FIT 内的偏移
mtdparts_offset(commandline, old_partition, new_partition,
                images.fs_len, offset, new_cmdline, ...);
setenv("bootargs", new_cmdline);  // 改写后传给内核
```

### cmd_bootm.c mtdparts_offset() (line 399-477)
```c
// 遍历 cmdline 的 mtdparts 条目
// 找到 old_name (kernel_system_b) 条目后:
parse_partition_size_offset(part_start, &part_size, &part_off);  // part_off=0x800000

// 改写为:
n += snprintf(out + n, out_len - n, "%d@0x%x(%s)",
              new_size,                    // images.fs_len = 4141056
              (unsigned int)(part_off + sub_offset),  // 0x800000 + 0x174200 = 0x974200
              new_name);                   // "system_b"
```

### insmod_sfc_top (rootfs 脚本)
```sh
active=$(cat /proc/cmdline)
active=${active#*system=}
active=${active%% *}

if [ "$active" == "0" ]; then
    SYSTEM_PARTITION=system_a
elif [ "$active" == "1" ]; then
    SYSTEM_PARTITION=system_b
fi

system_index=$(partition_analysis -p sfc0_nor -a ${SYSTEM_PARTITION})
mount -t squashfs /dev/mtdblock${system_index} /system -o ro
```
路径: `third_party/rootfs/5.4.0_mxu2cve2/root-uclibc-toolchain540-r337-mxu2-cve2/usr/bin/insmod_sfc_top`

## 数字验证

| 量 | 值 | 来源 |
|----|-----|------|
| kernel_system_b 分区起点 | 0x800000 | PRJ.h line 643 |
| squashfs 在 FIT 内偏移 | 0x174200 | bootm 解析 FIT 结构: images.fs_addr - base |
| 改写后 system_b 起点 | 0x974200 | 0x800000 + 0x174200 ✓ |
| squashfs 实际大小 | 4141056 (0x3F3880) | images.fs_len (bootm 解析) |
| squashfs 尾部 | 0x567A80 | 0x174200 + 0x3F3880 |
| kernel_system_b 分区尾 | 0x570000 | 0x800000 + 0x570000 (5568K) |
| 尾部 < 分区尾 | 0x567A80 < 0x570000 ✓ | squashfs 在分区内 |

## Kernel 为什么不需要 mtdparts 条目

用户追问：既然 system_b 被"摘出来"挂载，kernel 分区为什么不在 CMDLINE 里显示？

答案：kernel 和 squashfs 的**消费方式完全不同**。

### Kernel: U-Boot raw read -> RAM 执行

U-Boot 通过 `update_kernel_bootcmd_by_system()` 根据 `system=0/1` **动态生成 bootcmd**，
用 raw flash offset 直接读 kernel 到 RAM，然后 bootm 执行。Linux 运行后不再访问 flash 上的 kernel 镜像。

```c
// main.c line 421-435
static int update_kernel_bootcmd_by_system(void)
{
    const char *kernel_offset;
    kernel_offset = mai_system_slot == MAI_SYSTEM_SLOT_B ?
        MAI_KERNEL_B_OFFSET : MAI_KERNEL_A_OFFSET;  // B=0x800000, A=0x290000

    snprintf(bootcmd, sizeof(bootcmd),
        "sf0 probe;sf0 read " MAI_KERNEL_LOAD_ADDR " %s "
        MAI_KERNEL_SIZE ";bootm " MAI_KERNEL_LOAD_ADDR,
        kernel_offset);  // -> "sf0 probe;sf0 read 0x80a00000 0x800000 0x600000;bootm 0x80a00000"
}
```

调用条件（main.c line 806）：
```c
#if defined(CONFIG_SUPPORT_A_B_PARTITION) && defined(CONFIG_SFC_NOR) && !defined(CONFIG_OF_LIBFDT)
    if (update_kernel_bootcmd_by_system())
        ...
#endif
```

HM6502 编译配置（mkconfig + PRJ.h）：
- CONFIG_FIT=y (mkconfig line 182)
- CONFIG_SFC_NOR=y (PRJ.h line 584, via CONFIG_SPL_SFC_NOR)
- CONFIG_SUPPORT_A_B_PARTITION=y (mkconfig line 187)
- CONFIG_OF_LIBFDT=未定义 (mkconfig 未写入)

-> 条件成立，bootcmd 动态生成。

### Squashfs (system_b): Linux mtdblock mount

squashfs 在 FIT 内部，Linux 需要把它 mount 成块设备 /system。
必须通过 mtdparts 条目创建 /dev/mtdblock3，且偏移精确指向 squashfs 头。
这就是前面描述的 mtdparts_offset() 动态改写机制。

### 对比总结

| 维度 | Kernel | Squashfs (system) |
|------|--------|-------------------|
| 消费者 | U-Boot | Linux |
| 获取方式 | sf0 read (raw flash offset) | mount -t squashfs /dev/mtdblockN |
| 需要 mtdparts? | 不需要（raw offset 硬编码在 bootcmd） | 需要（内核按 mtdparts 创建块设备） |
| 偏移来源 | MAI_KERNEL_A/B_OFFSET 宏 (main.c line 92-93) | PRJ.h 静态 + bootm 动态改写 |
| 运行后还需访问? | 不需要（已在 RAM 执行） | 需要（/system 只读挂载持续在线） |

### Slot 选择宏定义 (main.c line 75-94)

```c
#define MAI_SYSTEM_SLOT_A  0
#define MAI_SYSTEM_SLOT_B  1
#define MAI_SYSTEM_A_VALUE "0"
#define MAI_SYSTEM_B_VALUE "1"

// HM6502/HM6503/HM6801/HM6402:
#define MAI_KERNEL_LOAD_ADDR  "0x80a00000"
#define MAI_KERNEL_A_OFFSET   "0x290000"
#define MAI_KERNEL_B_OFFSET   "0x800000"
#define MAI_KERNEL_SIZE       "0x600000"  // 6MB, 覆盖整个 5568K 分区
```

system= 值来源：bootargs 中的 `system=` token（user_env -s system 0/1 写入 env）。
`get_effective_system_value()` (line 402-418) 解析后设置 `mai_system_slot`。

### CMDLINE 里残留的 kernel_system_a

mtdparts_offset() 只改写当前激活槽位（system=1 时改 kernel_system_b -> system_b）。
非激活槽 kernel_system_a 保持原样，留着给 OTA 用 -- Linux 需要知道非激活槽完整范围才能往里写新镜像。

## 烧录影响

**分区级烧录必须按 PRJ.h 编译期定义，不按运行时 CMDLINE：**
- 烧 `kernel_system_b.image` -> 偏移 0x800000, 大小 5568K (整块 FIT)
- 不要按 CMDLINE 的 `4141056@0x974200` 烧，那不是物理分区边界

`gen_tftp_script.py` 的 `system_b` 关键字烧的就是 0x800000 整块 FIT，符合设计。

## 适用范围

此机制适用于所有 Ingenic T32/T33 FIT 模式 NOR flash 项目：
HM6801 / HM6502 / HM6502_B01 / HM6503 / HM6402

HM6502_B01 分区大小不同 (5888K)，但动态改写机制相同。
非 FIT 模式 (PRJ.h line 648) 使用独立 kernel/system 分区，无此改写。
