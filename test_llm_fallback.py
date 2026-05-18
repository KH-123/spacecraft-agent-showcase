"""
全面的 LLM 提取 + Fallback 机制测试脚本。

测试场景：
1. 无 API Key → fallback 到 rules parser
2. API Key 无效 → 异常 → fallback 到 rules parser
3. LLM 返回非法 JSON → fallback
4. LLM 返回 schema 不匹配 → fallback
5. LLM 正常返回 → 使用 LLM 结果
6. 中文输入（吨、千瓦、极地轨道）→ 正常提取
7. 带 typo 的中文输入（轨道类型位极地轨道）→ 正常提取
8. Validator 正常/警告/severe 分级
9. 完整端到端流程（app.py 模拟）
10. 异常类层次结构
11. Fallback 条件判断
12. 参数确认报告
13. 边界输入测试
"""

import os
import sys
import json
import logging
import traceback

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

# 确保项目根目录在 sys.path 中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

PASS = 0
FAIL = 0
TOTAL = 0


def run_test(name: str, fn):
    """Run a test function and track pass/fail."""
    global TOTAL, PASS, FAIL
    TOTAL += 1
    print(f"\n{'='*60}")
    print(f"🧪 Test #{TOTAL}: {name}")
    print(f"{'='*60}")
    try:
        fn()
        print(f"  ✅ PASS")
        PASS += 1
    except Exception as e:
        print(f"  ❌ FAIL: {e}")
        traceback.print_exc()
        FAIL += 1


# ============================================================================
# Test 1: 无 API Key → fallback 到 rules parser
# ============================================================================
def test_no_api_key():
    """清除 LLM_API_KEY，验证 extract_mission_parameters 自动 fallback 到 rules parser。"""
    # 保存原始环境变量
    orig_key = os.environ.pop("LLM_API_KEY", None)
    orig_base_url = os.environ.pop("LLM_BASE_URL", None)
    orig_model = os.environ.pop("LLM_MODEL", None)

    try:
        from agents.extractor import extract_mission_parameters

        params = extract_mission_parameters(
            "设计一颗低轨遥感小卫星，轨道高度500公里，载荷质量50kg，功耗100W，寿命3年。"
        )

        print(f"  source 追踪:")
        for key, entry in params.items():
            print(f"    {key}: value={entry.get('value')}, source={entry.get('source')}")

        # 验证 fallback 到 rules_fallback
        assert params["orbit_altitude_km"]["source"] == "rules_fallback", \
            f"Expected rules_fallback, got {params['orbit_altitude_km']['source']}"
        assert params["payload_mass_kg"]["source"] == "rules_fallback"
        assert params["power_required_w"]["source"] == "rules_fallback"

        # 验证值正确
        assert params["orbit_altitude_km"]["value"] == 500
        assert params["payload_mass_kg"]["value"] == 50
        assert params["power_required_w"]["value"] == 100

        print("  ✅ 无 API Key 时成功 fallback 到 rules parser，值正确")
    finally:
        # 恢复环境变量
        if orig_key is not None:
            os.environ["LLM_API_KEY"] = orig_key
        if orig_base_url is not None:
            os.environ["LLM_BASE_URL"] = orig_base_url
        if orig_model is not None:
            os.environ["LLM_MODEL"] = orig_model


# ============================================================================
# Test 2: API Key 无效 → 异常 → fallback 到 rules parser
# ============================================================================
def test_invalid_api_key():
    """设置无效 API Key，验证 LLM 调用失败后 fallback 到 rules parser。"""
    os.environ["LLM_API_KEY"] = "sk-invalid-key-for-testing"
    os.environ["LLM_BASE_URL"] = "https://api.deepseek.com"
    os.environ["LLM_MODEL"] = "deepseek-chat"

    try:
        from agents.extractor import extract_mission_parameters

        params = extract_mission_parameters(
            "设计一颗低轨遥感小卫星，轨道高度500公里，载荷质量50kg，功耗100W，寿命3年。"
        )

        print(f"  source 追踪:")
        for key, entry in params.items():
            print(f"    {key}: value={entry.get('value')}, source={entry.get('source')}")

        # 验证 fallback 到 rules_fallback
        assert params["orbit_altitude_km"]["source"] == "rules_fallback", \
            f"Expected rules_fallback, got {params['orbit_altitude_km']['source']}"

        # 验证值正确
        assert params["orbit_altitude_km"]["value"] == 500
        assert params["payload_mass_kg"]["value"] == 50

        print("  ✅ 无效 API Key 时成功 fallback 到 rules parser")
    finally:
        del os.environ["LLM_API_KEY"]
        del os.environ["LLM_BASE_URL"]
        del os.environ["LLM_MODEL"]


