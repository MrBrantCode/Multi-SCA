package com.sca.export;

import java.io.File;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;

/**
 * 漏洞数据库导出工具主程序
 */
public class ExportMain {
    
    public static void main(String[] args) {
        String outputFile = null;
        boolean resume = false;
        
        // 解析命令行参数
        if (args.length >= 2 && "--resume".equals(args[0])) {
            outputFile = args[1];
            resume = true;
        } else if (args.length >= 2 && "--output".equals(args[0])) {
            outputFile = args[1];
        } else if (args.length == 0) {
            // 默认文件名
            outputFile = "vulnerability_db_" + 
                LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMdd_HHmm")) + ".json";
        } else {
            printUsage();
            System.exit(1);
        }
        
        System.out.println("=".repeat(60));
        System.out.println("漏洞数据库导出工具");
        System.out.println("=".repeat(60));
        System.out.println("数据库: 10.176.37.194/osschain_bachelor");
        System.out.println("输出文件: " + outputFile);
        if (resume) {
            System.out.println("模式: 断点续传（从已有文件继续）");
        } else {
            System.out.println("模式: 全新导出");
        }
        System.out.println("=".repeat(60));
        
        VulnerabilityExporter exporter = new VulnerabilityExporter();
        
        if (!exporter.connect()) {
            System.err.println("[!] 无法连接数据库，退出");
            System.exit(1);
        }
        
        try {
            boolean success = exporter.exportAllVulnerabilities(outputFile, resume);
            
            if (success) {
                File file = new File(outputFile);
                long fileSize = file.length() / 1024 / 1024;
                System.out.println("\n[+] 导出完成！");
                System.out.println("[+] 文件: " + outputFile);
                System.out.println("[+] 大小: " + fileSize + " MB");
            } else {
                System.err.println("[!] 导出失败");
                System.exit(1);
            }
        } catch (Exception e) {
            System.err.println("[!] 导出失败: " + e.getMessage());
            e.printStackTrace();
            System.exit(1);
        } finally {
            exporter.disconnect();
        }
    }
    
    private static void printUsage() {
        System.out.println("用法:");
        System.out.println("  java -jar export-tool.jar [--output <文件路径>]");
        System.out.println("  java -jar export-tool.jar --resume <已有文件路径>");
        System.out.println("\n示例:");
        System.out.println("  java -jar export-tool.jar");
        System.out.println("  java -jar export-tool.jar --output db.json");
        System.out.println("  java -jar export-tool.jar --resume db.json");
    }
}




