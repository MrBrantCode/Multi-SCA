package com.example.nbtosbom;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;

import java.io.File;
import java.io.IOException;
import java.sql.*;
import java.util.*;
import java.util.logging.Level;
import java.util.logging.Logger;

public class SbomVulnEnricher {
    private static final ObjectMapper mapper = new ObjectMapper();
    private static final Logger logger = Logger.getLogger(SbomVulnEnricher.class.getName());

    // DB connection settings
    private final String jdbcUrl;
    private final String dbUser;
    private final String dbPass;

    public SbomVulnEnricher(String host, String database, String user, String pass) {
        this.jdbcUrl = String.format("jdbc:mysql://%s/%s", host, database);
        this.dbUser = user;
        this.dbPass = pass;
    }

    /**
     * High level API method. Reads inputPath, enriches, writes outputPath.
     */
    public void enrich(String inputPath, String outputPath) throws Exception {
        JsonNode root = mapper.readTree(new File(inputPath));

        ArrayNode components = (ArrayNode) root.path("components");
        if (components == null) {
            throw new IllegalArgumentException("Input SBOM doesn't contain a components array");
        }

        // Map purl -> set of CVEs
        Map<String, Set<String>> purlToCves = new LinkedHashMap<>();

        try (Connection conn = DriverManager.getConnection(jdbcUrl, dbUser, dbPass)) {
            for (JsonNode comp : components) {
                String purl = getOrBuildPurl(comp);
                if (purl == null) continue; // skip components we couldn't build purl for

                Set<String> cves = queryVulnerabilitiesForPurl(conn, purl);
                if (!cves.isEmpty()) {
                    purlToCves.put(purl, cves);
                }
            }
        }

        // Build vulnerabilities array in CycloneDX minimal structure
        ArrayNode vulnsArray = mapper.createArrayNode();
        int vulnCounter = 1;
        for (Map.Entry<String, Set<String>> e : purlToCves.entrySet()) {
            String purl = e.getKey();
            for (String cve : e.getValue()) {
                ObjectNode vuln = mapper.createObjectNode();
                // ID: prefer CVE as id
                vuln.put("id", cve);
                // short desc / source
                vuln.put("description", "Imported from internal DB via purl mapping");
                vuln.put("source", "internal-db");

                // affects
                ArrayNode affects = mapper.createArrayNode();
                ObjectNode aff = mapper.createObjectNode();
                aff.put("ref", purl);
                affects.add(aff);
                vuln.set("affects", affects);

                vulnsArray.add(vuln);
                vulnCounter++;
            }
        }

        // Attach vulnerabilities to the root and write out
        ObjectNode outRoot;
        if (root instanceof ObjectNode) {
            outRoot = (ObjectNode) root.deepCopy();
        } else {
            outRoot = mapper.createObjectNode();
            outRoot.setAll((ObjectNode) root);
        }
        outRoot.set("vulnerabilities", vulnsArray);

        mapper.writerWithDefaultPrettyPrinter().writeValue(new File(outputPath), outRoot);
    }

    /**
     * Try to get an existing purl field or build one using common heuristics.
     */
    private String getOrBuildPurl(JsonNode comp) {
        // If there's a purl already in the component, use it
        JsonNode purlNode = comp.get("purl");
        if (purlNode != null && !purlNode.asText().isEmpty()) return purlNode.asText();

        String type = comp.path("type").asText(null);
        String name = comp.path("name").asText(null);
        String version = comp.path("version").asText(null);

        if (name == null || version == null) return null;

        // Common ecosystems heuristics
        if ("library".equalsIgnoreCase(type)) {
            // Guess by looking at name patterns
            if (name.contains("@") || name.contains("/")) {
                // might be npm scoped or path-like; default to npm
                return String.format("pkg:npm/%s@%s", name, version);
            }
            // fallback: try maven if name looks like group:artifact
            if (name.contains(":")) {
                String[] parts = name.split(":", 2);
                return String.format("pkg:maven/%s/%s@%s", parts[0], parts[1], version);
            }
            // default to npm
            return String.format("pkg:npm/%s@%s", name, version);
        }

        // Some components include an "ecosystem" or "purl"-like info
        JsonNode ext = comp.get("properties");
        if (ext != null && ext.isArray()) {
            for (JsonNode prop : ext) {
                String nameProp = prop.path("name").asText(null);
                String val = prop.path("value").asText(null);
                if ("ecosystem".equalsIgnoreCase(nameProp) && val != null) {
                    switch (val.toLowerCase()) {
                        case "npm":
                            return String.format("pkg:npm/%s@%s", name, version);
                        case "maven":
                        case "mvn":
                            // attempt to parse name as group:artifact
                            if (name.contains(":")) {
                                String[] parts = name.split(":", 2);
                                return String.format("pkg:maven/%s/%s@%s", parts[0], parts[1], version);
                            }
                            return String.format("pkg:maven/%s@%s", name, version);
                        case "pypi":
                            return String.format("pkg:pypi/%s@%s", name, version);
                        case "nuget":
                            return String.format("pkg:nuget/%s@%s", name, version);
                    }
                }
            }
        }

        // Last resort: a generic package purl
        return String.format("pkg:generic/%s@%s", name, version);
    }


    private Set<String> queryVulnerabilitiesForPurl(Connection conn, String purl) {
    logger.info("当前数据库：" + jdbcUrl);
    logger.info("查询 purl: " + purl);

    Set<String> result = new LinkedHashSet<>();

    // 使用已知正确的列名
    String q1 = "SELECT pk_oss_id FROM t_oss_id_purl_map WHERE pk_purl = ?";
    String q2 = "SELECT cve_id FROM t_origin_vulnerability WHERE oss_id = ?";

    try (PreparedStatement ps1 = conn.prepareStatement(q1)) {
        ps1.setString(1, purl);
        try (ResultSet rs1 = ps1.executeQuery()) {
            while (rs1.next()) {
                String ossId = rs1.getString("pk_oss_id");
                if (ossId == null || ossId.isEmpty()) continue;

                try (PreparedStatement ps2 = conn.prepareStatement(q2)) {
                    ps2.setString(1, ossId);
                    try (ResultSet rs2 = ps2.executeQuery()) {
                        while (rs2.next()) {
                            String cve = rs2.getString("cve_id");
                            if (cve != null && !cve.isEmpty()) result.add(cve);
                        }
                    }
                }
            }
        }
    } catch (SQLException ex) {
        logger.log(Level.WARNING, "SQL 查询出错（purl=" + purl + "）: " + ex.getMessage(), ex);
    }

    return result;
    }

}