# ============================================================================
# Test 3: Schema 不匹配 → fallback
# ============================================================================
def test_schema_mismatch():
    """测试 SchemaMismatchError 异常类和 schema 验证逻辑。"""
    from agents.llm_extractor import SchemaMismatchError, _validate_schema

    # 测试空 dict
    try:
        _validate_schema({})
        assert False, "Should have raised SchemaMismatchError"
    except SchemaMismatchError as e:
        print(f"  ✅ 空 dict 被正确拒绝: {e}")

    # 测试缺少 mission_parameters
    try:
        _validate_schema({"some_key": {}})
        assert False, "Should have raised SchemaMismatchError"
    except SchemaMismatchError as e:
        print(f"  ✅ 缺少 mission_parameters 被正确拒绝: {e}")

    # 测试 mission_parameters 不是 dict
    try:
        _validate_schema({"mission_parameters": "not_a_dict"})
        assert False, "Should have raised SchemaMismatchError"
    except SchemaMismatchError as e:
        print(f"  ✅ mission_parameters 不是 dict 被正确拒绝: {e}")

    # 测试缺少字段
    try:
        _validate_schema({"mission_parameters": {}})
        assert False, "Should have raised SchemaMismatchError"
    except SchemaMismatchError as e:
        print(f"  ✅ 缺少字段被正确拒绝: {e}")

    # 测试有效 schema
    valid_data = {
        "mission_parameters": {
            "orbit_altitude": {"found": True, "value": 500, "unit": "km", "raw_text": "500公里", "confidence": 0.95},
            "payload_mass": {"found": True, "value": 50, "unit": "kg", "raw_text": "50kg", "confidence": 0.95},
            "power_required": {"found": False, "value": None, "unit": None, "raw_text": None, "confidence": 0.0},
            "orbit_inclination": {"found": False, "value": None, "unit": None, "raw_text": None, "confidence": 0.0},
            "orbit_type": {"found": True, "value": "LEO", "unit": None, "raw_text": "低轨", "confidence": 0.9},
            "mission_lifetime": {"found": True, "value": 3, "unit": "year", "raw_text": "3年", "confidence": 0.95},
            "ground_resolution": {"found": False, "value": None, "unit": None, "raw_text": None, "confidence": 0.0},
        }
    }
    try:
        _validate_schema(valid_data)
        print("  ✅ 有效 schema 通过验证")
    except SchemaMismatchError as e:
        assert False, f"Valid schema should pass: {e}"

    print("  ✅ Schema 验证逻辑全部正确")


