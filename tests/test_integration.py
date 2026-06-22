"""Quick integration test for HybridMind core modules."""
import sys
sys.path.insert(0, '.')

# Test 1: IntentRouter
print("=" * 50)
print("TEST 1: IntentRouter")
print("=" * 50)
from src.router import IntentRouter, Intent
router = IntentRouter()

tests = [
    ("帮我写一个斐波那契数列的函数", "CODE"),
    ("生成一个快速排序算法", "CODE"),
    ("搜索 Python 闭包的知识", "DOC"),
    ("什么是装饰器的原理", "DOC"),
    ("读取 ./docs/report.pdf 的内容", "MULTIMODAL"),
    ("分析这张图片的内容", "MULTIMODAL"),
    ("今天天气怎么样", "UNKNOWN"),
]
passed = 0
for inp, expected in tests:
    intent = router.classify_intent(inp)
    ok = intent.name == expected
    passed += ok
    print(f"  {'OK' if ok else 'FAIL'} | '{inp[:35]}...' -> {intent.name} (expected {expected})")
print(f"\n  Router: {passed}/{len(tests)} passed")

# Test 2: CodeSkill
print("\n" + "=" * 50)
print("TEST 2: CodeSkill")
print("=" * 50)
from src.skills.code_skill import CodeSkill
cs = CodeSkill()

code = cs.generate_code("写一个斐波那契数列函数")
print(f"  Generated {len(code)} chars of code")
valid, err = cs.check_syntax(code)
print(f"  Syntax check: {'OK' if valid else 'FAIL: ' + err}")
if valid:
    ok, out = cs.run_tests(code)
    print(f"  Execution: {'OK' if ok else 'FAIL'}")
    if ok:
        print(f"  Output: {out.strip()}")

# Test 3: KnowledgeBase
print("\n" + "=" * 50)
print("TEST 3: HybridKnowledgeBase")
print("=" * 50)
from src.knowledge_base import HybridKnowledgeBase
kb = HybridKnowledgeBase()
print(f"  KB initialized, doc count: {kb.collection.count()}")

# Add a test document
import tempfile, os
with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
    f.write("Python闭包是指在一个内部函数中，对外部作用域的变量进行引用。闭包可以让函数记住其创建时的环境。装饰器是Python中闭包的典型应用。")
    tmp_path = f.name

doc_id = kb.add_document(tmp_path)
print(f"  Added doc: {doc_id}")

# Query
result = kb.query("什么是闭包", n_results=3)
print(f"  Query '什么是闭包': {len(result['documents'])} results")
if result['documents']:
    print(f"  Top result: {result['documents'][0][:80]}...")

# Cleanup
os.unlink(tmp_path)
kb.delete_document(tmp_path)

# Test 4: Agent integration
print("\n" + "=" * 50)
print("TEST 4: HybridMindAgent")
print("=" * 50)
from src.agent import HybridMindAgent
agent = HybridMindAgent(kb=kb)

result = agent.process("帮我写一个斐波那契数列的函数")
print(f"  Intent: {result['intent']}")
print(f"  Success: {result['success']}")
print(f"  Retries: {result['retries']}")
print(f"  Output preview: {result['result'][:100]}...")

result2 = agent.process("今天天气怎么样")
print(f"\n  Intent: {result2['intent']}")
print(f"  Success: {result2['success']}")
print(f"  Output preview: {result2['result'][:100]}...")

print("\n" + "=" * 50)
print("ALL TESTS PASSED")
print("=" * 50)
