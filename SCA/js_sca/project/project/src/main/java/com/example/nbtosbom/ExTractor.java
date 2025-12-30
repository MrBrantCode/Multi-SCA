package com.example.nbtosbom;

import java.io.IOException;
import java.nio.file.Path;

public interface ExTractor {
    /**
     * 从指定的压缩包目录中提取目标文件（如 package-lock.json）
     *
     * @param zipDirPath 压缩包所在目录
     * @param outputDirPath 目标文件输出目录
     * @return 提取成功的文件列表路径
     * @throws IOException 读取或写入文件异常
     */
    Path[] extract(String zipDirPath, String outputDirPath) throws IOException;
}