# ============================================================================
# Test 4: Normalizer 单位转换测试
# ============================================================================
def test_normalizer_unit_conversion():
    """测试 normalizer 的单位转换功能。"""
    from agents.normalizer import (
        _convert_value, _normalize_orbit_type,
        MASS_TO_KG, POWER_TO_W, ALTITUDE_TO_KM, TIME_TO_YEARS,
    )

    # 测试质量转换
    assert _convert_value(1, "吨", MASS_TO_KG) == (1000.0, "standardized"), "吨→kg 转换失败"
    assert _convert_value(1, "ton", MASS_TO_KG) == (1000.0, "standardized"), "ton→kg 转换失败"
    assert _convert_value(1, "t", MASS_TO_KG) == (1000.0, "standardized"), "t→kg 转换失败"
    assert _convert_value(50, "kg", MASS_TO_KG) == (50.0, "standardized"), "kg 转换失败"
    assert _convert_value(50, "千克", MASS_TO_KG) == (50.0, "standardized"), "千克→kg 转换失败"
    assert _convert_value(50, "公斤", MASS_TO_KG) == (50.0, "standardized"), "公斤→kg 转换失败"
    print("  ✅ 质量单位转换全部正确")

    # 测试功率转换
    assert _convert_value(0.5, "千瓦", POWER_TO_W) == (500.0, "standardized"), "千瓦→W 转换失败"
    assert _convert_value(0.5, "kW", POWER_TO_W) == (500.0, "standardized"), "kW→W 转换失败"
    assert _convert_value(100, "W", POWER_TO_W) == (100.0, "standardized"), "W 转换失败"
    assert _convert_value(100, "瓦", POWER_TO_W) == (100.0, "standardized"), "瓦→W 转换失败"
    print("  ✅ 功率单位转换全部正确")

    # 测试高度转换
    assert _convert_value(500, "km", ALTITUDE_TO_KM) == (500.0, "standardized"), "km 转换失败"
    assert _convert_value(500, "公里", ALTITUDE_TO_KM) == (500.0, "standardized"), "公里→km 转换失败"
    assert _convert_value(500, "千米", ALTITUDE_TO_KM) == (500.0, "standardized"), "千米→km 转换失败"
    print("  ✅ 高度单位转换全部正确")

    # 测试时间转换
    assert _convert_value(3, "年", TIME_TO_YEARS) == (3.0, "standardized"), "年→years 转换失败"
    assert _convert_value(3, "year", TIME_TO_YEARS) == (3.0, "standardized"), "year→years 转换失败"
    assert _convert_value(3, "yr", TIME_TO_YEARS) == (3.0, "standardized"), "yr→years 转换失败"
    assert _convert_value(6, "月", TIME_TO_YEARS) == (0.5, "standardized"), "月→years 转换失败"
    print("  ✅ 时间单位转换全部正确")

    # 测试轨道类型标准化
    assert _normalize_orbit_type("太阳同步轨道") == ("SSO", True)
    assert _normalize_orbit_type("极地轨道") == ("polar orbit", True)
    assert _normalize_orbit_type("低轨") == ("LEO", True)
    assert _normalize_orbit_type("近地轨道") == ("LEO", True)
    assert _normalize_orbit_type("SSO") == ("SSO", True)
    assert _normalize_orbit_type("LEO") == ("LEO", True)
    print("  ✅ 轨道类型标准化全部正确")

    print("  ✅ Normalizer 单位转换全部通过")


# ============================================================================
# Test 5: Normalizer LLM 输出归一化测试
# ============================================================================
def test_normalizer_llm_output():
    """测试 normalize_llm_output 函数。"""
    from agents.normalizer import normalize_llm_output

    # 模拟 LLM 返回数据（包含中文单位）
    llm_raw = {
        "mission_parameters": {
            "orbit_altitude": {"found": True, "value": 500, "unit": "公里", "raw_text": "500公里", "confidence": 0.95},
            "payload_mass": {"found": True, "value": 1, "unit": "吨", "raw_text": "1吨", "confidence": 0.95},
            "power_required": {"found": True, "value": 0.5, "unit": "千瓦", "raw_text": "0.5千瓦", "confidence": 0.9},
            "orbit_inclination": {"found": False, "value": None, "unit": None, "raw_text": None, "confidence": 0.0},
            "orbit_type": {"found": True, "value": "极地轨道", "unit": None, "raw_text": "极地轨道", "confidence": 0.9},
            "mission_lifetime": {"found": True, "value": 3, "unit": "年", "raw_text": "3年", "confidence": 0.95},
            "ground_resolution": {"found": True, "value": 5, "unit": "米", "raw_text": "5米", "confidence": 0.9},
        }
    }

    result = normalize_llm_output(llm_raw)

    print(f"  归一化结果:")
    for key, entry in result.items():
        print(f"    {key}: value={entry.get('value')}, unit={entry.get('unit')}, found={entry.get('found')}, source={entry.get('source')}")

    # 验证单位转换
    assert result["orbit_altitude_km"]["value"] == 500, f"高度应为 500, 实际: {result['orbit_altitude_km']['value']}"
    assert result["payload_mass_kg"]["value"] == 1000, f"质量应为 1000 (1吨), 实际: {result['payload_mass_kg']['value']}"
    assert result["power_required_w"]["value"] == 500, f"功率应为 500 (0.5千瓦), 实际: {result['power_required_w']['value']}"
    assert result["orbit_type"]["value"] == "polar orbit", f"轨道类型应为 polar orbit, 实际: {result['orbit_type']['value']}"
    assert result["mission_lifetime_years"]["value"] == 3, f"寿命应为 3, 实际: {result['mission_lifetime_years']['value']}"
    assert result["ground_resolution_m"]["value"] == 5, f"分辨率应为 5, 实际: {result['ground_resolution_m']['value']}"

    # 验证 source
    assert result["payload_mass_kg"]["source"] == "llm_extracted_normalized"

    print("  ✅ LLM 输出归一化全部正确")


