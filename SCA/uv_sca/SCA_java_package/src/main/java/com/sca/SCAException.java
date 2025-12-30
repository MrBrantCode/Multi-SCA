package com.sca;

/**
 * SCA工具自定义异常基类
 * 用于区分不同类型的错误，提供更好的错误处理
 */
public class SCAException extends Exception {
    
    public SCAException(String message) {
        super(message);
    }
    
    public SCAException(String message, Throwable cause) {
        super(message, cause);
    }
}



