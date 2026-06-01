"""
项目完整性测试脚本
运行方式: python test_integrity.py
"""
import sys
import importlib

def test_import(module_name, description=""):
    try:
        importlib.import_module(module_name)
        print(f"✅ {module_name} 导入成功" + (f"  ({description})" if description else ""))
        return True
    except Exception as e:
        print(f"❌ {module_name} 导入失败: {e}")
        return False

def main():
    print("=" * 60)
    print("X Wanderer 项目完整性测试")
    print("=" * 60)

    success = True

    # 核心模块
    success &= test_import("config.settings", "配置")
    success &= test_import("agent.state", "状态定义")
    success &= test_import("agent.memory.memory_manager", "记忆管理器")
    success &= test_import("agent.memory.profile_store", "画像存储")
    success &= test_import("agent.graph", "LangGraph 主图")
    success &= test_import("platforms.x.client", "X API 客户端")
    success &= test_import("platforms.x.tools", "X 工具")
    success &= test_import("utils.scheduler", "定时任务")
    success &= test_import("commands.file_command", "文件指令")
    success &= test_import("commands.cli", "命令行干预")

    # 节点
    nodes = ["supervisor", "wander", "observe", "reflect", "engage", "report", "intervention"]
    for node in nodes:
        success &= test_import(f"agent.nodes.{node}", f"节点: {node}")

    print("\n" + "=" * 60)
    if success:
        print("✅ 项目核心模块导入测试全部通过！")
        print("项目结构完整，可以尝试运行 main.py")
    else:
        print("⚠️  部分模块导入失败，请检查上方错误信息。")
    print("=" * 60)

if __name__ == "__main__":
    main()
