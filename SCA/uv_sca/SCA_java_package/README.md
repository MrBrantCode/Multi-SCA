# SCA Engine - Java实现

软件成分分析（Software Composition Analysis）工具的Java实现版本。

## 功能特性

- ✅ ZIP项目文件解压
- ✅ 调用uv tree获取Python依赖树
- ✅ PURL（Package URL）生成
- ✅ 在线漏洞查询（MySQL数据库）
- ✅ 多种报告格式（JSON、CSV、SBOM）

## 系统要求

- Java 11 或更高版本
- Maven 3.6+
- uv工具（用于Python依赖分析）
- MySQL数据库（在线模式需要）

## 构建项目

```bash
cd SCA_java
mvn clean package
```

构建完成后，会在 `target/` 目录生成：
- `sca-engine-1.0.0-jar-with-dependencies.jar` - 主程序（包含所有依赖）
- `export-tool-1.0.0-jar-with-dependencies.jar` - 导出工具（需要单独构建）

## 使用方法

**重要提示**：构建完成后，JAR文件位于 `target/` 目录下，文件名为 `sca-engine-1.0.0-jar-with-dependencies.jar`。

### 1. 扫描项目（交互式输入 - 推荐）

直接运行程序，然后按提示输入ZIP文件路径：

```bash
# Windows PowerShell
cd SCA_java
java -jar target\sca-engine-1.0.0-jar-with-dependencies.jar

# Linux/Mac
cd SCA_java
java -jar target/sca-engine-1.0.0-jar-with-dependencies.jar
```

运行后会提示输入ZIP文件路径，支持：
- 相对路径：`uvtest1.zip`
- 绝对路径：`D:\projects\uvtest1.zip`
- 拖拽文件：直接拖拽ZIP文件到命令行窗口

### 2. 扫描项目（命令行参数）

也可以通过命令行参数直接指定文件：

```bash
# Windows PowerShell
cd SCA_java
java -jar target\sca-engine-1.0.0-jar-with-dependencies.jar uvtest1.zip

# Linux/Mac
cd SCA_java
java -jar target/sca-engine-1.0.0-jar-with-dependencies.jar uvtest1.zip
```

### 3. 导出漏洞数据库（可选，用于备份）

导出工具需要指定主类 `com.sca.export.ExportMain` 来运行：

```bash
# Windows PowerShell
cd SCA_java
java -cp target\sca-engine-1.0.0-jar-with-dependencies.jar com.sca.export.ExportMain --output vulnerability_db.json

# Linux/Mac
cd SCA_java
java -cp target/sca-engine-1.0.0-jar-with-dependencies.jar com.sca.export.ExportMain --output vulnerability_db.json
```

或使用默认文件名（自动生成时间戳）：

```bash
# Windows PowerShell
cd SCA_java
java -cp target\sca-engine-1.0.0-jar-with-dependencies.jar com.sca.export.ExportMain

# Linux/Mac
cd SCA_java
java -cp target/sca-engine-1.0.0-jar-with-dependencies.jar com.sca.export.ExportMain
```

断点续传模式（从已有文件继续导出）：

```bash
# Windows PowerShell
cd SCA_java
java -cp target\sca-engine-1.0.0-jar-with-dependencies.jar com.sca.export.ExportMain --resume vulnerability_db.json

# Linux/Mac
cd SCA_java
java -cp target/sca-engine-1.0.0-jar-with-dependencies.jar com.sca.export.ExportMain --resume vulnerability_db.json
```

### 2. 扫描项目（交互式输入 - 推荐）

直接运行程序，然后按提示输入ZIP文件路径：

```bash
# Windows PowerShell
cd SCA_java
java -jar target\sca-engine-1.0.0-jar-with-dependencies.jar

# Linux/Mac
cd SCA_java
java -jar target/sca-engine-1.0.0-jar-with-dependencies.jar
```

运行后会提示输入ZIP文件路径，支持：
- 相对路径：`uvtest1.zip`
- 绝对路径：`D:\projects\uvtest1.zip`
- 拖拽文件：直接拖拽ZIP文件到命令行窗口

**或者使用命令行参数**：

```bash
# Windows PowerShell
cd SCA_java
java -jar target\sca-engine-1.0.0-jar-with-dependencies.jar uvtest1.zip

# Linux/Mac
cd SCA_java
java -jar target/sca-engine-1.0.0-jar-with-dependencies.jar uvtest1.zip
```

**注意**：
- 如果ZIP文件不在当前目录，请使用相对路径或绝对路径
- 需要确保数据库连接配置正确
- 扫描完成后，报告文件会自动生成在当前目录

