package com.sca.core;

import java.io.IOException;
import java.nio.file.FileVisitResult;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.SimpleFileVisitor;
import java.nio.file.attribute.BasicFileAttributes;

/**
 * 查找uv项目目录
 */
public class ProjectFinder {
    
    /**
     * 查找包含pyproject.toml或uv.lock的目录
     */
    public static Path findUvProject(Path baseDir) throws IOException {
        UvProjectFinder visitor = new UvProjectFinder();
        Files.walkFileTree(baseDir, visitor);
        return visitor.getProjectDir();
    }
    
    private static class UvProjectFinder extends SimpleFileVisitor<Path> {
        private Path projectDir = null;
        
        @Override
        public FileVisitResult visitFile(Path file, BasicFileAttributes attrs) {
            String fileName = file.getFileName().toString();
            if ("pyproject.toml".equals(fileName) || "uv.lock".equals(fileName)) {
                projectDir = file.getParent();
                return FileVisitResult.TERMINATE;
            }
            return FileVisitResult.CONTINUE;
        }
        
        public Path getProjectDir() {
            return projectDir;
        }
    }
}




