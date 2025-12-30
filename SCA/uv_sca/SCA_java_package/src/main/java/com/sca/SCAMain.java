package com.sca;

import com.sca.core.*;
import com.sca.database.VulnerabilityDatabase;
import com.sca.report.*;
import com.sca.util.InputValidator;

import java.io.File;
import java.io.IOException;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;
import java.util.Scanner;
import org.apache.commons.io.FileUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * SCA工具主程序
 */
public class SCAMain {
    private static final Logger logger = LoggerFactory.getLogger(SCAMain.class);
    
    public static void main(String[] args) {
        String zipPath;
        
        // 如果提供了命令行参数，使用参数；否则提示用户输入
        if (args.length >= 1) {
            zipPath = args[0];
        } else {
            // 交互式输入
            zipPath = promptForZipPath();
            if (zipPath == null || zipPath.trim().isEmpty()) {
                System.out.println("\n[!] 未输入文件路径，程序退出");
                System.exit(0);
            }
        }
        
        try {
            // 输入验证
            InputValidator.validateZipFile(zipPath);
            
            // 自动执行扫描并生成报告
            main(zipPath);
            
        } catch (SCAException e) {
            logger.error("[!] {}", e.getMessage());
            logger.error("   提示: 请检查输入文件");
            System.exit(1);
        } catch (IllegalArgumentException e) {
            logger.error("[!] 输入验证失败: {}", e.getMessage());
            System.exit(1);
        } catch (Exception e) {
            logger.error("[!] 发生未知错误");
            // 只在调试模式打印堆栈
            if (System.getProperty("debug") != null) {
                logger.error("详细错误信息", e);
            } else {
                logger.error("   提示: 使用 -Ddebug=true 查看详细错误信息");
            }
            System.exit(1);
        }
    }
    
    /**
     * 提示用户输入ZIP文件路径
     */
    private static String promptForZipPath() {
        System.out.println("=".repeat(60));
        System.out.println("          SCA工具 - 软件成分分析");
        System.out.println("=".repeat(60));
        System.out.println();
        System.out.print("请输入ZIP文件路径（支持相对路径和绝对路径）: ");
        
        try (Scanner scanner = new Scanner(System.in)) {
            String input = scanner.nextLine().trim();
            
            // 处理用户输入，支持拖拽文件路径（可能包含引号）
            if (input.startsWith("\"") && input.endsWith("\"")) {
                input = input.substring(1, input.length() - 1);
            }
            if (input.startsWith("'") && input.endsWith("'")) {
                input = input.substring(1, input.length() - 1);
            }
            
            return input;
        }
    }
    
