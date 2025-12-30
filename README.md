# SCA 统一命令行工具（Rust / Python(uv) / JavaScript）

本项目将 SCA 分析能力统一封装成一个命令行入口 `sca`，支持：
- 自动识别项目类型（目录或 zip）
- 按类型调用对应 **纯 Python 分析器** 生成 SBOM（CycloneDX JSON）与相关输出
- 统一归档到 `results/` 目录
- 支持交互式命令行：`sca shell`

> 当前已接入（纯 Python）：**Rust(Cargo.lock)**、**Python(pyproject.toml)**、**JavaScript(package-lock.json)**  
> 后续可按统一接口扩展接入 Java/Maven、Go、.NET 等。

---

## 项目结构（高层）

- `unified_sca/`：统一包装器（CLI / detect / zip_utils / shell）
  - `cli.py`：统一命令入口（detect/scan/shell）
  - `detect.py`：项目类型识别（支持 zip 下钻）
  - `zip_utils.py`：安全解压（含 Windows 反斜杠路径规范化）
  - `shell.py`：交互式 shell
- `sca_tools/`：纯 Python 分析器（产品化/可扩展）
  - `sca_tools/base.py`：统一 Analyzer 接口/输出约定
  - `sca_tools/registry.py`：按类型调度
  - `sca_tools/analyzers/`：各语言锁文件解析与 SBOM 生成
- `test_project/`：测试用项目（目录/zip）
- `results/`：统一输出目录（scan 时生成）

---

## 支持的输入形式

所有 `detect/scan` 的 `<path>` 支持：
- **项目目录**
- **zip 文件**（`.zip`）

工具会在内部做“净化/解压/重新打包”，避免 `.git/.venv/node_modules` 等干扰。

---

## 命令用法（本机/服务器通用）

### 1) 识别项目类型（不生成结果文件）

```bash
sca detect "<path>"
```

常用选项：
- `--first-level`：对容器目录第一层子目录/zip逐个识别并汇总输出
- `--work-base <dir>`：指定 zip 临时解压目录基路径

### 2) 执行扫描（生成 SBOM 并归档到 results）

```bash
sca scan "<path>" --results-dir "<results_dir>"
```

说明：
- `--results-dir` 是“输出根目录”，工具会在其下创建 `rust/`、`python/`、`javascript/` 子目录。

### 3) 交互式模式（进入后再输入命令）

```bash
sca shell
```

在 `sca>` 提示符下可输入（注意：不要再写前缀 `sca`）：

```text
sca> detect /path/to/test_project
sca> scan /path/to/sample_npm --results-dir /path/to/results
sca> exit
```

---

## 输出目录结构

以 `--results-dir /opt/results` 为例：

- `/opt/results/rust/<project>/<timestamp>/`
  - `sbom.json`
  - `vuln_report.json`
  - `rustpj.stdout.txt`
  - `rustpj.stderr.txt`
- `/opt/results/python/<project>/<timestamp>/`
  - `sbom.json`
  - `vuln_report.json`
  - `scan_details.json`
- `/opt/results/javascript/<project>/<timestamp>/`
  - `sbom.json`
  - `nbtosbom.stdout.txt`
  - `nbtosbom.stderr.txt`

---

## 离线/服务器部署注意事项（重要）

### Rust（强烈建议）
- **建议被测项目携带 `Cargo.lock`**（否则工具可能尝试 `cargo generate-lockfile`，离线/无 cargo 会失败）
- 漏洞库使用本仓库自带的 `SCA/rust_sca/rustpj/data/advisory-db`

### Python
- 当前纯 Python 版本默认从 `pyproject.toml` 读取 **直接依赖** 生成 SBOM（不依赖 uv / 不联网）
  - 若希望未来生成“完整传递依赖树”，可在后续版本引入 lock 文件解析/离线索引机制（按统一接口扩展即可）

### JavaScript（npm lock）
- 依赖 `package-lock.json`
- 当前纯 Python 版本无需 Java

---

## Linux 服务器部署（推荐方式：pip install 生成 sca 命令）

假设你将项目放在 `/opt/sca`（该目录内应包含 `SCA/`、`unified_sca/`、`pyproject.toml` 等）：

```bash
cd /opt/sca
python3 -m venv .venv
. .venv/bin/activate
pip install -U pip
pip install .
```

安装后会生成命令 `sca`。

（纯 Python 版本无需配置 `SCA_TOOLS_ROOT`）

### 使用示例

```bash
sca detect /opt/sca/test_project
sca scan /opt/sca/test_project/javascript/rich_npm --results-dir /opt/sca/results
sca shell
```

---

## Linux 服务器部署（替代方式：直接把脚本加入 PATH）

如果你不想 `pip install .`，也可以把项目自带脚本加入 PATH：

```bash
export PATH="/opt/sca/bin:$PATH"
export SCA_TOOLS_ROOT="/opt/sca"
sca detect /path/to/project
```

---

## 常见问题（FAQ）

### 1) `sca shell` 里执行 `sca scan ...` 报错？
交互模式下不要再写 `sca` 前缀，直接输入子命令：

```text
sca> scan /path/to/project --results-dir /path/to/results
```

### 2) 识别 zip 失败（Windows 打包）？
已对 zip 内反斜杠路径（`\`）做了规范化处理；若仍失败，建议用 `detect --keep-workdir` 保留临时目录排查。


