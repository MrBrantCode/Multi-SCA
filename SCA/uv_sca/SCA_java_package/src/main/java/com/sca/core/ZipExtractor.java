package com.sca.core;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;

/**
 * ZIP文件解压工具
 */
public class ZipExtractor {
    
    /**
     * 解压ZIP文件到临时目录
     */
    public static Path extract(String zipPath) throws IOException {
        File zipFile = new File(zipPath);
        if (!zipFile.exists()) {
            throw new IOException("ZIP文件不存在: " + zipPath);
        }
        
        // 创建临时目录
        Path tempDir = Files.createTempDirectory("uv_project_");
        
        try (ZipInputStream zis = new ZipInputStream(Files.newInputStream(zipFile.toPath()))) {
            ZipEntry entry;
            while ((entry = zis.getNextEntry()) != null) {
                String entryName = entry.getName();
                
                // 跳过空条目
                if (entryName == null || entryName.isEmpty()) {
                    continue;
                }
                
                // 规范化路径分隔符（Windows使用\，ZIP使用/）
                entryName = entryName.replace('\\', '/');
                
                Path entryPath = tempDir.resolve(entryName);
                
                // 防止ZIP路径遍历攻击
                Path normalizedEntry = entryPath.normalize();
                Path normalizedTemp = tempDir.normalize();
                if (!normalizedEntry.startsWith(normalizedTemp)) {
                    throw new IOException("非法的ZIP条目路径: " + entryName);
                }
                
                // 判断是否为目录（ZIP中目录条目以/结尾，或者isDirectory()返回true）
                boolean isDirectory = entry.isDirectory() || entryName.endsWith("/");
                
                if (isDirectory) {
                    // 创建目录（包括所有父目录）
                    Files.createDirectories(entryPath);
                } else {
                    // 确保父目录存在
                    Path parent = entryPath.getParent();
                    if (parent != null) {
                        Files.createDirectories(parent);
                    }
                    
                    // 写入文件
                    try (FileOutputStream fos = new FileOutputStream(entryPath.toFile())) {
                        byte[] buffer = new byte[8192];
                        int len;
                        while ((len = zis.read(buffer)) > 0) {
                            fos.write(buffer, 0, len);
                        }
                    }
                }
                zis.closeEntry();
            }
        }
        
        return tempDir;
    }
}

