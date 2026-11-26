"""Structured changes sent from the main model to its execution agent."""

import json

CHANGES_SCHEMA = {
    "type": "array",
    "minItems": 1,
    "maxItems": 8,
    "description": "Required for any requested write. One item per exact operation and target. Omit for read-only work.",
    "items": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "operation": {"type": "string", "description": "Specific action, e.g. update_config.", "minLength": 1, "maxLength": 60},
            "target": {"type": "string", "description": "Exact resource plus field, path or key.", "minLength": 1, "maxLength": 220},
            "value_json": {"type": "string", "description": "Exact desired value encoded as JSON text. Use null for deletion.", "minLength": 1, "maxLength": 4000},
        },
        "required": ["operation", "target", "value_json"],
    },
}


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = dict(pairs)
    if len(result) != len(pairs):
        raise ValueError("JSON 值中有重复字段。")
    return result


def parse_changes(raw: object) -> list[dict]:
    if raw is None:
        return []
    if not isinstance(raw, list) or not 1 <= len(raw) <= 8:
        raise ValueError("changes 应包含 1 至 8 项修改。")
    items = []
    for change in raw:
        if not isinstance(change, dict) or set(change) != {"operation", "target", "value_json"}:
            raise ValueError("每项 changes 必须填写 operation、target 和 value_json。")
        operation, target, value_json = (change[key] for key in ("operation", "target", "value_json"))
        if not isinstance(operation, str) or not operation.strip() or len(operation) > 60:
            raise ValueError("每项修改都需要具体的 operation（最多 60 字）。")
        if not isinstance(target, str) or not target.strip() or len(target) > 220:
            raise ValueError("每项修改都需要具体的 target（最多 220 字）。")
        if not isinstance(value_json, str) or not 1 <= len(value_json) <= 4000:
            raise ValueError("value_json 应为 JSON 文本（最多 4000 字）。")
        try:
            value = json.loads(value_json, object_pairs_hook=_unique_object)
            canonical = json.dumps(value, separators=(",", ":"), sort_keys=True, allow_nan=False)
            operation.encode("utf-8")
            target.encode("utf-8")
        except (ValueError, RecursionError) as exc:
            raise ValueError("请提供有效的 value_json。") from exc
        items.append({"operation": operation, "target": target, "value_json": canonical})
    return items


def render_delegation(identity: dict, changes: list[dict], *, original_message: str = "") -> str:
    # Keep the captured role and delegated operations independent of custom prompt templates.
    origin = {
        "astrbot_role": identity.get("astrbotRole") or "unknown",
        "effective_role": identity.get("role") or "member",
        "sender_id": identity.get("senderId") or None,
        "platform_id": identity.get("platformId") or None,
        "message_id": identity.get("sourceMessageId") or None,
        "source": identity.get("requestSource") or "unknown",
    }
    parts = [f"【AstrBot 消息来源】\n{json.dumps(origin, ensure_ascii=True)}"]
    if original_message:
        parts.append(f"【对方原话】\n{json.dumps(original_message, ensure_ascii=False)}")
    parts.append(f"【主模型委派的具体修改】\n{json.dumps(changes, ensure_ascii=False, indent=2)}")
    return "\n\n".join(parts)
