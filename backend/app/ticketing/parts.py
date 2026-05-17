from app.ticketing.models import PartCandidate

PART_CATALOG = [
    PartCandidate(
        part_id="A100-FILTER-001",
        name="过滤器",
        device_model="A100",
        reason="A100 供压异常常见检查项。",
    ),
    PartCandidate(
        part_id="A100-PRESSURE-002",
        name="压力传感器",
        device_model="A100",
        reason="A100 E-17 供压异常可能涉及压力检测。",
    ),
    PartCandidate(
        part_id="CW200-FAN-001",
        name="冷凝风机",
        device_model="CW200",
        reason="CW200 高压报警需要检查冷凝散热。",
    ),
    PartCandidate(
        part_id="CW200-PRESSURE-002",
        name="压力传感器",
        device_model="CW200",
        reason="CW200 高压报警可能涉及压力检测。",
    ),
    PartCandidate(
        part_id="CW200-FILTER-003",
        name="过滤网",
        device_model="CW200",
        reason="CW200 散热不良时需要检查过滤网。",
    ),
]


def query_parts(device_model: str | None, text: str) -> list[PartCandidate]:
    if not device_model:
        return []

    normalized = text.lower()
    candidates = [
        part
        for part in PART_CATALOG
        if part.device_model.lower() == device_model.lower()
        and (part.name in text or part.name.lower() in normalized)
    ]
    if candidates:
        return candidates

    if any(keyword in text for keyword in ["备件", "更换", "高压报警", "压力"]):
        return [part for part in PART_CATALOG if part.device_model.lower() == device_model.lower()]
    return []
