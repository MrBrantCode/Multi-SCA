"""
存在漏洞依赖的测试程序
"""
import requests
import urllib3
from jinja2 import Template
import django
from PIL import Image
import io


def test_requests():
    """测试requests功能"""
    print("Testing requests...")
    try:
        # 使用存在漏洞的requests版本
        response = requests.get('https://httpbin.org/get')
        print(f"Requests version: {requests.__version__}")
        print(f"Status code: {response.status_code}")
    except Exception as e:
        print(f"Requests error: {e}")


def test_urllib3():
    """测试urllib3功能"""
    print("\nTesting urllib3...")
    try:
        http = urllib3.PoolManager()
        response = http.request('GET', 'https://httpbin.org/get')
        print(f"Urllib3 version: {urllib3.__version__}")
        print(f"Status: {response.status}")
    except Exception as e:
        print(f"Urllib3 error: {e}")


def test_jinja2():
    """测试Jinja2模板渲染"""
    print("\nTesting Jinja2...")
    try:
        template = Template("Hello {{ name }}!")
        result = template.render(name="World")
        print(f"Jinja2 version: {__import__('jinja2').__version__}")
        print(f"Template result: {result}")
    except Exception as e:
        print(f"Jinja2 error: {e}")


def test_django():
    """测试Django相关功能"""
    print("\nTesting Django...")
    try:
        print(f"Django version: {django.get_version()}")
        # 简单的Django配置检查
        from django.conf import settings
        if not settings.configured:
            settings.configure(
                DEBUG=True,
                SECRET_KEY='test-key-for-vulnerable-version'
            )
        print("Django configured successfully")
    except Exception as e:
        print(f"Django error: {e}")


def test_pillow():
    """测试Pillow图像处理"""
    print("\nTesting Pillow...")
    try:
        # 创建一个简单的测试图像
        img = Image.new('RGB', (100, 100), color='red')
        print(f"Pillow version: {PIL.__version__}")
        print(f"Image size: {img.size}")
        
        # 保存到内存
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        print("Image created successfully")
    except Exception as e:
        print(f"Pillow error: {e}")


def main():
    """主函数"""
    print("=" * 50)
    print("漏洞依赖测试程序")
    print("=" * 50)
    
    print("已知漏洞信息:")
    print("- requests==2.20.0: CVE-2018-18074 (信息泄露)")
    print("- urllib3==1.21.1: CVE-2018-20060 (CRLF注入)")
    print("- jinja2==2.10.1: CVE-2019-10906 (XSS漏洞)")
    print("- django==1.11.29: 多个CVE漏洞")
    print("- pillow==5.4.1: CVE-2019-16865 (DoS漏洞)")
    print("=" * 50)
    
    # 运行测试
    test_requests()
    test_urllib3()
    test_jinja2()
    test_django()
    test_pillow()
    
    print("\n" + "=" * 50)
    print("测试完成!")
    print("请使用SCA工具扫描此项目的zip文件检测漏洞")
    print("=" * 50)


if __name__ == "__main__":
    main()