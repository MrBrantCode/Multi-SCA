package com.sca.util;

import java.io.File;

/**
 * 输入验证工具类
 * 验证用户输入的文件路径、格式等
 */
public class InputValidator {
    
    /**
     * 验证ZIP文件路径
     * 
     * @param zipPath ZIP文件路径
     * @throws IllegalArgumentException 如果验证失败
     */
    public static void validateZipFile(String zipPath) {
        if (zipPath == null || zipPath.trim().isEmpty()) {
            throw new IllegalArgumentException("ZIP文件路径不能为空");
        }
        
        File file = new File(zipPath);
        
        // 1. 检查文件是否存在
        if (!file.exists()) {
            throw new IllegalArgumentException("文件不存在: " + zipPath);
        }
        
        // 2. 检查是否是文件（不是目录）
        if (!file.isFile()) {
            throw new IllegalArgumentException("路径不是文件: " + zipPath);
        }
        
        // 3. 检查文件扩展名
        String fileName = file.getName().toLowerCase();
        if (!fileName.endsWith(".zip")) {
            throw new IllegalArgumentException("文件必须是ZIP格式: " + zipPath);
        }
        
        // 4. 检查文件大小（最大100MB）
        long maxSize = 100 * 1024 * 1024; // 100MB
        if (file.length() > maxSize) {
            throw new IllegalArgumentException(
                String.format("文件太大: %.2f MB，最大支持100MB", 
                    file.length() / 1024.0 / 1024.0));
        }
        
        // 5. 检查文件是否可读
        if (!file.canRead()) {
            throw new IllegalArgumentException("文件不可读: " + zipPath);
        }
    }
    
}



