# Codex Profiles

这些文件安装到 `~/.codex/<name>.config.toml`，通过 `codex --profile <name>` 选择。

- `daily`：日常实现与普通 bug。
- `budget`：机械修改、批处理和低风险任务。
- `readonly`：只读探索与资料整理。
- `deep`：跨文件复杂实现、并发与难复现问题。
- `extreme`：架构迁移、高风险合同与最难推理。
- `interactive-fast`：仅用于人在屏幕前等待的交互任务；这是唯一默认开启 Fast mode 的模板。

共享 `config.toml` 不固定 model / reasoning / verbosity / service tier，避免安装脚本覆盖本机或账号已有偏好。若当前账号不支持模板模型，先运行：

```bash
python3 scripts/check_codex_model_policy.py
```

再根据输出调整本机 Profile；不要把账号私有或预览型号写回跨设备共享 baseline。
