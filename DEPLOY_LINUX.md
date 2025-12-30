## Linux 服务器部署（命令行工具 sca）

### 目标
- 在服务器任意目录下直接运行 `sca ...`（不需要 `python sca.py ...`）。
- 支持：
  - `sca detect <path>`
  - `sca scan <path> --results-dir <dir>`
  - `sca shell`（交互式）

### 前置条件
- Python 3.9+
- Java 11+（用于 JavaScript 组 jar）
- Rust 工具：需要对应 Linux 平台可执行文件（当前仓库内 `rustpj` 若为 macOS 编译，需在 Linux 上重新编译）

### 部署方式 A（推荐）：pip 安装生成 sca 命令
1. 拷贝整个项目到服务器（例如 `/opt/sca`），目录里应包含 `SCA/`、`unified_sca/`、`pyproject.toml`。
2. 安装：

```bash
cd /opt/sca
python3 -m venv .venv
. .venv/bin/activate
pip install -U pip
pip install .
```

3. 让工具找到三组工具目录：
   - 推荐设置环境变量 `SCA_TOOLS_ROOT` 指向包含 `SCA/` 目录的路径（通常就是 `/opt/sca`）：

```bash
export SCA_TOOLS_ROOT="/opt/sca"
```

4. 使用：

```bash
sca detect /path/to/test_project
sca scan /path/to/project --results-dir /path/to/results
sca shell
```

### 部署方式 B：不安装，直接把脚本加入 PATH
如果你不想 pip install：

```bash
export PATH="/opt/sca/bin:$PATH"
export SCA_TOOLS_ROOT="/opt/sca"
sca detect /path/to/test_project
```

### 交互式模式（sca shell）
进入 shell 后，你可以输入：
- `detect <path> ...`
- `scan <path> --results-dir <dir>`
- `help`
- `exit`


