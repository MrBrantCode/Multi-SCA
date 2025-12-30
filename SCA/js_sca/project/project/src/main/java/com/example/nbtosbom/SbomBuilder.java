package com.example.nbtosbom;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;

import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.HashSet;
import java.util.Iterator;
import java.util.Map;

public class SbomBuilder {
    private final ObjectMapper mapper;

    public SbomBuilder(ObjectMapper mapper) {
        this.mapper = mapper;
    }

    public ObjectNode build(JsonNode lockJson, String sourceRef) {
        ObjectNode root = mapper.createObjectNode();
        root.put("bomFormat", "CycloneDX");
        root.put("specVersion", "1.4");
        root.put("version", 1);

        // 构建 metadata
        ObjectNode metadata = mapper.createObjectNode();
        ObjectNode mainComponent = mapper.createObjectNode();
        mainComponent.put("type", "application");
        mainComponent.put("name", lockJson.path("name").asText("unknown"));
        mainComponent.put("version", lockJson.path("version").asText("0.0.0"));

        if (lockJson.has("packages") && lockJson.get("packages").has("")) {
            JsonNode rootPkg = lockJson.get("packages").get("");
            if (rootPkg.has("license")) {
                ArrayNode licenses = mapper.createArrayNode();
                ObjectNode lic = mapper.createObjectNode();
                ObjectNode spdx = mapper.createObjectNode();
                spdx.put("id", rootPkg.get("license").asText());
                lic.set("license", spdx);
                licenses.add(lic);
                mainComponent.set("licenses", licenses);
            }
        }

        metadata.set("component", mainComponent);
        metadata.put("generatedFrom", sourceRef);
        root.set("metadata", metadata);

        // 构建 components
        ArrayNode components = mapper.createArrayNode();
        HashSet<String> seenPurls = new HashSet<>();

        if (lockJson.has("packages") && lockJson.get("packages").isObject()) {
            Iterator<Map.Entry<String, JsonNode>> it = lockJson.get("packages").fields();
            while (it.hasNext()) {
                Map.Entry<String, JsonNode> e = it.next();
                String pkgPath = e.getKey();
                JsonNode pkgInfo = e.getValue();
                if (pkgPath == null || pkgPath.isEmpty()) continue;
                String name = pkgInfo.has("name") ? pkgInfo.get("name").asText() : pkgPath.replaceFirst("^node_modules/", "");
                String version = pkgInfo.has("version") ? pkgInfo.get("version").asText(null) : null;
                addComponentIfValid(components, seenPurls, name, version, pkgInfo);
            }
        }

        root.set("components", components);
        return root;
    }

    private void addComponentIfValid(ArrayNode components, HashSet<String> seenPurls,
                                     String name, String version, JsonNode info) {
        if (name == null || name.isBlank() || version == null || version.isBlank()) return;
        String purl = makeNpmPurl(name, version);
        if (seenPurls.contains(purl)) return;
        seenPurls.add(purl);

        ObjectNode comp = mapper.createObjectNode();
        comp.put("type", "library");
        comp.put("name", name);
        comp.put("version", version);
        comp.put("purl", purl);

        // license
        if (info != null && info.has("license")) {
            ArrayNode licenses = mapper.createArrayNode();
            ObjectNode lic = mapper.createObjectNode();
            ObjectNode spdx = mapper.createObjectNode();
            spdx.put("id", info.get("license").asText());
            lic.set("license", spdx);
            licenses.add(lic);
            comp.set("licenses", licenses);
        }

        // externalReferences
        ArrayNode extRefs = mapper.createArrayNode();
        if (info != null && info.has("resolved")) {
            ObjectNode dist = mapper.createObjectNode();
            dist.put("type", "distribution");
            dist.put("url", info.get("resolved").asText());
            extRefs.add(dist);
        }
        if (info != null && info.has("funding") && info.get("funding").has("url")) {
            ObjectNode fund = mapper.createObjectNode();
            fund.put("type", "funding");
            fund.put("url", info.get("funding").get("url").asText());
            extRefs.add(fund);
        }
        if (extRefs.size() > 0) {
            comp.set("externalReferences", extRefs);
        }

        // integrity
        if (info != null && info.has("integrity")) {
            comp.put("integrity", info.get("integrity").asText());
        }

        components.add(comp);
    }

    private String makeNpmPurl(String name, String version) {
    if (name == null) name = "";
    String encodedName = URLEncoder.encode(name, StandardCharsets.UTF_8);
    encodedName = encodedName.replace("%2F", "/");
    encodedName = encodedName.replace("+", "%20");

    String encodedVersion = URLEncoder.encode(version == null ? "" : version, StandardCharsets.UTF_8)
            .replace("+", "%20");

    return "pkg:npm/" + encodedName + "@" + encodedVersion;
}
}
