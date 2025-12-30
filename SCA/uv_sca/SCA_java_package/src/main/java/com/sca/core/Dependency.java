package com.sca.core;

/**
 * 依赖包信息
 */
public class Dependency {
    private String name;
    private String version;
    private String packageType;
    
    public Dependency(String name, String version, String packageType) {
        this.name = name;
        this.version = version;
        this.packageType = packageType;
    }
    
    public String getName() {
        return name;
    }
    
    public String getVersion() {
        return version;
    }
    
    public String getPackageType() {
        return packageType;
    }
    
    @Override
    public String toString() {
        return String.format("%s@%s (%s)", name, version, packageType);
    }
}




