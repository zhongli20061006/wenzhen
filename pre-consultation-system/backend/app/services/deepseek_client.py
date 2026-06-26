import json
import re
import httpx
from typing import AsyncGenerator

from app.config import settings
from app.logger import logger

BASE_URL = "https://api.deepseek.com/v1"
TIMEOUT = 30.0

SYSTEM_PROMPT = """你是一个医疗预问诊系统的AI助手。你的任务是：
1. 根据患者描述的症状，推断可能相关的其他症状
2. 对候选疾病列表进行排序和评分
请始终以JSON格式返回结果，不要添加任何解释或额外文字。"""

EXTRACTION_PROMPT = """你是一个专业的医疗预问诊系统的症状提取助手。你的任务是从患者的自然语言描述中提取所有可能的症状。

规则：
1. 提取所有明确提到或强暗示的医学症状
2. 使用标准医学术语（如"胸痛"而非"胸口不舒服"，"发热"而非"发烧"）
3. 对描述模糊的症状，保留患者原话并标注低置信度
4. 不要凭空编造症状
5. 忽略非医学内容（如"我今天吃了饭"中的吃饭）

返回纯JSON（不要markdown代码块，不要额外文字）：
{"symptoms":[{"name":"症状名","confidence":0.95}],"reasoning":"提取思路简述"}

其中 confidence 含义：1.0=患者明确描述，0.7-0.9=强烈暗示，0.5-0.7=可能相关，<0.5=不返回"""

PROMPT_INJECTION_BLOCKLIST = [
    "ignore", "system", "override", "bypass", "指令",
    "忽略", "覆盖", "绕过", "新设定", "reset", "---",
]


def sanitize_input(text: str) -> str:
    lowered = text.lower()
    for keyword in PROMPT_INJECTION_BLOCKLIST:
        if keyword.lower() in lowered:
            logger.warning("DeepSeek 输入拦截: 检测到注入关键词 '%s'", keyword)
            return text[:200] + "...[截断]"
    text = text.replace("{", "{{").replace("}", "}}")
    if len(text) > 2000:
        text = text[:2000] + "...[截断]"
    return text


def is_available() -> bool:
    return bool(settings.DEEPSEEK_API_KEY) and settings.DEEPSEEK_ENABLED


def _parse_json_response(content: str, default: dict) -> dict:
    json_match = re.search(r'\{[^{}]*\}', content, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass
    brace_start = content.find('{')
    brace_end = content.rfind('}')
    if brace_start >= 0 and brace_end > brace_start:
        try:
            return json.loads(content[brace_start:brace_end + 1])
        except json.JSONDecodeError:
            logger.warning("DeepSeek JSON 解析失败, 原文: %s", content[:200])
    return default


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }


async def enrich_symptoms(symptoms: list[str], description: str = "") -> dict:
    if not is_available():
        return {"suggestions": [], "reasoning": ""}

    desc_text = f" 患者自述：{sanitize_input(description)}" if description else ""
    user_prompt = f"患者描述症状：{'、'.join(symptoms[:10])}。{desc_text}\n请推断患者可能存在的其他相关症状，以JSON返回：{{\"suggestions\": [\"症状名\"], \"reasoning\": \"推断理由简述\"}}"

    return await _call(user_prompt)


async def rank_diseases(symptoms: list[str], candidates: list[dict], collected_data: dict = None) -> dict:
    if not is_available():
        return {"rankings": [], "explanation": ""}

    candidate_text = "\n".join(
        f"- {c['disease_name']} (当前得分: {c['score']:.3f}, 科室: {c.get('department_name','')})"
        for c in candidates[:10]
    )

    extra = ""
    if collected_data:
        sev = collected_data.get("severity")
        dur = collected_data.get("onset_days")
        hist = collected_data.get("medical_history", [])
        if sev:
            extra += f" 严重程度(1-10): {sev}。"
        if dur is not None:
            extra += f" 病程: {dur}天。"
        if hist:
            extra += f" 既往史: {'、'.join(hist)}。"

    user_prompt = f"""患者症状：{'、'.join(symptoms[:10])}。{extra}
候选疾病及当前评分：
{candidate_text}

请重新排序这些疾病，考虑症状组合的典型性和紧急性。以JSON返回：
{{"rankings": [{{"disease_name": "疾病名", "adjusted_score": 0.0-1.0, "reasoning": "一句理由"}}], "explanation": "总体排序理由简述"}}"""

    return await _call(user_prompt)


