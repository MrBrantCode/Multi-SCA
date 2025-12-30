package com.sca.core;

import java.util.ArrayList;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * 解析uv tree输出
 */
public class DependencyParser {
    
    private static final Pattern DEPENDENCY_PATTERN = 
        Pattern.compile("^[├└│┊\\s]*(?:──\\s+)?([a-zA-Z0-9_\\-\\.]+)\\s+([vw]?[\\d\\.]+[a-zA-Z0-9_\\-\\.]*)$");
    
    /**
     * 解析uv tree输出，提取依赖信息
     */
    public static List<Dependency> parse(String output) {
        List<Dependency> dependencies = new ArrayList<>();
        
        if (output == null || output.trim().isEmpty()) {
            return dependencies;
        }
        
        String[] lines = output.split("\n");
        for (String line : lines) {
            line = line.trim();
            
            // 跳过空行、注释行、项目根目录行
            if (line.isEmpty() || 
                line.startsWith("#") || 
                line.contains("->") ||
                line.matches("^\\w+\\s+v[\\d\\.]")) {
                continue;
            }
            
            // 尝试匹配包名和版本
            Matcher matcher = DEPENDENCY_PATTERN.matcher(line);
            if (matcher.matches()) {
                String packageName = matcher.group(1);
                String version = matcher.group(2);
                
                // 跳过Python本身和uv的条目
                if ("python".equals(packageName) || "uv".equals(packageName)) {
                    continue;
                }
                
                // 如果版本号以v开头，去掉v
                if (version.startsWith("v")) {
                    version = version.substring(1);
                }
                
                dependencies.add(new Dependency(packageName, version, "pypi"));
            }
        }
        
        return dependencies;
    }
}