    private static void main(String zipPath) throws SCAException {
        logger.info("=".repeat(60));
        logger.info("SCA工具 - 软件成分分析");
        logger.info("=".repeat(60));
        
        // 1. 解压ZIP文件
        logger.info("[+] 解压ZIP文件: {}", zipPath);
        Path extractDir = null;
        try {
            try {
                extractDir = ZipExtractor.extract(zipPath);
            } catch (IOException e) {
                throw new SCAException("解压ZIP文件失败: " + e.getMessage(), e);
            }
            logger.info("[+] 已解压到: {}", extractDir);
            
            // 2. 查找项目目录
            Path projectDir;
            try {
                projectDir = ProjectFinder.findUvProject(extractDir);
            } catch (IOException e) {
                throw new SCAException("查找项目目录失败: " + e.getMessage(), e);
            }
            if (projectDir == null) {
                throw new SCAException("未找到uv项目目录（需要包含pyproject.toml或uv.lock）");
            }
            logger.info("[+] 找到项目目录: {}", projectDir);
            
            // 2.5. 删除损坏的.venv目录（如果存在）
            Path venvPath = projectDir.resolve(".venv");
            if (java.nio.file.Files.exists(venvPath)) {
                try {
                    logger.info("[+] 检测到.venv目录，正在删除以避免使用损坏的venv...");
                    deleteDirectory(venvPath.toFile());
                    logger.info("[+] 已删除.venv目录");
                } catch (Exception e) {
                    logger.error("[!] 删除.venv时出错: {}", e.getMessage());
                }
            }
            
            // 3. 运行uv tree获取依赖
            logger.info("[+] 执行uv tree...");
            List<Dependency> dependencies = null;
            
            try {
                String uvTreeOutput = UvTreeRunner.runUvTree(projectDir);
                // 解析依赖树
                logger.info("[+] 解析依赖树...");
                dependencies = DependencyParser.parse(uvTreeOutput);
                logger.info("[+] 找到 {} 个依赖包", dependencies.size());
            } catch (Exception e) {
                logger.error("[!] uv tree执行失败: {}", e.getMessage());
                
                // 检查错误是否可能是网络问题
                String errorMsg = e.getMessage().toLowerCase();
                boolean isNetworkError = errorMsg.contains("failed to fetch") || 
                                        errorMsg.contains("network") || 
                                        errorMsg.contains("dns error") ||
                                        errorMsg.contains("connect");
                
                // 如果是网络错误，尝试从pyproject.toml解析
                if (isNetworkError) {
                    logger.info("[+] 检测到网络错误，尝试从pyproject.toml解析依赖...");
                    dependencies = PyProjectParser.parse(projectDir);
                    if (dependencies != null && !dependencies.isEmpty()) {
                        logger.info("[+] 从pyproject.toml生成 {} 个依赖", dependencies.size());
                    } else {
                        logger.warn("[!] 无法从pyproject.toml解析依赖，请确保项目包含uv.lock文件或pyproject.toml中有精确版本依赖（如 requests==2.20.0）");
                        throw new SCAException("无法获取依赖信息");
                    }
                } else {
                    throw new SCAException("uv tree执行失败: " + e.getMessage(), e);
                }
            }
            
            // 5. 生成PURL列表
            logger.info("[+] 生成PURL...");
            List<String> purlList = PurlGenerator.generate(dependencies);
            logger.info("[+] 生成 {} 个PURL", purlList.size());
            
            if (purlList.isEmpty()) {
                logger.warn("[!] 未生成PURL列表，跳过漏洞查询");
                return;
            }
            
            // 6. 查询漏洞
            logger.info("[+] 查询漏洞...");
            List<Map<String, Object>> vulnerabilities;
            
            VulnerabilityDatabase db = new VulnerabilityDatabase();
            if (!db.connect()) {
                throw new SCAException("无法连接数据库");
            }
            try {
                vulnerabilities = db.queryVulnerabilitiesByPurl(purlList);
            } finally {
                db.disconnect();
            }
            
            logger.info("[+] 找到 {} 个漏洞", vulnerabilities.size());
            
            // 7. 生成报告
            String zipName = new File(zipPath).getName().replace(".zip", "");
            String timestamp = java.time.LocalDateTime.now()
                .format(java.time.format.DateTimeFormatter.ofPattern("yyyyMMdd_HHmm"));
            
            // 控制台报告
            ReportGenerator.generateConsoleReport(vulnerabilities, purlList.size());
            
            // JSON报告
            String jsonReportPath = String.format("vulnerability_report_%s_%s.json", timestamp, zipName);
            try {
                ReportGenerator.generateJsonReport(vulnerabilities, jsonReportPath);
                logger.info("[+] JSON报告已生成: {}", jsonReportPath);
            } catch (IOException e) {
                throw new SCAException("生成JSON报告失败: " + e.getMessage(), e);
            }
            
            // CSV报告
            String csvReportPath = String.format("vulnerability_report_%s_%s.csv", timestamp, zipName);
            try {
                ReportGenerator.generateCsvReport(vulnerabilities, csvReportPath);
                logger.info("[+] CSV报告已生成: {}", csvReportPath);
            } catch (IOException e) {
                throw new SCAException("生成CSV报告失败: " + e.getMessage(), e);
            }
            
            // SBOM报告
            String sbomReportPath = String.format("sbom_report_%s_%s.json", timestamp, zipName);
            try {
                ReportGenerator.generateSbomReport(vulnerabilities, purlList, sbomReportPath);
                logger.info("[+] SBOM报告已生成: {}", sbomReportPath);
            } catch (IOException e) {
                throw new SCAException("生成SBOM报告失败: " + e.getMessage(), e);
            }
            
            logger.info("\n[+] 扫描完成！所有报告已生成在当前目录");
        } finally {
            // 清理临时文件
            if (extractDir != null) {
                try {
                    FileUtils.deleteDirectory(extractDir.toFile());
                    logger.info("[+] 已清理临时目录");
                } catch (Exception e) {
                    logger.warn("[!] 清理临时目录失败: {}", e.getMessage());
                }
            }
        }
    }
    
    /**
     * 递归删除目录
     */
    private static void deleteDirectory(java.io.File directory) {
        if (directory.exists()) {
            java.io.File[] files = directory.listFiles();
            if (files != null) {
                for (java.io.File file : files) {
                    if (file.isDirectory()) {
                        deleteDirectory(file);
                    } else {
                        file.delete();
                    }
                }
            }
            directory.delete();
        }
    }
}

