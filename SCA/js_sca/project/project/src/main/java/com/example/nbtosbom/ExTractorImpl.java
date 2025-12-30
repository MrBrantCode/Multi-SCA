package com.example.nbtosbom;

import java.io.IOException;
import java.nio.file.*;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.stream.Collectors;
import java.util.stream.Stream;
import java.util.logging.Logger;
import java.util.logging.ConsoleHandler;
import java.util.logging.SimpleFormatter;
import java.util.logging.LogRecord;
import java.util.zip.ZipInputStream;
import java.util.zip.ZipEntry;

public class ExTractorImpl implements ExTractor {

    private static final Logger logger = Logger.getLogger(ExTractorImpl.class.getName());
    private static final String[] TARGET_FILES = { "package-lock.json", "package_lock.json" };

    static {
        setupLogging();
    }

    private static void setupLogging() {
        ConsoleHandler handler = new ConsoleHandler();
        handler.setFormatter(new SimpleFormatter() {
            @Override
            public String format(LogRecord record) {
                return String.format("[%s] %s%n", record.getLevel(), record.getMessage());
            }
        });
        logger.addHandler(handler);
        logger.setUseParentHandlers(false);
    }

    @Override
    public Path[] extract(String zipDirPath, String outputDirPath) throws IOException {
        Path zipDir = Paths.get(zipDirPath);
        if (!Files.exists(zipDir)) throw new IOException("ZIP目录不存在: " + zipDirPath);

        Path outputDir = Paths.get(outputDirPath);
        Files.createDirectories(outputDir);

        Path zipFile = findSingleZipFile(zipDir);
        if (zipFile == null) return new Path[0];

        Path extractDir = extractZipFile(zipFile);
        if (extractDir == null) return new Path[0];

        List<Path> targetFiles = findAllTargetFiles(extractDir);
        if (targetFiles.isEmpty()) return new Path[0];

        return copyAllToOutput(targetFiles, outputDir);
    }

    private Path findSingleZipFile(Path dir) throws IOException {
        try (Stream<Path> paths = Files.list(dir)) {
            Path zipFile = paths.filter(Files::isRegularFile)
                    .filter(p -> p.toString().toLowerCase().endsWith(".zip"))
                    .findFirst()
                    .orElse(null);
            if (zipFile != null) logger.info("找到ZIP文件: " + zipFile.getFileName());
            return zipFile;
        }
    }

    private Path extractZipFile(Path zipFile) throws IOException {
        Path extractDir = Files.createTempDirectory("extract_");
        logger.info("开始解压到临时目录: " + extractDir);
        try (ZipInputStream zis = new ZipInputStream(Files.newInputStream(zipFile))) {
            ZipEntry entry;
            while ((entry = zis.getNextEntry()) != null) {
                Path entryPath = extractDir.resolve(entry.getName());
                if (entry.isDirectory()) Files.createDirectories(entryPath);
                else {
                    Files.createDirectories(entryPath.getParent());
                    Files.copy(zis, entryPath, StandardCopyOption.REPLACE_EXISTING);
                }
                zis.closeEntry();
            }
        }
        return extractDir;
    }

    private List<Path> findAllTargetFiles(Path dir) throws IOException {
        List<Path> result = new ArrayList<>();
        for (String target : TARGET_FILES) {
            try (Stream<Path> paths = Files.walk(dir)) {
                List<Path> matches = paths.filter(Files::isRegularFile)
                        .filter(p -> p.getFileName().toString().equals(target))
                        .sorted(Comparator.comparingInt(p -> p.getNameCount()))
                        .collect(Collectors.toList());
                if (!matches.isEmpty()) {
                    logger.info("找到目标文件: " + target + " 数量: " + matches.size());
                    result.addAll(matches);
                    break;
                }
            }
        }
        return result;
    }

    private Path[] copyAllToOutput(List<Path> files, Path outputDir) throws IOException {
        List<Path> copied = new ArrayList<>();
        for (int i = 0; i < files.size(); i++) {
            Path src = files.get(i);
            String numberedName = String.format("%s_%02d%s",
                    src.getFileName().toString().replaceAll("\\..*$",""),
                    i+1,
                    src.getFileName().toString().substring(src.getFileName().toString().lastIndexOf(".")));
            Path target = outputDir.resolve(numberedName);
            Files.copy(src, target, StandardCopyOption.REPLACE_EXISTING);
            logger.info("复制文件: " + target);
            copied.add(target);
        }
        return copied.toArray(new Path[0]);
    }
}
