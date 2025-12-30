package com.sca.core;

import java.io.BufferedReader;
import java.io.File;
import java.io.IOException;
import java.io.InputStreamReader;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

/**
 * 执行uv tree命令
 */
public class UvTreeRunner {
    
    /**
     * 运行uv tree命令
     * @param projectDir 项目目录
     * @return uv tree输出
     * @throws Exception 执行失败时抛出异常
     */
    public static String runUvTree(Path projectDir) throws Exception {
        System.out.println("[+] 在 " + projectDir + " 中执行 uv tree...");
        
        // 检查uv是否可用
        String[] uvCommand = findUvCommand();
        if (uvCommand == null) {
            throw new RuntimeException("未找到uv命令，请确保已安装uv");
        }
        
        // 检查并清理损坏的.venv
        cleanupCorruptedVenv(projectDir);
        
        // 构建命令
        List<String> command = new ArrayList<>();
        for (String part : uvCommand) {
            command.add(part);
        }
        command.add("tree");
        // 尝试找到Python可执行文件
        String pythonPath = findPython();
        if (pythonPath != null) {
            command.add("--python");
            command.add(pythonPath);
        }
        
        // 如果存在uv.lock文件，使用--locked参数（避免网络访问）
        Path lockFile = projectDir.resolve("uv.lock");
        if (Files.exists(lockFile)) {
            System.out.println("[+] 检测到uv.lock文件，使用--locked参数（避免网络访问）");
            command.add("--locked");
        }
        
        ProcessBuilder pb = new ProcessBuilder(command);
        pb.directory(projectDir.toFile());
        pb.redirectErrorStream(true);
        
        Process process = pb.start();
        
        StringBuilder output = new StringBuilder();
        try (BufferedReader reader = new BufferedReader(
                new InputStreamReader(process.getInputStream()))) {
            String line;
            while ((line = reader.readLine()) != null) {
                output.append(line).append("\n");
            }
        }
        
        int exitCode = process.waitFor();
        if (exitCode != 0) {
            throw new RuntimeException("uv tree执行失败，退出码: " + exitCode + "\n输出: " + output);
        }
        
        return output.toString();
    }
    
    /**
     * 查找uv命令
     */
    private static String[] findUvCommand() {
        // 先尝试 python -m uv
        try {
            Process process = new ProcessBuilder("python", "-m", "uv", "--version")
                .redirectErrorStream(true)
                .start();
            int exitCode = process.waitFor();
            if (exitCode == 0) {
                System.out.println("[+] 使用 python -m uv");
                return new String[]{"python", "-m", "uv"};
            }
        } catch (Exception e) {
            // 忽略
        }
        
        // 再尝试直接调用uv
        try {
            Process process = new ProcessBuilder("uv", "--version")
                .redirectErrorStream(true)
                .start();
            int exitCode = process.waitFor();
            if (exitCode == 0) {
                System.out.println("[+] 使用 uv");
                return new String[]{"uv"};
            }
        } catch (Exception e) {
            // 忽略
        }
        
        return null;
    }
    
    /**
     * 查找Python可执行文件
     */
    private static String findPython() {
        String[] commands = {"python", "python3", "py"};
        for (String cmd : commands) {
            try {
                Process process = new ProcessBuilder(cmd, "--version")
                    .redirectErrorStream(true)
                    .start();
                int exitCode = process.waitFor();
                if (exitCode == 0) {
                    return cmd;
                }
            } catch (Exception e) {
                // 继续尝试下一个
            }
        }
        return null;
    }
    
    /**
     * 清理损坏的.venv目录
     */
    private static void cleanupCorruptedVenv(Path projectDir) {
        Path venvDir = projectDir.resolve(".venv");
        if (java.nio.file.Files.exists(venvDir)) {
            Path pythonExe = venvDir.resolve("Scripts").resolve("python.exe");
            if (!java.nio.file.Files.exists(pythonExe)) {
                System.out.println("[+] 检测到损坏的.venv，正在删除...");
                try {
                    deleteDirectory(venvDir.toFile());
                } catch (Exception e) {
                    System.err.println("[!] 删除.venv失败: " + e.getMessage());
                }
            }
        }
    }
    
    private static void deleteDirectory(File directory) throws IOException {
        if (directory.exists()) {
            File[] files = directory.listFiles();
            if (files != null) {
                for (File file : files) {
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

