# 第三方组件与署名

本仓库是 llama.cpp 新版 WebUI 的中文翻译补丁，本身不包含上游的代码产物、UI 打包文件或模型文件。

## 1. Yao-Shun-Ya/llama-webui-zh — MIT

- 仓库：https://github.com/Yao-Shun-Ya/llama-webui-zh
- 版权：Copyright (c) 2026 Yao-Shun-Ya
- 使用范围：`scripts/upstream_patch_b11344.py` 中的翻译词表（GR/LABEL/TITLE/TOOLTIP/HELP/DESCRIPTION/PLACEHOLDER/TEMPLATE/RAW 等）与
  "对 bundle 做字面量替换、用 `--path` 挂载" 的实现思路改编自该项目；
  本仓库对其进行了新版 UI 适配并增补约 150 条词表。
- 许可证原文：`THIRD_PARTY/llama-webui-zh-LICENSE`

## 2. ggml-org/llama.cpp — MIT

- 仓库：https://github.com/ggml-org/llama.cpp
- 版权：Copyright (c) 2023-2026 The ggml authors
- 使用范围：被汉化的 WebUI 本体。本仓库只在运行时生成的 `webui-zh/` 中做文本替换，
  且 `webui-en/`、`webui-zh/` 均为本地生成物，已通过 `.gitignore` 排除，不再分发。
- 许可证：MIT（https://github.com/ggml-org/llama.cpp/blob/master/LICENSE）

## 3. PrismML-eng/llama.cpp

- 仓库：https://github.com/PrismML-eng/llama.cpp
- 使用范围：验证环境所用的运行时 fork（`prism-b12232-f702476`），未复制其代码。

## 4. 翻译与适配

- 新增词表与适配脚本：Copyright (c) 2026 Entropysilence231
- 以 MIT 许可发布，详见 `LICENSE`
