package com.sca.core;

import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;

/**
 * PURL生成器
 */
public class PurlGenerator {
    
    /**
     * 根据依赖信息生成PURL列表
     */
    public static List<String> generate(List<Dependency> dependencies) {
        List<String> purlList = new ArrayList<>();
        
        for (Dependency dep : dependencies) {
            String purl = generatePurl(dep);
            purlList.add(purl);
        }
        
        return purlList;
    }
    
    /**
     * 生成单个PURL
     */
    private static String generatePurl(Dependency dep) {
        try {
            String encodedName = URLEncoder.encode(dep.getName(), StandardCharsets.UTF_8.toString())
                .replace("+", "%20");
            return String.format("pkg:%s/%s@%s", 
                dep.getPackageType(), encodedName, dep.getVersion());
        } catch (Exception e) {
            // 如果编码失败，使用原始名称
            return String.format("pkg:%s/%s@%s", 
                dep.getPackageType(), dep.getName(), dep.getVersion());
        }
    }
}