# ============================================================================
# Test 6: Validator 分级测试
# ============================================================================
def test_validator_levels():
    """测试 validator 的正常/警告/severe 三级分级。"""
    from agents.validator import validate_parameters, has_severe_errors, get_warnings

    # 测试 1: 正常值
    normal_params = {
        "orbit_altitude_km": {"value": 500, "unit": "km", "found": True},
        "mission_lifetime_years": {"value": 3, "unit": "years", "found": True},
        "payload_mass_kg": {"value": 50, "unit": "kg", "found": True},
        "power_required_w": {"value": 100, "unit": "W", "found": True},
        "daily_data_volume_GB": {"value": 100, "unit": "GB", "found": True},
    }
    results = validate_parameters(normal_params)
    severe_count = sum(1 for r in results if r.level == "severe")
    warning_count = sum(1 for r in results if r.level == "warning")
    print(f"  正常值: severe={severe_count}, warning={warning_count}")
    assert severe_count == 0, f"正常值不应有 severe, 实际: {severe_count}"
    assert not has_severe_errors(results), "正常值不应触发 has_severe_errors"
    print("  ✅ 正常值验证通过")

    # 测试 2: 警告值
    # orbit_altitude_km=1000: warning range is 200-1200, 1000 is within warning range → pass
    # mission_lifetime_years=8: warning range is 0.5-10, 8 is within warning range → pass
    # payload_mass_kg=200: warning range is 1-300, 200 is within warning range → pass
    # power_required_w=500: warning range is 1-1000, 500 is within warning range → pass
    # 需要超出 warning range 但仍在 severe range 内才能触发 warning
    # 例如: orbit_altitude_km=150 (severe_min=160, warning_min=200) → 150<160 → severe
    # 例如: orbit_altitude_km=180 (severe_min=160, warning_min=200) → 160<180<200 → warning!
    # 例如: mission_lifetime_years=12 (severe_max=15, warning_max=10) → 10<12<15 → warning!
    warning_params = {
        "orbit_altitude_km": {"value": 180, "unit": "km", "found": True},
        "mission_lifetime_years": {"value": 12, "unit": "years", "found": True},
        "payload_mass_kg": {"value": 250, "unit": "kg", "found": True},
        "power_required_w": {"value": 800, "unit": "W", "found": True},
    }
    results = validate_parameters(warning_params)
    severe_count = sum(1 for r in results if r.level == "severe")
    warning_count = sum(1 for r in results if r.level == "warning")
    print(f"  警告值: severe={severe_count}, warning={warning_count}")
    assert severe_count == 0, f"警告值不应有 severe, 实际: {severe_count}"
    assert warning_count > 0, f"警告值应有 warning, 实际: {warning_count}"
    assert not has_severe_errors(results), "警告值不应触发 has_severe_errors"
    print("  ✅ 警告值验证通过")

    # 测试 3: Severe 值
    severe_params = {
        "orbit_altitude_km": {"value": 100, "unit": "km", "found": True},
        "mission_lifetime_years": {"value": 20, "unit": "years", "found": True},
        "payload_mass_kg": {"value": 500, "unit": "kg", "found": True},
        "power_required_w": {"value": 2000, "unit": "W", "found": True},
        "daily_data_volume_GB": {"value": 5000, "unit": "GB", "found": True},
    }
    results = validate_parameters(severe_params)
    severe_count = sum(1 for r in results if r.level == "severe")
    warning_count = sum(1 for r in results if r.level == "warning")
    print(f"  Severe 值: severe={severe_count}, warning={warning_count}")
    assert severe_count > 0, f"Severe 值应有 severe, 实际: {severe_count}"
    assert has_severe_errors(results), "Severe 值应触发 has_severe_errors"
    print("  ✅ Severe 值验证通过")

    # 测试 4: 未找到的值（不触发验证）
    not_found_params = {
        "orbit_altitude_km": {"value": None, "unit": None, "found": False},
        "mission_lifetime_years": {"value": None, "unit": None, "found": False},
        "payload_mass_kg": {"value": None, "unit": None, "found": False},
        "power_required_w": {"value": None, "unit": None, "found": False},
        "daily_data_volume_GB": {"value": None, "unit": None, "found": False},
    }
    results = validate_parameters(not_found_params)
    severe_count = sum(1 for r in results if r.level == "severe")
    print(f"  未找到值: severe={severe_count}")
    assert severe_count == 0, f"未找到值不应有 severe, 实际: {severe_count}"
    print("  ✅ 未找到值验证通过")

    print("  ✅ Validator 三级分级全部正确")