async def _call(user_prompt: str, system_prompt: str | None = None) -> dict:
    messages = [
        {"role": "system", "content": system_prompt or SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]
    body = {
        "model": "deepseek-chat",
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": 1500,
        "stream": False,
    }

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(
                f"{BASE_URL}/chat/completions",
                headers=_headers(),
                json=body,
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            logger.debug("DeepSeek 回复: %s", content[:300])
            return _parse_json_response(content, {"error": "parse_failed", "raw": content[:500]})
    except httpx.HTTPStatusError as e:
        logger.error("DeepSeek HTTP %d: %s", e.response.status_code, e.response.text[:200])
        return {"error": f"http_{e.response.status_code}"}
    except httpx.RequestError as e:
        logger.error("DeepSeek 请求失败: %s", e)
        return {"error": "request_failed", "detail": str(e)[:200]}
    except Exception as e:
        logger.error("DeepSeek 未知错误: %s", e)
        return {"error": "unknown", "detail": str(e)[:200]}


async def stream_call(user_prompt: str) -> AsyncGenerator[str, None]:
    if not is_available():
        yield json.dumps({"error": "deepseek_disabled"})
        return

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]
    body = {
        "model": "deepseek-chat",
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": 1500,
        "stream": True,
    }

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            async with client.stream(
                "POST", f"{BASE_URL}/chat/completions",
                headers=_headers(),
                json=body,
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        chunk = line[6:]
                        if chunk == "[DONE]":
                            break
                        try:
                            delta = json.loads(chunk)
                            text = delta.get("choices", [{}])[0].get("delta", {}).get("content", "")
                            if text:
                                yield text
                        except json.JSONDecodeError:
                            continue
    except Exception as e:
        logger.error("DeepSeek 流式请求失败: %s", e)
        yield json.dumps({"error": "stream_failed", "detail": str(e)[:200]})


async def suggest_next_question(
    confirmed_symptoms: list[str],
    denied_symptoms: list[str],
    candidates: list[dict],
    asked_symptoms: list[str],
    collected_data: dict = None,
) -> dict:
    if not is_available():
        return {"symptom_name": "", "reasoning": "", "matched": False}

    confirmed_text = "、".join(confirmed_symptoms) if confirmed_symptoms else "（无）"
    denied_text = "、".join(denied_symptoms) if denied_symptoms else "（无）"
    asked_text = "、".join(asked_symptoms) if asked_symptoms else "（无）"

    candidate_text = "\n".join(
        f"- {c['disease_name']} (得分: {c['score']:.3f}, 科室: {c.get('department_name','')})"
        for c in candidates[:10]
    )

    extra = ""
    if collected_data:
        sev = collected_data.get("severity")
        dur = collected_data.get("onset_days")
        if sev:
            extra += f" 严重程度: {sev}/10。"
        if dur is not None:
            extra += f" 病程: {dur}天。"

    user_prompt = f"""你是医疗预问诊系统的AI决策助手。

患者已确认的症状：{confirmed_text}
患者否认的症状：{denied_text}
已经问过的症状：{asked_text}
当前候选疾病及得分：
{candidate_text}
{extra}

请从候选疾病的关联症状中，选出下一个最值得追问的症状。选择标准：
1. 能最高效地区分TOP候选疾病（鉴别力强）
2. 不能是已确认、已否认或已问过的症状
3. 考虑严重程度和病程的紧迫性
4. 优先选择必要条件(is_required)或鉴别标志(is_discriminative)的症状

返回JSON（不要其他文字）：
{{"symptom_name": "症状名", "reasoning": "选择该症状的理由（含疾病区分逻辑，50字以内）"}}"""

    return await _call(user_prompt)


async def health_check() -> dict:
    if not is_available():
        return {"status": "disabled", "message": "DeepSeek 未启用或 API Key 未设置"}
    try:
        result = await _call("请回复 OK")
        return {"status": "ok" if "error" not in result else "degraded", "test_response": result}
    except Exception as e:
        return {"status": "error", "message": str(e)[:200]}


async def extract_symptoms_from_text(description: str, db) -> list[dict]:
    """
    DeepSeek 保底症状提取 — 当 BERT + 关键词均无法有效提取症状时，
    将患者原话直接发送给 DeepSeek 进行自然语言症状识别。

    返回格式与 match_keywords/extract_bert 一致：
    [{symptom_id, symptom_name, match_type, confidence, source}]
    """
    if not is_available() or not description or not description.strip():
        return []

    from app.models.symptom_dict import SymptomDict

    user_prompt = f"请从以下患者描述中提取所有可能的医学症状：\n{description.strip()}"

    result = await _call(user_prompt, system_prompt=EXTRACTION_PROMPT)
    if "error" in result:
        logger.warning("DeepSeek 症状提取失败: %s", result.get("error"))
        return []

    ds_symptoms: list[dict] = result.get("symptoms", [])
    reasoning = result.get("reasoning", "")
    if not ds_symptoms:
        logger.debug("DeepSeek 未提取到症状 (reasoning=%s)", reasoning)
        return []

    logger.info("DeepSeek 症状提取保底: raw=%d symptoms, reasoning=%s",
                 len(ds_symptoms), reasoning[:80])

    # 映射 DeepSeek 症状名到 symptom_dict
    symptoms = db.query(SymptomDict).all()
    sym_map_by_name: dict[str, int] = {}
    sym_map_by_alias: dict[str, int] = {}
    for s in symptoms:
        sym_map_by_name[s.name] = s.id
        if s.aliases:
            for alias in s.aliases.split(","):
                alias = alias.strip()
                if alias:
                    sym_map_by_alias[alias] = s.id

    results: list[dict] = []
    seen_ids: set[int] = set()
    for ds in ds_symptoms:
        name = ds.get("name", "").strip()
        confidence = float(ds.get("confidence", 0.7))
        if not name or confidence < 0.5:
            continue

        # 1. 精确匹配症状名
        if name in sym_map_by_name:
            sid = sym_map_by_name[name]
            if sid not in seen_ids:
                seen_ids.add(sid)
                results.append({
                    "symptom_id": sid, "symptom_name": name,
                    "match_type": "deepseek_exact", "confidence": min(confidence, 0.95),
                    "source": "deepseek",
                })
                continue

        # 2. 别名匹配
        if name in sym_map_by_alias:
            sid = sym_map_by_alias[name]
            if sid not in seen_ids:
                original_name = db.query(SymptomDict).filter(SymptomDict.id == sid).first()
                seen_ids.add(sid)
                results.append({
                    "symptom_id": sid,
                    "symptom_name": original_name.name if original_name else name,
                    "match_type": "deepseek_alias", "confidence": min(confidence, 0.90),
                    "source": "deepseek",
                })
                continue

        # 3. 模糊匹配（子串或相似度）
        matched_sid = None
        matched_name = None
        for sym in symptoms:
            if sym.name in name or name in sym.name:
                matched_sid, matched_name = sym.id, sym.name
                break
            if sym.aliases:
                for alias in sym.aliases.split(","):
                    alias = alias.strip()
                    if alias and (alias in name or name in alias):
                        matched_sid, matched_name = sym.id, sym.name
                        break
                if matched_sid:
                    break

        if matched_sid and matched_sid not in seen_ids:
            seen_ids.add(matched_sid)
            results.append({
                "symptom_id": matched_sid, "symptom_name": matched_name,
                "match_type": "deepseek_fuzzy", "confidence": min(confidence * 0.85, 0.85),
                "source": "deepseek",
            })

    logger.info("DeepSeek 症状提取映射: %d raw → %d mapped", len(ds_symptoms), len(results))
    return results
