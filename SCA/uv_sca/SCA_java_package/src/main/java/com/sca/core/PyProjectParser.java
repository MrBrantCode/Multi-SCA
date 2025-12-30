package com.sca.core;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * 从pyproject.toml解析依赖（网络错误时的fallback）
 */
public class PyProjectParser {
    
    /**
     * 从pyproject.toml解析依赖
     * 只解析精确版本号的依赖（如 requests==2.20.0）
     */
    public static List<Dependency> parse(Path projectDir) {
        Path pyprojectPath = projectDir.resolve("pyproject.toml");
        if (!Files.exists(pyprojectPath)) {
            return new ArrayList<>();
        }
        
        List<Dependency> dependencies = new ArrayList<>();
        
        try {
            String content = new String(Files.readAllBytes(pyprojectPath), "UTF-8");
            
            // 查找 [project] 部分的 dependencies
            // 使用正则表达式匹配 dependencies = ["package==version", ...]
            Pattern depsPattern = Pattern.compile("dependencies\\s*=\\s*\\[(.*?)\\]", Pattern.DOTALL);
            Matcher depsMatcher = depsPattern.matcher(content);
            
            if (!depsMatcher.find()) {
                return new ArrayList<>();
            }
            
            String depsText = depsMatcher.group(1);
            // 匹配 "package==version" 或 'package==version'
            Pattern depPattern = Pattern.compile("[\"']([^\"']+)[\"']");
            Matcher depMatcher = depPattern.matcher(depsText);
            
            while (depMatcher.find()) {
                String depStr = depMatcher.group(1);
                // 只提取精确版本（==）
                if (depStr.contains("==")) {
                    String[] parts = depStr.split("==");
                    if (parts.length == 2) {
                        String packageName = parts[0].trim();
                        String version = parts[1].trim();
                        dependencies.add(new Dependency(packageName, version, "pypi"));
                    }
                }
            }
            
            if (!dependencies.isEmpty()) {
                System.out.println("[+] 从pyproject.toml解析到 " + dependencies.size() + " 个依赖（精确版本）");
            }
            
        } catch (IOException e) {
            System.err.println("[!] 解析pyproject.toml失败: " + e.getMessage());
        } catch (Exception e) {
            System.err.println("[!] 解析pyproject.toml时出错: " + e.getMessage());
        }
        
        return dependencies;
    }
}




