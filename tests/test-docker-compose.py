#!/usr/bin/env python3
"""
Docker Compose 配置测试脚本
测试单体容器和微服务架构的配置正确性
"""

import os
import sys
import yaml
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Any

class DockerComposeTester:
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.compose_files = {
            'monolithic': 'docker-compose.yml',
            'microservices': 'docker-compose.microservices.yml'
        }
        
    def test_compose_file_syntax(self, compose_file: str) -> bool:
        """测试Docker Compose文件语法"""
        try:
            file_path = self.project_root / compose_file
            if not file_path.exists():
                print(f"❌ 文件不存在: {compose_file}")
                return False
                
            # 验证YAML语法
            with open(file_path, 'r', encoding='utf-8') as f:
                yaml.safe_load(f)
            
            # 验证Docker Compose语法
            result = subprocess.run(
                ['docker-compose', '-f', str(file_path), 'config'],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            
            if result.returncode == 0:
                print(f"✅ {compose_file} 语法正确")
                return True
            else:
                print(f"❌ {compose_file} 语法错误:")
                print(result.stderr)
                return False
                
        except Exception as e:
            print(f"❌ 测试 {compose_file} 时出错: {e}")
            return False
    
    def test_service_dependencies(self, compose_file: str) -> bool:
        """测试服务依赖关系"""
        try:
            file_path = self.project_root / compose_file
            with open(file_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            services = config.get('services', {})
            errors = []
            
            for service_name, service_config in services.items():
                depends_on = service_config.get('depends_on', [])
                if isinstance(depends_on, list):
                    for dependency in depends_on:
                        if dependency not in services:
                            errors.append(f"服务 {service_name} 依赖不存在的服务: {dependency}")
                elif isinstance(depends_on, dict):
                    for dependency in depends_on.keys():
                        if dependency not in services:
                            errors.append(f"服务 {service_name} 依赖不存在的服务: {dependency}")
            
            if errors:
                print(f"❌ {compose_file} 依赖关系错误:")
                for error in errors:
                    print(f"  - {error}")
                return False
            else:
                print(f"✅ {compose_file} 依赖关系正确")
                return True
                
        except Exception as e:
            print(f"❌ 测试 {compose_file} 依赖关系时出错: {e}")
            return False
    
    def test_environment_variables(self, compose_file: str) -> bool:
        """测试环境变量配置"""
        try:
            file_path = self.project_root / compose_file
            with open(file_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            services = config.get('services', {})
            required_vars = {
                'backend': ['API_KEY', 'API_URL', 'API_MODEL'],
                'app': ['API_KEY', 'API_URL', 'API_MODEL']
            }
            
            errors = []
            for service_name, service_config in services.items():
                if service_name in required_vars:
                    env = service_config.get('environment', [])
                    env_dict = {}
                    
                    # 转换环境变量列表为字典
                    for item in env:
                        if isinstance(item, str) and '=' in item:
                            key, value = item.split('=', 1)
                            env_dict[key] = value
                    
                    # 检查必需的环境变量
                    for required_var in required_vars[service_name]:
                        if required_var not in env_dict and not any(
                            f"${{{required_var}}}" in str(env) for env in env
                        ):
                            errors.append(f"服务 {service_name} 缺少必需环境变量: {required_var}")
            
            if errors:
                print(f"❌ {compose_file} 环境变量配置错误:")
                for error in errors:
                    print(f"  - {error}")
                return False
            else:
                print(f"✅ {compose_file} 环境变量配置正确")
                return True
                
        except Exception as e:
            print(f"❌ 测试 {compose_file} 环境变量时出错: {e}")
            return False
    
    def test_port_configurations(self, compose_file: str) -> bool:
        """测试端口配置"""
        try:
            file_path = self.project_root / compose_file
            with open(file_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            services = config.get('services', {})
            used_ports = set()
            errors = []
            
            for service_name, service_config in services.items():
                ports = service_config.get('ports', [])
                for port_mapping in ports:
                    if isinstance(port_mapping, str):
                        host_port = port_mapping.split(':')[0]
                    else:
                        host_port = str(port_mapping[0])
                    
                    if host_port in used_ports:
                        errors.append(f"端口冲突: {host_port} 被多个服务使用")
                    else:
                        used_ports.add(host_port)
            
            if errors:
                print(f"❌ {compose_file} 端口配置错误:")
                for error in errors:
                    print(f"  - {error}")
                return False
            else:
                print(f"✅ {compose_file} 端口配置正确")
                return True
                
        except Exception as e:
            print(f"❌ 测试 {compose_file} 端口配置时出错: {e}")
            return False
    
    def test_volume_configurations(self, compose_file: str) -> bool:
        """测试卷配置"""
        try:
            file_path = self.project_root / compose_file
            with open(file_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            services = config.get('services', {})
            errors = []
            
            for service_name, service_config in services.items():
                volumes = service_config.get('volumes', [])
                for volume in volumes:
                    if isinstance(volume, str) and ':' in volume:
                        host_path = volume.split(':')[0]
                        if host_path.startswith('./') or host_path.startswith('/'):
                            # 检查主机路径是否存在（对于相对路径）
                            if host_path.startswith('./'):
                                full_path = self.project_root / host_path[2:]
                                if not full_path.exists():
                                    errors.append(f"服务 {service_name} 挂载的主机路径不存在: {host_path}")
            
            if errors:
                print(f"❌ {compose_file} 卷配置错误:")
                for error in errors:
                    print(f"  - {error}")
                return False
            else:
                print(f"✅ {compose_file} 卷配置正确")
                return True
                
        except Exception as e:
            print(f"❌ 测试 {compose_file} 卷配置时出错: {e}")
            return False
    
    def test_health_checks(self, compose_file: str) -> bool:
        """测试健康检查配置"""
        try:
            file_path = self.project_root / compose_file
            with open(file_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            services = config.get('services', {})
            errors = []
            
            for service_name, service_config in services.items():
                healthcheck = service_config.get('healthcheck', {})
                if healthcheck:
                    test_cmd = healthcheck.get('test', [])
                    if not test_cmd:
                        errors.append(f"服务 {service_name} 健康检查缺少测试命令")
                    
                    interval = healthcheck.get('interval', '30s')
                    timeout = healthcheck.get('timeout', '10s')
                    retries = healthcheck.get('retries', 3)
                    
                    # 验证时间格式
                    try:
                        if isinstance(interval, str):
                            int(interval.replace('s', ''))
                        if isinstance(timeout, str):
                            int(timeout.replace('s', ''))
                    except ValueError:
                        errors.append(f"服务 {service_name} 健康检查时间格式错误")
            
            if errors:
                print(f"❌ {compose_file} 健康检查配置错误:")
                for error in errors:
                    print(f"  - {error}")
                return False
            else:
                print(f"✅ {compose_file} 健康检查配置正确")
                return True
                
        except Exception as e:
            print(f"❌ 测试 {compose_file} 健康检查时出错: {e}")
            return False
    
    def run_all_tests(self) -> Dict[str, bool]:
        """运行所有测试"""
        print("🚀 开始Docker Compose配置测试")
        print("=" * 50)
        
        results = {}
        
        for config_type, compose_file in self.compose_files.items():
            print(f"\n📋 测试 {config_type} 配置: {compose_file}")
            print("-" * 40)
            
            tests = [
                self.test_compose_file_syntax,
                self.test_service_dependencies,
                self.test_environment_variables,
                self.test_port_configurations,
                self.test_volume_configurations,
                self.test_health_checks
            ]
            
            config_results = []
            for test in tests:
                result = test(compose_file)
                config_results.append(result)
            
            results[config_type] = all(config_results)
            
            if results[config_type]:
                print(f"✅ {config_type} 配置测试通过")
            else:
                print(f"❌ {config_type} 配置测试失败")
        
        return results
    
    def generate_test_report(self, results: Dict[str, bool]):
        """生成测试报告"""
        print("\n" + "=" * 50)
        print("📊 测试报告")
        print("=" * 50)
        
        total_configs = len(results)
        passed_configs = sum(1 for result in results.values() if result)
        
        print(f"总配置数: {total_configs}")
        print(f"通过配置: {passed_configs}")
        print(f"失败配置: {total_configs - passed_configs}")
        print(f"通过率: {passed_configs/total_configs*100:.1f}%")
        
        print("\n详细结果:")
        for config_type, result in results.items():
            status = "✅ 通过" if result else "❌ 失败"
            print(f"  {config_type}: {status}")
        
        if all(results.values()):
            print("\n🎉 所有配置测试通过！")
            return True
        else:
            print("\n⚠️  部分配置测试失败，请检查上述错误信息")
            return False

def main():
    """主函数"""
    tester = DockerComposeTester()
    
    # 检查Docker Compose是否可用
    try:
        subprocess.run(['docker-compose', '--version'], 
                      capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Docker Compose 未安装或不可用")
        sys.exit(1)
    
    # 运行测试
    results = tester.run_all_tests()
    
    # 生成报告
    success = tester.generate_test_report(results)
    
    # 退出码
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main() 