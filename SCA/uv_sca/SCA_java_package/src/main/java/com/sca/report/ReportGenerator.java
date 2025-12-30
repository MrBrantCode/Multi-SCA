package com.sca.report;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonObject;
import com.google.gson.JsonArray;
import org.apache.commons.csv.CSVFormat;
import org.apache.commons.csv.CSVPrinter;

import java.io.FileWriter;
import java.io.IOException;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;

/**
 * 报告生成器
 */
public class ReportGenerator {
    
    private static final Gson gson = new GsonBuilder()
        .setPrettyPrinting()
        .disableHtmlEscaping()
        .create();
    
    /**
     * 生成控制台报告
     */
    public static void generateConsoleReport(List<Map<String, Object>> vulnerabilities, int purlCount) {
        System.out.println("\n" + "=".repeat(80));
        System.out.println("                   漏洞扫描报告");
        System.out.println("=".repeat(80));
        
        System.out.println("扫描时间: " + LocalDateTime.now()
            .format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss")));
        System.out.println("扫描包数量: " + purlCount);
        System.out.println("发现漏洞数量: " + vulnerabilities.size());
        System.out.println("-".repeat(80));
        
        if (vulnerabilities.isEmpty()) {
            System.out.println("✅ 未发现已知漏洞");
            return;
        }
        
        // 按严重程度分组
        Map<String, List<Map<String, Object>>> severityGroups = new HashMap<>();
        for (Map<String, Object> vuln : vulnerabilities) {
            String severity = (String) vuln.getOrDefault("severity", "UNKNOWN");
            severityGroups.computeIfAbsent(severity, k -> new ArrayList<>()).add(vuln);
        }
        
        // 输出严重程度统计
        System.out.println("漏洞严重程度统计:");
        String[] severities = {"CRITICAL", "HIGH", "MEDIUM", "LOW", "UNKNOWN", "NONE"};
        for (String severity : severities) {
            if (severityGroups.containsKey(severity)) {
                System.out.println("  " + severity + ": " + severityGroups.get(severity).size() + " 个");
            }
        }
        
        System.out.println("\n" + "=".repeat(80));
        System.out.println("                   漏洞详情");
        System.out.println("=".repeat(80));
        
        // 输出每个漏洞的详细信息
        for (int i = 0; i < vulnerabilities.size(); i++) {
            Map<String, Object> vuln = vulnerabilities.get(i);
            System.out.println("\n" + (i + 1) + ". [" + vuln.get("severity") + "] " + vuln.get("cve_id"));
            System.out.println("   组件: " + vuln.get("package_name") + " " + vuln.get("package_version"));
            System.out.println("   PURL: " + vuln.get("purl"));
            System.out.println("   内部ID: " + vuln.get("oss_id"));
            
            if (vuln.get("cvss_score") != null) {
                System.out.println("   CVSS v3分数: " + vuln.get("cvss_score"));
            }
            if (vuln.get("cvss_score_v2") != null) {
                System.out.println("   CVSS v2分数: " + vuln.get("cvss_score_v2"));
            }
            if (vuln.get("cvss_score_v4") != null) {
                System.out.println("   CVSS v4分数: " + vuln.get("cvss_score_v4"));
            }
            if (vuln.get("published_date") != null) {
                System.out.println("   发布日期: " + vuln.get("published_date"));
            }
            if (vuln.get("description") != null) {
                String desc = vuln.get("description").toString();
                if (desc.length() > 200) {
                    desc = desc.substring(0, 200) + "...";
                }
                System.out.println("   描述: " + desc);
            }
        }
    }
    
    /**
     * 生成JSON格式报告
     */
    public static void generateJsonReport(List<Map<String, Object>> vulnerabilities, String outputPath) 
            throws IOException {
        Map<String, Object> report = new HashMap<>();
        report.put("generated_at", LocalDateTime.now().toString());
        report.put("vulnerabilities_found", vulnerabilities.size());
        report.put("vulnerabilities", vulnerabilities);
        
        try (FileWriter writer = new FileWriter(outputPath)) {
            gson.toJson(report, writer);
        }
        
        System.out.println("[+] JSON报告已保存至: " + outputPath);
    }
    
    /**
     * 生成CSV格式报告
     */
    public static void generateCsvReport(List<Map<String, Object>> vulnerabilities, String outputPath) 
            throws IOException {
        if (vulnerabilities.isEmpty()) {
            System.out.println("[!] 没有漏洞数据可导出");
            return;
        }
        
        String[] headers = {
            "cve_id", "severity", "package_name", "package_version",
            "package_type", "oss_id", "cvss_score", "cvss_score_v2",
            "cvss_score_v4", "published_date", "description"
        };
        
        try (FileWriter writer = new FileWriter(outputPath);
             CSVPrinter csvPrinter = new CSVPrinter(writer, CSVFormat.DEFAULT.withHeader(headers))) {
            
            for (Map<String, Object> vuln : vulnerabilities) {
                List<Object> record = new ArrayList<>();
                for (String header : headers) {
                    Object value = vuln.getOrDefault(header, "");
                    record.add(value != null ? value : "");
                }
                csvPrinter.printRecord(record);
            }
        }
        
        System.out.println("[+] CSV报告已保存至: " + outputPath);
    }
    
    /**
     * 生成SBOM报告（CycloneDX格式）
     */
    public static void generateSbomReport(List<Map<String, Object>> vulnerabilities, 
                                          List<String> purlList, String outputPath) throws IOException {
        JsonObject sbom = new JsonObject();
        sbom.addProperty("bomFormat", "CycloneDX");
        sbom.addProperty("specVersion", "1.4");
        sbom.addProperty("serialNumber", "urn:uuid:" + UUID.randomUUID().toString());
        sbom.addProperty("version", 1);
        
        // Metadata
        JsonObject metadata = new JsonObject();
        metadata.addProperty("timestamp", LocalDateTime.now().toString());
        
        JsonArray tools = new JsonArray();
        JsonObject tool = new JsonObject();
        tool.addProperty("vendor", "SCA Tool");
        tool.addProperty("name", "uv-SCA-engine");
        tool.addProperty("version", "1.0");
        tools.add(tool);
        metadata.add("tools", tools);
        
        JsonObject component = new JsonObject();
        component.addProperty("type", "application");
        component.addProperty("name", "scanned-project");
        component.addProperty("version", "unknown");
        metadata.add("component", component);
        
        sbom.add("metadata", metadata);
        
        // Components
        JsonArray components = new JsonArray();
        Map<String, JsonObject> componentMap = new HashMap<>();
        
        for (String purl : purlList) {
            if (purl.startsWith("pkg:")) {
                String rest = purl.substring(4);
                String[] parts = rest.split("/");
                if (parts.length >= 2) {
                    String packageType = parts[0];
                    String nameVersion = parts[1];
                    String name, version;
                    if (nameVersion.contains("@")) {
                        String[] nv = nameVersion.split("@", 2);
                        name = nv[0];
                        version = nv[1];
                    } else {
                        name = nameVersion;
                        version = "unknown";
                    }
                    
                    JsonObject comp = new JsonObject();
                    comp.addProperty("type", "library");
                    comp.addProperty("bom-ref", purl);
                    comp.addProperty("name", name);
                    comp.addProperty("version", version);
                    comp.addProperty("purl", purl);
                    components.add(comp);
                    componentMap.put(purl, comp);
                }
            }
        }
        
        sbom.add("components", components);
        
        // Vulnerabilities
        if (!vulnerabilities.isEmpty()) {
            JsonArray vulnArray = new JsonArray();
            for (Map<String, Object> vuln : vulnerabilities) {
                JsonObject vulnObj = new JsonObject();
                vulnObj.addProperty("id", (String) vuln.getOrDefault("cve_id", "N/A"));
                
                JsonObject source = new JsonObject();
                source.addProperty("name", "CVE");
                source.addProperty("url", "https://cve.mitre.org/cgi-bin/cvename.cgi?name=" + 
                    vuln.getOrDefault("cve_id", ""));
                vulnObj.add("source", source);
                
                JsonArray ratings = new JsonArray();
                Object cvssV3 = vuln.get("cvss_score_v3");
                if (cvssV3 != null) {
                    JsonObject rating = new JsonObject();
                    JsonObject ratingSource = new JsonObject();
                    ratingSource.addProperty("name", "CVSSv3");
                    rating.add("source", ratingSource);
                    rating.addProperty("score", Double.parseDouble(cvssV3.toString()));
                    rating.addProperty("severity", (String) vuln.getOrDefault("severity", "UNKNOWN"));
                    ratings.add(rating);
                }
                vulnObj.add("ratings", ratings);
                
                vulnArray.add(vulnObj);
            }
            sbom.add("vulnerabilities", vulnArray);
        }
        
        try (FileWriter writer = new FileWriter(outputPath)) {
            gson.toJson(sbom, writer);
        }
        
        System.out.println("[+] SBOM报告已保存至: " + outputPath);
    }
}