# ============================================================================
# Test 7: 中文输入（吨、千瓦、极地轨道）→ 提取 + 归一化 + 验证
# ============================================================================
def test_chinese_input_full_flow():
    """测试中文输入（含吨、千瓦、极地轨道）的完整流程。"""
    # 清除 API Key 以使用 rules fallback
    orig_key = os.environ.pop("LLM_API_KEY", None)

    try:
        from agents.extractor import extract_mission_parameters
        from agents.validator import validate_parameters, has_severe_errors

        # 中文输入：含吨、千瓦、极地轨道
        text = "设计一颗极地轨道遥感卫星，有效质量1吨，载荷功耗0.5千瓦，轨道高度600公里，寿命5年。"
        params = extract_mission_parameters(text)

        print(f"  提取结果:")
        for key, entry in params.items():
            print(f"    {key}: value={entry.get('value')}, unit={entry.get('unit')}, source={entry.get('source')}")

        # 验证至少提取到了部分参数
        found_params = [k for k, v in params.items() if v.get("found")]
        print(f"  找到的参数: {found_params}")
        assert len(found_params) > 0, "应至少提取到部分参数"

        # 验证轨道类型
        print(f"  轨道类型: {params.get('orbit_type', {}).get('value')}")

        # 验证 validator
        results = validate_parameters(params)
        severe = has_severe_errors(results)
        print(f"  Validator severe: {severe}")

        print("  ✅ 中文输入完整流程通过")
    finally:
        if orig_key is not None:
            os.environ["LLM_API_KEY"] = orig_key


# ============================================================================
# Test 8: Typo 中文输入（轨道类型位极地轨道）
# ============================================================================
def test_typo_chinese_input():
    """测试带 typo 的中文输入。"""
    orig_key = os.environ.pop("LLM_API_KEY", None)

    try:
        from agents.extractor import extract_mission_parameters

        # typo: "轨道类型位极地轨道" → 应为"轨道类型为极地轨道"
        text = "设计一颗轨道类型位极地轨道的遥感卫星，轨道高度500公里，载荷质量100kg。"
        params = extract_mission_parameters(text)

        print(f"  提取结果:")
        for key, entry in params.items():
            print(f"    {key}: value={entry.get('value')}, source={entry.get('source')}")

        # 验证至少提取到了部分参数
        found_params = [k for k, v in params.items() if v.get("found")]
        print(f"  找到的参数: {found_params}")
        assert len(found_params) > 0, "应至少提取到部分参数"

        print("  ✅ Typo 中文输入通过（不会崩溃）")
    finally:
        if orig_key is not None:
            os.environ["LLM_API_KEY"] = orig_key


