# MIPS (Ingenic T32) 内核 FTRACE 配置指南

## 适用平台

- HM6502 / HM6801 / HM6502_B01 / HM6503 / HM6402
- SoC: Ingenic T32 (MIPS XBurst)
- 内核: 3.10.14__isvp_goat_1.0__
- defconfig: `arch/mips/configs/hm6502_nonramfs_defconfig`

## 安全可用的 ftrace 选项（实测 2026-07-12）

| 选项 | 用途 | 安全 | 说明 |
|------|------|------|------|
| `CONFIG_FTRACE=y` | Tracing 基础设施 | ✅ | 仅启用菜单，不插探针 |
| `CONFIG_SCHED_TRACER=y` | 调度延迟追踪 | ✅ | 基于 tracepoints，无运行时开销 |
| `CONFIG_IRQSOFF_TRACER=y` | 关中断延迟追踪 | ✅ | MIPS 支持 TRACE_IRQFLAGS_SUPPORT |
| `CONFIG_PREEMPT_TRACER=y` | 关抢占延迟追踪 | ✅ | CONFIG_PREEMPT=y 已启用 |
| `CONFIG_DEBUG_FS=y` | debugfs 挂载点 | ✅ | 必须挂载：`mount -t debugfs none /sys/kernel/debug` |
| `CONFIG_TRACEPOINTS=y` | 内核 tracepoints | ✅ | 已有，独立于 ftrace |

## ❌ 不可用的选项（MIPS 3.10 已知问题）

### CONFIG_FUNCTION_TRACER

**症状：** 在 defconfig 中启用后内核引导阶段崩溃，串口无任何输出，设备硬挂（需要物理断电恢复）。

**根因（2026-07-12 分析）：**
- MIPS 3.10 上 `CONFIG_FUNCTION_TRACER` 在每个内核函数入口插入 `mcount` 探针（-pg 编译标志）
- MIPS 架构的 `mcount` 实现（`arch/mips/kernel/mcount.S`）在 3.10 版本存在 bug，启动初期调用未初始化的函数时触发
- 与 `CONFIG_FRAME_POINTER` 无关——MIPS 被显式排除在 `lib/Kconfig.debug` 的 `select FRAME_POINTER` 之外（第 623 行：`select FRAME_POINTER if !MIPS && ...`）
- `CONFIG_SCHED_OMIT_FRAME_POINTER=y` 不和 ftrace 冲突

### CONFIG_STACK_TRACER

**症状：** 自动 select `CONFIG_FUNCTION_TRACER`，连带触发 mcount bug。

### CONFIG_FTRACE_STARTUP_TEST

**症状：** 启动自测可能触发内核态 ftrace 的其他边界 bug。

## defconfig 修改示例

在 `CONFIG_TRACING_SUPPORT=y` 行之后添加：

```kconfig
# FTRACE for profiling
CONFIG_FTRACE=y
CONFIG_SCHED_TRACER=y
CONFIG_IRQSOFF_TRACER=y
CONFIG_PREEMPT_TRACER=y
# CONFIG_FUNCTION_TRACER is not set   # ← MIPS 3.10 mcount bug
# CONFIG_FUNCTION_GRAPH_TRACER is not set
# CONFIG_STACK_TRACER is not set
```

## 验证 ftrace 在工作

烧录后登录设备：

```bash
# 挂载 debugfs（如未挂载）
mount -t debugfs none /sys/kernel/debug

# 查看可用 tracer
cat /sys/kernel/debug/tracing/available_tracers
# 预期输出: sched_switch sched_wakeup irqsoff preemptirqsoff preemptoff nop

# 启用调度追踪
echo sched_switch > /sys/kernel/debug/tracing/current_tracer
cat /sys/kernel/debug/tracing/trace

# 启用关中断延迟追踪
echo irqsoff > /sys/kernel/debug/tracing/current_tracer
```

## 注意事项

- `CONFIG_FTRACE=y` 会增加内核大小约 100KB（kernel_system_b.image 从 5.67MB → 5.77MB）
- 在 16MB NOR flash 上足够，分区空闲约 800KB
- debugfs 默认由 init 脚本挂载（`/etc/inittab` 或 `init.sh`），如果没挂载需手动执行
- ftrace 是轻量级跟踪，运行时开销取决于选的 tracer。`nop` 模式几乎无开销
