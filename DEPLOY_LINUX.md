## Linux 服务器部署（命令行工具 sca）

### 目标
- 在服务器任意目录下直接运行 `sca ...`（不需要 `python sca.py ...`）。
- 支持：
  - `sca detect <path>`
  - `sca scan <path> --results-dir <dir>`
  - `sca shell`（交互式）

### 前置条件
- Python 3.9+
- （纯 Python 版本）无需 Java / cargo

### 部署方式 A（推荐）：pip 安装生成 sca 命令
1. 拷贝整个项目到服务器（例如 `/opt/sca`），目录里应包含 `unified_sca/`、`sca_tools/`、`pyproject.toml`、`test_project/`（可选）。
2. 安装：

```bash
cd /opt/sca
python3 -m venv .venv
. .venv/bin/activate
pip install -U pip
pip install .
```

3. 使用：

```bash
sca detect /path/to/test_project
sca scan /path/to/project --results-dir /path/to/results
sca shell
```

### 部署方式 B：不安装，直接把脚本加入 PATH
如果你不想 pip install：

```bash
export PATH="/opt/sca/bin:$PATH"
sca detect /path/to/test_project
```

### 交互式模式（sca shell）
进入 shell 后，你可以输入：
- `detect <path> ...`
- `scan <path> --results-dir <dir>`
- `help`
- `exit`