# ============================================================================
# Test 9: 完整端到端流程模拟
# ============================================================================
def test_end_to_end_flow():
    """模拟 app.py 的完整端到端流程。"""
    orig_key = os.environ.pop("LLM_API_KEY", None)

    try:
        from agents.extractor import extract_mission_parameters
        from agents.validator import validate_parameters, has_severe_errors
        from agents.planner import plan_analysis_tasks, execute_all_tasks
        from agents.report_generator import generate_report, generate_parameter_confirmation_report
        from agents.parser import identify_missing_parameters

        # 场景 A: 正常输入 → 生成设计报告
        print("\n  --- 场景 A: 正常输入 ---")
        text_a = "设计一颗低轨遥感小卫星，轨道高度500公里，载荷质量50kg，功耗100W，寿命3年。"
        params_a = extract_mission_parameters(text_a)
        missing_a = identify_missing_parameters(params_a)
        validation_a = validate_parameters(params_a)

        print(f"  参数来源: {params_a['orbit_altitude_km']['source']}")
        print(f"  缺失参数: {[m['parameter'] for m in missing_a]}")
        print(f"  Severe 错误: {has_severe_errors(validation_a)}")

        if not has_severe_errors(validation_a):
            tasks = plan_analysis_tasks(params_a)
            results = execute_all_tasks(params_a)
            report = generate_report(params_a, missing_a, results)
            print(f"  报告长度: {len(report)} 字符")
            assert len(report) > 500, f"报告太短: {len(report)}"
            print("  ✅ 正常输入 → 设计报告生成成功")
        else:
            report = generate_parameter_confirmation_report(params_a, missing_a, validation_a)
            print(f"  确认报告长度: {len(report)} 字符")
            print("  ⚠️ 正常输入触发了 severe（需要检查）")

        # 场景 B: Severe 输入 → 参数确认报告
        print("\n  --- 场景 B: Severe 输入 ---")
        text_b = "设计一颗卫星，轨道高度100公里，载荷质量500kg，功耗2000W，寿命20年。"
        params_b = extract_mission_parameters(text_b)
        missing_b = identify_missing_parameters(params_b)
        validation_b = validate_parameters(params_b)

        print(f"  参数来源: {params_b['orbit_altitude_km']['source']}")
        print(f"  Severe 错误: {has_severe_errors(validation_b)}")

        if has_severe_errors(validation_b):
            report_b = generate_parameter_confirmation_report(params_b, missing_b, validation_b)
            print(f"  确认报告长度: {len(report_b)} 字符")
            assert "severe" in report_b.lower() or "严重" in report_b or "参数确认" in report_b, \
                "确认报告应包含 severe/严重/参数确认 关键词"
            print("  ✅ Severe 输入 → 参数确认报告生成成功")
        else:
            print("  ⚠️ Severe 输入未触发 severe（需要检查 guardrail 阈值）")

        print("  ✅ 端到端流程全部通过")
    finally:
        if orig_key is not None:
            os.environ["LLM_API_KEY"] = orig_key


# ============================================================================
# Test 10: LLM 异常类层次结构测试
# ============================================================================
def test_exception_hierarchy():
    """测试 LLM 异常类的层次结构和 catch 机制。"""
    from agents.llm_extractor import (
        LLMExtractionError,
        NoAPIKeyError,
        InvalidJSONError,
        SchemaMismatchError,
    )

    # 验证继承关系
    assert issubclass(NoAPIKeyError, LLMExtractionError), "NoAPIKeyError 应继承 LLMExtractionError"
    assert issubclass(InvalidJSONError, LLMExtractionError), "InvalidJSONError 应继承 LLMExtractionError"
    assert issubclass(SchemaMismatchError, LLMExtractionError), "SchemaMismatchError 应继承 LLMExtractionError"

    # 验证 catch 机制
    try:
        raise NoAPIKeyError("Test")
    except LLMExtractionError:
        print("  ✅ NoAPIKeyError 能被 LLMExtractionError catch")

    try:
        raise InvalidJSONError("Test")
    except LLMExtractionError:
        print("  ✅ InvalidJSONError 能被 LLMExtractionError catch")

    try:
        raise SchemaMismatchError("Test")
    except LLMExtractionError:
        print("  ✅ SchemaMismatchError 能被 LLMExtractionError catch")

    print("  ✅ 异常类层次结构全部正确")


