package com.example.nbtosbom;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;

import java.io.File;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.UUID;
import java.util.logging.Logger;

public class Main {

    private static final Logger logger = Logger.getLogger(Main.class.getName());

    public static void main(String[] args) {
        String first = args != null && args.length >= 1 ? args[0] : null;
        String outputSbom = args != null && args.length >= 2 ? args[1] : "sbom.json";
        String outputEnriched = args != null && args.length >= 3 ? args[2] : "sbom-enriched.json";

        if (first == null) {
            System.err.println("请提供输入：要么是 package-lock.json 的路径，要么是包含 ZIP 的目录/ZIP 文件路径。");
            System.exit(2);
        }

        try {
            Path lockFilePath;

            Path candidate = Paths.get(first);

            // logger.info("是否存在：" + Files.exists(candidate));
            // logger.info("是否为文件：" + Files.isRegularFile(candidate));
            logger.info("扩展名：" + (candidate.getFileName() != null ? candidate.getFileName().toString() : "无文件名"));

            if (Files.exists(candidate) && Files.isRegularFile(candidate) && first.toLowerCase().endsWith(".json")) {
                // 直接给定了 json（假定为锁文件）
                lockFilePath = candidate;
                logger.info("直接使用输入的 json 文件: " + lockFilePath.toAbsolutePath());
            } else {
                // 当作 ZIP 目录或 ZIP 文件处理：调用 ExTractorImpl
                ExTractor extractor = new ExTractorImpl();
                Path tempOut = Files.createTempDirectory("extracted_locks_out_");
                Path[] extracted = extractor.extract(first, tempOut.toString());
                if (extracted == null || extracted.length == 0) {
                    throw new IOException("未从 ZIP 中提取到锁文件");
                }
                lockFilePath = extracted[0];
                logger.info("选用提取出的锁文件: " + lockFilePath.toAbsolutePath());
            }

            ObjectMapper mapper = new ObjectMapper();
            JsonNode lockJson = mapper.readTree(lockFilePath.toFile());

            SbomBuilder builder = new SbomBuilder(mapper);
            ObjectNode sbom = builder.build(lockJson, lockFilePath.toAbsolutePath().toString());

            if (!sbom.has("serialNumber")) {
                sbom.put("serialNumber", "urn:uuid:" + UUID.randomUUID());
            }

            mapper.writerWithDefaultPrettyPrinter().writeValue(new File(outputSbom), sbom);
            System.out.println("SBOM物料清单 已生成: " + new File(outputSbom).getAbsolutePath());

//          Todo
            String host = System.getenv().getOrDefault("SBOM_DB_HOST", "10.176.37.194");
            String database = System.getenv().getOrDefault("SBOM_DB_NAME", "osschain_bachelor");

            SbomVulnEnricher enricher = new SbomVulnEnricher(host, database, "u_bachelor", "bachelor12345");
            enricher.enrich(outputSbom, outputEnriched);

            System.out.println("带漏洞信息的 SBOM 文件 已生成: " + new File(outputEnriched).getAbsolutePath());
            System.exit(0);

        } catch (Exception e) {
            System.err.println("处理失败: " + e.getMessage());
            e.printStackTrace();
            System.exit(1);
        }
    }
}
