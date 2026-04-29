import json
import traceback
from typing import Any, Dict, List

import requests

URL = "http://127.0.0.1:18080/encode"
TIMEOUT = 300

# ========= 测试数据路径 =========
I2I_IMG1 = r"F:\Code\RetrievalSys\algorithm\tests\test_data\ImageRetrieval\airplane_001.jpg"
I2I_IMG2 = r"F:\Code\RetrievalSys\algorithm\tests\test_data\ImageRetrieval\airplane_002.jpg"
I2I_IMG3 = r"F:\Code\RetrievalSys\algorithm\tests\test_data\ImageRetrieval\airplane_003.jpg"

T2I_TEXT1 = (
    "Spindle cell variant of embryonal rhabdomyosarcoma is characterized by "
    "fascicles of eosinophilic spindle cells."
)
T2I_TEXT2 = "cell variant of embryonal rhabdomyosarcoma is characterized by fas"

T2I_IMG1 = r"F:\Code\RetrievalSys\algorithm\tests\test_data\MedicalRetrieval\2a2277a9-b0ded155-c0de8eb9-c124d10e-82c5caab.jpg"
T2I_IMG2 = r"F:\Code\RetrievalSys\algorithm\tests\test_data\MedicalRetrieval\68b5c4b1-227d0485-9cc38c3f-7b84ab51-4b472714.jpg"

T2V_TEXT1 = "a band performing in a small club"
T2V_TEXT2 = "a person speaking on stage"

T2V_VIDEO1 = r"F:\Code\RetrievalSys\algorithm\tests\test_data\VideoRetrieval\video0.mp4"
T2V_VIDEO2 = r"F:\Code\RetrievalSys\algorithm\tests\test_data\VideoRetrieval\video1.mp4"


def pretty(obj: Any, max_len: int = 1200) -> str:
    text = json.dumps(obj, ensure_ascii=False, indent=2)
    return text[:max_len] + ("\n...<truncated>" if len(text) > max_len else "")


def post_case(name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    print("=" * 100)
    print(f"[CASE] {name}")
    print("[REQUEST]")
    print(pretty(payload, max_len=2000))

    try:
        resp = requests.post(URL, json=payload, timeout=TIMEOUT)
        print(f"[STATUS] {resp.status_code}")

        try:
            data = resp.json()
        except Exception:
            data = {"raw_text": resp.text}

        print("[RESPONSE]")
        print(pretty(data))
        return {
            "name": name,
            "status_code": resp.status_code,
            "ok": resp.ok,
            "response": data,
        }
    except Exception as e:
        print("[EXCEPTION]")
        print(str(e))
        traceback.print_exc()
        return {
            "name": name,
            "status_code": None,
            "ok": False,
            "response": {"exception": str(e)},
        }


def summarize(results: List[Dict[str, Any]]) -> None:
    print("\n" + "=" * 100)
    print("[SUMMARY]")
    passed = 0
    failed = 0
    for r in results:
        ok = r["ok"]
        status = r["status_code"]
        tag = "PASS" if ok else "FAIL"
        print(f"{tag:4} | status={status} | {r['name']}")
        if ok:
            passed += 1
        else:
            failed += 1
    print("-" * 100)
    print(f"passed={passed}, failed={failed}, total={len(results)}")


def main():
    cases = [
        # =========================
        # i2i
        # =========================
        {
            "name": "i2i_normal_single_query_multi_key",
            "payload": {
                "scene": "i2i",
                "query": I2I_IMG1,
                "key": [I2I_IMG2, I2I_IMG3],
            },
        },
        {
            "name": "i2i_empty_query_with_key",
            "payload": {
                "scene": "i2i",
                "query": "",
                "key": [I2I_IMG1],
            },
        },
        {
            "name": "i2i_query_list_empty_key",
            "payload": {
                "scene": "i2i",
                "query": [I2I_IMG1, I2I_IMG2],
                "key": [],
            },
        },
        {
            "name": "i2i_query_and_key_both_empty",
            "payload": {
                "scene": "i2i",
                "query": "",
                "key": [],
            },
        },
        {
            "name": "i2i_query_none_key_none",
            "payload": {
                "scene": "i2i",
                "query": None,
                "key": None,
            },
        },
        {
            "name": "i2i_invalid_blank_items_filtered",
            "payload": {
                "scene": "i2i",
                "query": ["", "   ", I2I_IMG1],
                "key": ["", None, I2I_IMG2],
            },
        },

        # =========================
        # t2i
        # =========================
        {
            "name": "t2i_normal_single_query_multi_key",
            "payload": {
                "scene": "t2i",
                "query": T2I_TEXT1,
                "key": [T2I_IMG1, T2I_IMG2],
            },
        },
        {
            "name": "t2i_query_list_empty_key",
            "payload": {
                "scene": "t2i",
                "query": [T2I_TEXT1, T2I_TEXT2],
                "key": [""],
            },
        },
        {
            "name": "t2i_empty_query_with_key",
            "payload": {
                "scene": "t2i",
                "query": "",
                "key": [T2I_IMG1],
            },
        },
        {
            "name": "t2i_query_and_key_both_empty",
            "payload": {
                "scene": "t2i",
                "query": "",
                "key": [],
            },
        },
        {
            "name": "t2i_query_none_key_none",
            "payload": {
                "scene": "t2i",
                "query": None,
                "key": None,
            },
        },
        {
            "name": "t2i_invalid_blank_items_filtered",
            "payload": {
                "scene": "t2i",
                "query": ["", "   ", T2I_TEXT2],
                "key": ["", None, T2I_IMG1],
            },
        },

        # =========================
        # t2v
        # =========================
        {
            "name": "t2v_normal_single_query_multi_key",
            "payload": {
                "scene": "t2v",
                "query": T2V_TEXT1,
                "key": [T2V_VIDEO1, T2V_VIDEO2],
            },
        },
        {
            "name": "t2v_query_list_empty_key",
            "payload": {
                "scene": "t2v",
                "query": [T2V_TEXT1, T2V_TEXT2],
                "key": [],
            },
        },
        {
            "name": "t2v_empty_query_with_key",
            "payload": {
                "scene": "t2v",
                "query": "",
                "key": [T2V_VIDEO1],
            },
        },
        {
            "name": "t2v_query_and_key_both_empty",
            "payload": {
                "scene": "t2v",
                "query": "",
                "key": [],
            },
        },
        {
            "name": "t2v_query_none_key_none",
            "payload": {
                "scene": "t2v",
                "query": None,
                "key": None,
            },
        },
        {
            "name": "t2v_invalid_blank_items_filtered",
            "payload": {
                "scene": "t2v",
                "query": ["", "   ", T2V_TEXT1],
                "key": ["", None, T2V_VIDEO1],
            },
        },

        # =========================
        # scence 兼容性
        # =========================
        {
            "name": "compat_scence_field_i2i",
            "payload": {
                "scence": "i2i",
                "query": I2I_IMG1,
                "key": [I2I_IMG2],
            },
        },
    ]

    results = []
    for case in cases:
        result = post_case(case["name"], case["payload"])
        results.append(result)

    summarize(results)


if __name__ == "__main__":
    main()