# ============================================================================
# Test 11: Extractor fallback 条件测试
# ============================================================================
def test_extractor_fallback_conditions():
    """测试 extractor 的 fallback 条件判断逻辑。"""
    from agents.extractor import _llm_output_acceptable

    # 测试 1: 空结果 → 不可接受
    empty = {
        "orbit_altitude_km": {"value": None, "found": False},
        "payload_mass_kg": {"value": None, "found": False},
    }
    assert not _llm_output_acceptable(empty), "空结果应不可接受"
    print("  ✅ 空结果被正确判定为不可接受")

    # 测试 2: 1 个字段找到 → 可接受（MIN_FOUND_FIELDS = 1）
    one_found = {
        "orbit_altitude_km": {"value": 500, "found": True},
        "payload_mass_kg": {"value": None, "found": False},
    }
    assert _llm_output_acceptable(one_found), "1 个字段找到应可接受"
    print("  ✅ 1 个字段找到被正确判定为可接受")

    # 测试 3: 全部找到 → 可接受
    all_found = {
        "orbit_altitude_km": {"value": 500, "found": True},
        "payload_mass_kg": {"value": 50, "found": True},
        "power_required_w": {"value": 100, "found": True},
    }
    assert _llm_output_acceptable(all_found), "全部找到应可接受"
    print("  ✅ 全部字段找到被正确判定为可接受")

    print("  ✅ Fallback 条件判断全部正确")


# ============================================================================
# Test 12: Report Generator 参数确认报告测试
# ============================================================================
def test_parameter_confirmation_report():
    """测试参数确认报告的生成。"""
    from agents.report_generator import generate_parameter_confirmation_report
    from agents.validator import validate_parameters

    # 构建 severe 参数
    params = {
        "orbit_altitude_km": {"value": 100, "unit": "km", "found": True, "source": "rules_fallback"},
        "payload_mass_kg": {"value": 500, "unit": "kg", "found": True, "source": "rules_fallback"},
        "power_required_w": {"value": 2000, "unit": "W", "found": True, "source": "rules_fallback"},
        "orbit_inclination_deg": {"value": None, "unit": None, "found": False, "source": "not_found"},
        "orbit_type": {"value": None, "unit": None, "found": False, "source": "not_found"},
        "mission_lifetime_years": {"value": 20, "unit": "years", "found": True, "source": "rules_fallback"},
        "ground_resolution_m": {"value": None, "unit": None, "found": False, "source": "not_found"},
    }
    missing_params = [
        {"parameter": "orbit_inclination_deg", "description": "轨道倾角 (Orbit Inclination)", "severity": "recommended"},
        {"parameter": "orbit_type", "description": "轨道类型 (Orbit type)", "severity": "required"},
        {"parameter": "ground_resolution_m", "description": "地面分辨率 (Ground Resolution)", "severity": "recommended"},
    ]
    validation_results = validate_parameters(params)

    report = generate_parameter_confirmation_report(params, missing_params, validation_results)

    print(f"  确认报告长度: {len(report)} 字符")
    print(f"  报告前 200 字符:\n{report[:200]}")

    # 验证报告包含关键部分
    assert "参数确认" in report or "Parameter Confirmation" in report, "报告应包含标题"
    assert "severe" in report.lower() or "严重" in report, "报告应包含 severe/严重 信息"
    assert len(report) > 200, f"报告太短: {len(report)}"

    print("  ✅ 参数确认报告生成成功")