## 项目结构

```
SCA_java/
├── pom.xml                          # Maven配置文件
├── README.md                        # 本文件
└── src/main/java/com/sca/
    ├── SCAMain.java                 # 主程序入口
    ├── core/                        # 核心功能
    │   ├── Dependency.java          # 依赖包模型
    │   ├── ZipExtractor.java        # ZIP解压
    │   ├── ProjectFinder.java       # 项目查找
    │   ├── UvTreeRunner.java        # uv tree执行
    │   ├── DependencyParser.java    # 依赖解析
    │   └── PurlGenerator.java       # PURL生成
    ├── database/                    # 数据库相关
    │   └── VulnerabilityDatabase.java      # 在线数据库
    ├── report/                      # 报告生成
    │   └── ReportGenerator.java     # 报告生成器
    └── export/                      # 导出工具
        ├── VulnerabilityExporter.java # 导出器
        └── ExportMain.java          # 导出工具入口
```

## 报告格式

### JSON报告
包含所有漏洞的详细信息，适合程序化处理。

### CSV报告
包含漏洞的关键信息，适合Excel等工具打开。

### SBOM报告
CycloneDX格式的软件物料清单，包含组件和漏洞信息。

## 配置

数据库配置在 `VulnerabilityDatabase.java` 和 `VulnerabilityExporter.java` 中：

```java
private static final String DB_HOST = "10.176.37.194";
private static final String DB_NAME = "osschain_bachelor";
private static final String DB_USER = "u_bachelor";
private static final String DB_PASSWORD = "bachelor12345";
```

如需修改，请编辑相应文件后重新编译。

## 与Python版本的对比

| 特性 | Python版本 | Java版本 |
|------|-----------|----------|
| 依赖管理 | requirements.txt | Maven (pom.xml) |
| JSON处理 | json库 | Gson |
| CSV处理 | csv库 | Apache Commons CSV |
| 数据库连接 | mysql-connector-python | mysql-connector-j |
| 打包方式 | 脚本文件 | JAR包 |
| 性能 | 中等 | 较高 |
| 部署 | 需要Python环境 | 只需JRE |

## 常见问题

### Q: 运行时提示 "Unable to access jarfile" 错误？
A: 请确保：
1. 使用完整的JAR文件名：`sca-engine-1.0.0-jar-with-dependencies.jar`
2. JAR文件在 `target/` 目录下
3. 使用正确的路径，例如：`target\sca-engine-1.0.0-jar-with-dependencies.jar`（Windows）或 `target/sca-engine-1.0.0-jar-with-dependencies.jar`（Linux/Mac）

### Q: 如何修改数据库连接信息？
A: 编辑 `VulnerabilityDatabase.java` 和 `VulnerabilityExporter.java` 中的数据库配置常量，然后重新编译。

### Q: 支持哪些Python包管理器？
A: 当前仅支持uv工具。如需支持pip等其他工具，需要修改 `UvTreeRunner.java`。


### Q: 如何快速使用（不每次都输入完整路径）？
A: 可以创建快捷脚本：

**Windows (run.bat)** - 用于扫描：
```batch
@echo off
cd /d %~dp0
java -jar target\sca-engine-1.0.0-jar-with-dependencies.jar %*
```

**Windows (export.bat)** - 用于导出数据库：
```batch
@echo off
cd /d %~dp0
java -cp target\sca-engine-1.0.0-jar-with-dependencies.jar com.sca.export.ExportMain %*
```

**Linux/Mac (run.sh)** - 用于扫描：
```bash
#!/bin/bash
cd "$(dirname "$0")"
java -jar target/sca-engine-1.0.0-jar-with-dependencies.jar "$@"
```

**Linux/Mac (export.sh)** - 用于导出数据库：
```bash
#!/bin/bash
cd "$(dirname "$0")"
java -cp target/sca-engine-1.0.0-jar-with-dependencies.jar com.sca.export.ExportMain "$@"
```

然后就可以直接使用：
```bash
# Windows - 扫描
.\run.bat uvtest1.zip

# Windows - 导出
.\export.bat --output vulnerability_db.json

# Linux/Mac - 扫描
./run.sh uvtest1.zip

# Linux/Mac - 导出
./export.sh --output vulnerability_db.json
```

## 许可证

与Python版本保持一致。

## 更新日志

### v1.0.0
- 初始版本
- 实现所有核心功能
- 支持在线数据库查询
- 支持多种报告格式

