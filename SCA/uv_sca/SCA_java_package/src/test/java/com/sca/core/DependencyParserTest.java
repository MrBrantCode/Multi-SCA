package com.sca.core;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.DisplayName;
import static org.junit.jupiter.api.Assertions.*;

import java.util.List;

/**
 * DependencyParser 单元测试示例
 * 
 * 运行测试：
 * mvn test
 * 
 * 或者只运行这个测试：
 * mvn test -Dtest=DependencyParserTest
 */
@DisplayName("依赖解析器测试")
public class DependencyParserTest {
    
    @Test
    @DisplayName("应该能解析简单的依赖")
    public void testParseSimpleDependency() {
        // 准备测试数据
        String uvTreeOutput = "requests 2.31.0\n";
        
        // 执行测试
        List<Dependency> deps = DependencyParser.parse(uvTreeOutput);
        
        // 验证结果
        assertNotNull(deps, "解析结果不应该为null");
        assertEquals(1, deps.size(), "应该解析出1个依赖");
        assertEquals("requests", deps.get(0).getName(), "包名应该是requests");
        assertEquals("2.31.0", deps.get(0).getVersion(), "版本应该是2.31.0");
    }
    
    @Test
    @DisplayName("应该能解析多个依赖")
    public void testParseMultipleDependencies() {
        String uvTreeOutput = 
            "requests 2.31.0\n" +
            "urllib3 1.26.0\n" +
            "pillow 10.0.0\n";
        
        List<Dependency> deps = DependencyParser.parse(uvTreeOutput);
        
        assertEquals(3, deps.size(), "应该解析出3个依赖");
        assertEquals("requests", deps.get(0).getName());
        assertEquals("urllib3", deps.get(1).getName());
        assertEquals("pillow", deps.get(2).getName());
    }
    
    @Test
    @DisplayName("空输入应该返回空列表")
    public void testParseEmptyOutput() {
        List<Dependency> deps = DependencyParser.parse("");
        assertTrue(deps.isEmpty(), "空输入应该返回空列表");
    }
    
    @Test
    @DisplayName("null输入应该返回空列表或抛出异常")
    public void testParseNullInput() {
        // 根据你的实现，可能是返回空列表或抛出异常
        // 这里假设返回空列表
        List<Dependency> deps = DependencyParser.parse(null);
        assertTrue(deps.isEmpty(), "null输入应该返回空列表");
    }
    
    @Test
    @DisplayName("应该能处理带特殊字符的包名")
    public void testParseSpecialCharacters() {
        String uvTreeOutput = "package-name 1.0.0\n";
        List<Dependency> deps = DependencyParser.parse(uvTreeOutput);
        
        assertEquals(1, deps.size());
        assertEquals("package-name", deps.get(0).getName());
    }
}



