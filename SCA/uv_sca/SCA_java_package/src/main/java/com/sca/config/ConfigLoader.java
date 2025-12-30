package com.sca.config;

import java.io.InputStream;
import java.util.Properties;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * 配置加载器 - 解决硬编码密码问题
 * 
 * 使用方法：
 * 1. 创建 src/main/resources/config.properties 文件
 * 2. 在文件中写入配置（不要提交到Git）
 * 3. 在 .gitignore 中添加 config.properties
 */
public class ConfigLoader {
    private static final Logger logger = LoggerFactory.getLogger(ConfigLoader.class);
    private static Properties props;
    
    static {
        loadConfig();
    }
    
    private static void loadConfig() {
        props = new Properties();
        try (InputStream is = ConfigLoader.class
                .getResourceAsStream("/config.properties")) {
            
            if (is == null) {
                // 如果配置文件不存在，尝试从环境变量读取
                loadFromEnvironment();
                return;
            }
            
            props.load(is);
            logger.info("[+] 成功加载配置文件");
        } catch (Exception e) {
            logger.warn("[!] 加载配置文件失败，尝试从环境变量读取");
            loadFromEnvironment();
        }
    }
    
    private static void loadFromEnvironment() {
        props = new Properties();
        // 从环境变量读取
        props.setProperty("db.host", 
            System.getenv().getOrDefault("SCA_DB_HOST", "10.176.37.194"));
        props.setProperty("db.name", 
            System.getenv().getOrDefault("SCA_DB_NAME", "osschain_bachelor"));
        props.setProperty("db.user", 
            System.getenv().getOrDefault("SCA_DB_USER", "u_bachelor"));
        props.setProperty("db.password", 
            System.getenv().getOrDefault("SCA_DB_PASSWORD", ""));
        
        if (props.getProperty("db.password").isEmpty()) {
            throw new RuntimeException(
                "数据库密码未设置！请设置环境变量 SCA_DB_PASSWORD 或创建配置文件");
        }
    }
    
    public static String getDbHost() {
        return props.getProperty("db.host");
    }
    
    public static String getDbName() {
        return props.getProperty("db.name");
    }
    
    public static String getDbUser() {
        return props.getProperty("db.user");
    }
    
    public static String getDbPassword() {
        return props.getProperty("db.password");
    }
}