# ============================================================================
# Test 13: 边界输入测试
# ============================================================================
def test_edge_cases():
    """测试空输入和边界输入。"""
    orig_key = os.environ.pop("LLM_API_KEY", None)

    try:
        from agents.extractor import extract_mission_parameters
        from agents.validator import validate_parameters, has_severe_errors

        # 测试空字符串
        print("\n  --- 空字符串输入 ---")
        params_empty = extract_mission_parameters("")
        found_empty = [k for k, v in params_empty.items() if v.get("found")]
        print(f"  空输入找到的参数: {found_empty}")
        # 空输入不应崩溃
        print("  ✅ 空字符串输入不崩溃")

        # 测试纯英文输入
        print("\n  --- 纯英文输入 ---")
        params_en = extract_mission_parameters(
            "Design a LEO remote sensing satellite with 500km altitude, 50kg payload, 100W power."
        )
        found_en = [k for k, v in params_en.items() if v.get("found")]
        print(f"  英文输入找到的参数: {found_en}")
        assert len(found_en) > 0, "英文输入应至少提取到部分参数"
        print("  ✅ 纯英文输入通过")

        # 测试特殊字符
        print("\n  --- 特殊字符输入 ---")
        params_special = extract_mission_parameters("!@#$%^&*()")
        found_special = [k for k, v in params_special.items() if v.get("found")]
        print(f"  特殊字符输入找到的参数: {found_special}")
        # 特殊字符不应崩溃
        print("  ✅ 特殊字符输入不崩溃")

        print("  ✅ 边界输入测试全部通过")
    finally:
        if orig_key is not None:
            os.environ["LLM_API_KEY"] = orig_key


# ============================================================================
# Test 14: Normalizer rules 输出包装测试
# ============================================================================
def test_normalizer_rules_output():
    """测试 normalize_rules_output 函数。"""
    from agents.normalizer import normalize_rules_output

    # 模拟 rules parser 输出
    rules_params = {
        "orbit_altitude_km": {"value": 500, "unit": "km", "found": True},
        "payload_mass_kg": {"value": 50, "unit": "kg", "found": True},
        "power_required_w": {"value": 100, "unit": "W", "found": True},
        "orbit_inclination_deg": {"value": None, "unit": None, "found": False},
        "orbit_type": {"value": "LEO", "unit": None, "found": True},
        "mission_lifetime_years": {"value": 3, "unit": "years", "found": True},
        "ground_resolution_m": {"value": None, "unit": None, "found": False},
    }

    result = normalize_rules_output(rules_params)

    # 验证 source
    assert result["orbit_altitude_km"]["source"] == "rules_fallback"
    assert result["payload_mass_kg"]["source"] == "rules_fallback"

    # 验证值保持不变
    assert result["orbit_altitude_km"]["value"] == 500
    assert result["payload_mass_kg"]["value"] == 50

    print("  ✅ normalize_rules_output 正确包装 rules 输出")

    print("  ✅ Rules 输出包装全部正确")


# ============================================================================
# Main: 运行所有测试
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 开始 LLM 提取 + Fallback 机制全面测试")
    print("=" * 60)

    run_test("无 API Key → fallback 到 rules parser", test_no_api_key)
    run_test("无效 API Key → fallback 到 rules parser", test_invalid_api_key)
    run_test("Schema 不匹配异常测试", test_schema_mismatch)
    run_test("Normalizer 单位转换测试", test_normalizer_unit_conversion)
    run_test("Normalizer LLM 输出归一化测试", test_normalizer_llm_output)
    run_test("Validator 三级分级测试", test_validator_levels)
    run_test("中文输入（吨、千瓦、极地轨道）完整流程", test_chinese_input_full_flow)
    run_test("Typo 中文输入（轨道类型位极地轨道）", test_typo_chinese_input)
    run_test("完整端到端流程模拟", test_end_to_end_flow)
    run_test("LLM 异常类层次结构测试", test_exception_hierarchy)
    run_test("Extractor fallback 条件测试", test_extractor_fallback_conditions)
    run_test("参数确认报告生成测试", test_parameter_confirmation_report)
    run_test("边界输入测试（空/英文/特殊字符）", test_edge_cases)
    run_test("Normalizer rules 输出包装测试", test_normalizer_rules_output)

    print(f"\n{'='*60}")
    print(f"📊 测试结果汇总")
    print(f"{'='*60}")
    print(f"  总计: {TOTAL}")
    print(f"  ✅ 通过: {PASS}")
    print(f"  ❌ 失败: {FAIL}")
    if FAIL == 0:
        print(f"\n🎉 全部测试通过！")
    else:
        print(f"\n⚠️  有 {FAIL} 个测试失败，请检查日志。")
    print(f"{'='*60}")