from __future__ import annotations

from collections import defaultdict
from typing import Any

from backend.rules_engine import infer_student_subjects, safe_int, safe_number, split_keywords
from backend.admissions_risk import (
    _collect_risks,
    _normalize_explicit_rule_v2,
)
from backend.admissions_presenter import (
    BUCKET_ORDER,
    _candidate_risk_level,
    _prepare_recommendation_outputs,
    _rejection_item,
    _unique_rejections,
)
from backend.admissions_query import (
    _fetch_candidate_rows,
    _fetch_explicit_rule_map,
    _fetch_history_map,
)
from backend.admissions_scoring import (
    BUCKET_META,
    RISK_LEVEL_LABELS,
    _calculate_rank_gap,
    _calculate_score_gap,
    _evaluate_rank_bucket,
    _evaluate_score_bucket,
    _resolve_candidate_bucket,
)
from backend.admissions_strategy import (
    HENAN_2026_TOTAL_CHOICE_TARGET,
    bucket_target_ratios,
    default_strategy_note,
    resolve_strategy_profile,
)
from backend.admissions_context import (
    BATCH_PRIORITY,
    DECLARED_BATCH_ALIASES,
    TRACK_LABELS,
    _batch_matches_declared_batch,
    _batch_sql_condition,
    _batch_sort_key,
    _fetch_latest_province_batch_rows,
    _latest_admission_year,
    _normalize_declared_batch,
    _pick_effective_batch_codes,
    _resolve_batch_filter_context,
    build_admissions_context,
    detect_track_code,
    estimate_rank_from_segments,
    get_track_labels,
    resolve_effective_rank,
    resolve_effective_score,
)

def _keyword_hits(student: dict[str, Any], row: dict[str, Any]) -> list[str]:
    keywords = split_keywords(
        student.get("school_preference"),
        student.get("target_direction"),
        student.get("interest_preferences"),
        student.get("development_goal"),
        student.get("region_preference"),
        student.get("family_preferences"),
        student.get("parent_focus"),
        student.get("remark"),
    )
    haystack = " ".join(
        str(row.get(field) or "")
        for field in (
            "institution_name",
            "major_name",
            "major_category",
            "batch_code",
            "institution_city",
            "institution_province",
            "plan_notes",
        )
    )
    return list(dict.fromkeys([keyword for keyword in keywords if keyword and keyword in haystack]))


def _region_bonus(student: dict[str, Any], row: dict[str, Any]) -> int:
    preference = str(student.get("region_preference") or "")
    institution_province = str(row.get("institution_province") or "")
    student_province = str(student.get("province") or "")
    bonus = 0
    if "本省" in preference and institution_province and institution_province == student_province:
        bonus += 6
    if "外省" in preference and institution_province and institution_province != student_province:
        bonus += 6
    if "省会" in preference and row.get("institution_city"):
        bonus += 2
    return bonus


def _summarize_probability(student_rank: int | None, student_score: float, history_rows: list[dict[str, Any]]) -> dict[str, Any]:
    ranks = [safe_int(item.get("min_rank")) for item in history_rows if safe_int(item.get("min_rank")) > 0]
    scores = [safe_number(item.get("min_score")) for item in history_rows if safe_number(item.get("min_score")) > 0]
    if not ranks and not scores:
        return {
            "score": 58,
            "label": "待补充概率",
            "note": "历史录取样本不足，当前只做基础冲稳保分层。",
        }

    rank_score = None
    if student_rank and ranks:
        best_rank = min(ranks)
        median_rank = sorted(ranks)[len(ranks) // 2]
        worst_rank = max(ranks)
        if student_rank <= best_rank:
            rank_score = 92
        elif student_rank <= median_rank:
            rank_score = 82
        elif student_rank <= worst_rank:
            rank_score = 68
        elif student_rank <= int(worst_rank * 1.08):
            rank_score = 56
        else:
            rank_score = 36

    score_score = None
    if student_score > 0 and scores:
        best_score = max(scores)
        median_score = sorted(scores)[len(scores) // 2]
        worst_score = min(scores)
        if student_score >= best_score:
            score_score = 90
        elif student_score >= median_score:
            score_score = 80
        elif student_score >= worst_score:
            score_score = 66
        elif student_score >= worst_score - 3:
            score_score = 54
        else:
            score_score = 34

    base_score = 0
    pieces = [item for item in (rank_score, score_score) if item is not None]
    if pieces:
        base_score = round(sum(pieces) / len(pieces))
    else:
        base_score = 58

    if base_score >= 86:
        label = "录取概率较高"
    elif base_score >= 74:
        label = "录取概率中高"
    elif base_score >= 60:
        label = "录取概率中等"
    elif base_score >= 48:
        label = "录取概率偏低"
    else:
        label = "录取风险较高"

    rank_text = f"历史最低位次区间 {min(ranks)} - {max(ranks)}" if ranks else "位次样本不足"
    score_text = f"历史最低分区间 {min(scores):.0f} - {max(scores):.0f}" if scores else "分数样本不足"
    return {
        "score": int(base_score),
        "label": label,
        "note": f"{rank_text}；{score_text}。",
    }


def _summarize_plan_risk(history_rows: list[dict[str, Any]]) -> dict[str, Any]:
    ranks = [safe_int(item.get("min_rank")) for item in history_rows if safe_int(item.get("min_rank")) > 0]
    if len(ranks) >= 3:
        sorted_ranks = sorted(ranks)
        median_rank = sorted_ranks[len(sorted_ranks) // 2]
        volatility_ratio = (max(ranks) - min(ranks)) / max(median_rank, 1)
        if volatility_ratio > 0.10:
            return {
                "level": "high",
                "label": "大小年位次波动",
                "note": "近年最低位次波动超过 10%，存在大小年风险，需结合当年计划和专业组热度人工复核。",
            }
        if volatility_ratio > 0.05:
            return {
                "level": "medium",
                "label": "位次波动需关注",
                "note": "近年最低位次波动超过 5%，建议不要作为唯一核心保底依据。",
            }

    planned = [(int(item["exam_year"]), safe_int(item.get("planned_count"))) for item in history_rows if safe_int(item.get("planned_count")) > 0]
    if len(planned) < 2:
        return {
            "level": "medium",
            "label": "计划波动待补充",
            "note": "可比招生计划样本不足，当前暂按中性风险处理。",
        }

    planned.sort()
    latest_year, latest_count = planned[-1]
    previous_counts = [count for _, count in planned[:-1]]
    previous_avg = sum(previous_counts) / len(previous_counts)
    diff_ratio = (latest_count - previous_avg) / max(previous_avg, 1)

    if diff_ratio <= -0.35:
        return {
            "level": "high",
            "label": "计划缩减风险",
            "note": f"{latest_year} 年计划人数较历史均值下降明显，需警惕竞争加剧。",
        }
    if diff_ratio <= -0.12:
        return {
            "level": "medium",
            "label": "计划略有收缩",
            "note": f"{latest_year} 年计划人数较历史均值略有下降，建议提高稳妥度。",
        }
    if diff_ratio >= 0.35:
        return {
            "level": "low",
            "label": "计划扩招机会",
            "note": f"{latest_year} 年计划人数较历史均值增加明显，可视为积极信号。",
        }
    return {
        "level": "low",
        "label": "计划基本稳定",
        "note": f"{latest_year} 年计划人数与历史均值接近，计划波动相对可控。",
    }


def _build_candidate_match_result(
    student: dict[str, Any],
    context: dict[str, Any],
    evaluate_subject_requirement,
    limit: int,
) -> dict[str, Any]:
    raw_rows = _fetch_candidate_rows(context)
    history_map = _fetch_history_map(raw_rows, context)
    explicit_rule_map = _fetch_explicit_rule_map(raw_rows, context)
    student_subjects = infer_student_subjects(student)
    track_code = context.get("track_code")
    score = safe_number(context.get("score"))
    rank = safe_int(context.get("rank"))

    candidates: list[dict[str, Any]] = []
    rejected_candidates: list[dict[str, Any]] = []
    for row in raw_rows:
        subject_result = evaluate_subject_requirement(row.get("requirement_text"), student_subjects, track_code)
        if subject_result["status"] == "mismatch":
            rejected_candidates.append(
                _rejection_item(
                    row,
                    context,
                    "选科要求不匹配，当前不建议直接报考。",
                    subject_result=subject_result,
                )
            )
            continue

        rank_result = _evaluate_rank_bucket(rank or None, row)
        score_result = _evaluate_score_bucket(score, row)
        history_rows = history_map.get((int(row["institution_id"]), int(row["major_id"])), [])
        explicit_rules = explicit_rule_map.get((int(row["institution_id"]), int(row["major_id"])), [])
        probability = _summarize_probability(rank or None, score, history_rows)
        final_bucket = _resolve_candidate_bucket(rank_result, score_result, probability)
        if final_bucket == "out":
            rejected_candidates.append(
                _rejection_item(
                    row,
                    context,
                    "与当前分数/位次门槛差距较大，当前批次不建议作为正式志愿。",
                    rank_result=rank_result,
                    score_result=score_result,
                )
            )
            continue
        plan_risk = _summarize_plan_risk(history_rows)
        risks = _collect_risks(row, explicit_rules)
        has_high_risk = any(item["level"] == "high" for item in risks)
        keyword_hits = []
        preference_score = 0
        plan_count = safe_int(row.get("latest_plan_count") or row.get("planned_count"))
        region_bonus = _region_bonus(student, row)
        stability_bonus = 4 if plan_count >= 10 else 0
        composite_score = round(
            subject_result["score"] * 0.28
            + rank_result["score"] * 0.38
            + score_result["score"] * 0.14
            + probability["score"] * 0.12
            + region_bonus
            + stability_bonus,
            1,
        )
        rank_gap = _calculate_rank_gap(rank or None, row)
        score_gap = _calculate_score_gap(score, row)
        city_text = row.get("institution_city") or row.get("institution_province") or "院校所在地区"
        candidate = {
            **row,
            "bucket": final_bucket,
            "bucket_meta": BUCKET_META[final_bucket],
            "subject_result": subject_result,
            "rank_result": rank_result,
            "score_result": score_result,
            "probability": probability,
            "plan_risk": plan_risk,
            "history_rows": history_rows,
            "risks": risks,
            "has_high_risk": has_high_risk,
            "keyword_hits": keyword_hits,
            "preference_score": preference_score,
            "composite_score": max(35.0, min(99.0, composite_score)),
            "city_text": city_text,
            "plan_count": plan_count,
            "rank_gap": rank_gap,
            "score_gap": score_gap,
        }
        candidate["risk_level"] = _candidate_risk_level(candidate)
        candidates.append(candidate)

    prepared = _prepare_recommendation_outputs(candidates, context)
    result_context = dict(context)
    result_context["raw_row_count"] = len(raw_rows)
    return {
        "context": result_context,
        "candidates": prepared["candidates"][:limit],
        "bucketed_candidates": prepared["bucketed_candidates"],
        "recommendation_table": prepared["recommendation_table"],
        "first_choice": prepared["first_choice"],
        "alternatives": prepared["alternatives"],
        "not_recommended": _unique_rejections(rejected_candidates),
    }


def _should_retry_with_score_relaxed_context(context: dict[str, Any]) -> bool:
    if safe_number(context.get("score")) <= 0:
        return False
    if context.get("rank_source") == "score_segments_estimate":
        return True

    latest_year = safe_int(context.get("latest_year"))
    exam_year = safe_int(context.get("exam_year"))
    track_code = str(context.get("track_code") or "")
    return bool(latest_year and exam_year and exam_year > latest_year and track_code in {"physics", "history"})


def _score_relaxed_context(context: dict[str, Any]) -> dict[str, Any]:
    relaxed = dict(context)
    relaxed["rank"] = None
    relaxed["rank_source"] = "score_relaxed_real_data"
    relaxed["candidate_strategy"] = "score_relaxed_real_data"
    return relaxed


def match_admissions_candidates(
    student: dict[str, Any],
    evaluate_subject_requirement,
    limit: int = 180,
) -> dict[str, Any]:
    context = build_admissions_context(student)
    context["candidate_strategy"] = "rank_and_score"
    result = _build_candidate_match_result(student, context, evaluate_subject_requirement, limit)
    if result["candidates"] or not _should_retry_with_score_relaxed_context(context):
        return result

    relaxed_result = _build_candidate_match_result(
        student,
        _score_relaxed_context(context),
        evaluate_subject_requirement,
        limit,
    )
    if relaxed_result["candidates"]:
        return relaxed_result
    return result


def group_major_recommendations(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for candidate in candidates:
        grouped[str(candidate.get("major_name") or "专业方向")].append(candidate)

    rows: list[dict[str, Any]] = []
    for major_name, items in grouped.items():
        items.sort(key=lambda item: item["composite_score"], reverse=True)
        top = items[0]
        sample_schools = [item.get("institution_name") for item in items[:3] if item.get("institution_name")]
        avg_score = round(sum(item["composite_score"] for item in items[:3]) / min(3, len(items)), 1)
        rows.append(
            {
                "title": major_name,
                "type": f"{top.get('degree_level') or '专业'} / {top.get('major_category') or top.get('batch_code') or '招生方向'}",
                "score": int(round(avg_score)),
                "reason": (
                    f"优先命中 {len(items)} 条真实招生记录，当前最佳样本来自 {top.get('institution_name') or '目标院校'}，"
                    f"{top['rank_result']['note']}"
                ),
                "meta": [
                    f"推荐院校：{' / '.join(sample_schools) if sample_schools else '待补充'}",
                    f"选科判断：{top['subject_result']['label']}；{top['subject_result']['note']}",
                    f"近年门槛：最低分 {safe_number(top.get('min_score')) or '待补充'} / 最低位次 {safe_int(top.get('min_rank')) or '待补充'}",
                    f"录取概率：{top['probability']['label']}；{top['probability']['note']}",
                    f"计划风险：{top['plan_risk']['label']}；{top.get('batch_code') or '待补充'} / 计划人数 {top.get('plan_count') or '待补充'}",
                    f"特殊风险：{'；'.join(risk['label'] for risk in top['risks'][:3]) if top['risks'] else '当前未识别到显性特殊限制'}",
                ],
                "tagLabel": top["risks"][0]["label"] if top["has_high_risk"] and top["risks"] else top["bucket_meta"]["tag"],
                "tagVariant": "warning" if top["has_high_risk"] else top["bucket_meta"]["variant"],
                "footer": (
                    f"优先城市：{top.get('city_text')}；排序依据："
                    "选科要求、正式分数位次、历年门槛和计划稳定度"
                ),
            }
        )

    rows.sort(key=lambda item: item["score"], reverse=True)
    return rows


def build_plan_columns_from_candidates(candidates: list[dict[str, Any]], context: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    prepared = _prepare_recommendation_outputs(candidates, context)
    grouped = prepared["bucketed_candidates"]
    tiered = prepared["tiered_candidates"]
    profile = prepared.get("strategy_profile") or resolve_strategy_profile(context.get("admissions_strategy_mode"))
    recommendation_table = prepared["recommendation_table"]
    counts = {bucket: len(items) for bucket, items in grouped.items()}
    tier_counts = {tier["key"]: len(tiered.get(tier["key"], [])) for tier in profile["tiers"]}
    strategy = {
        **bucket_target_ratios(profile["bucket_targets"]),
        "mode": profile["mode"],
        "name": profile["name"],
        "rush_count": counts["rush"],
        "steady_count": counts["steady"],
        "safe_count": counts["safe"],
        "display_tier_counts": tier_counts,
        "display_tiers": [
            {
                "key": tier["key"],
                "bucket": tier["bucket"],
                "target": tier["target"],
                "shortTitle": tier["label"],
                "title": tier["title"],
                "tagLabel": tier["tag"],
                "tagType": tier["variant"],
                "description": tier["description"],
            }
            for tier in profile["tiers"]
        ],
        "total_choice_target": HENAN_2026_TOTAL_CHOICE_TARGET,
        "average_major_score": round(sum(item["compositeScore"] for item in recommendation_table[:6]) / max(1, min(6, len(recommendation_table))), 1) if recommendation_table else 0,
        "note": default_strategy_note(profile["mode"]),
    }

    columns: list[dict[str, Any]] = []
    for tier in profile["tiers"]:
        bucket = str(tier["bucket"])
        cards = []
        for item in tiered.get(tier["key"], []):
            rank_gap = item.get("rank_gap")
            score_gap = item.get("score_gap")
            risk_note = f"重点风险：{'；'.join(risk['label'] for risk in item['risks'][:2])}" if item["risks"] else ""
            adjusted_note = "（由相邻档补位）" if item.get("bucket_adjusted") else ""
            cards.append(
                {
                    "school": item.get("institution_name") or "目标院校",
                    "detail": (
                        f"{item.get('major_name') or '目标专业'} / "
                        f"{item.get('plan_group_code') or item.get('batch_code') or '招生批次'} / "
                        f"{item.get('city_text')}{adjusted_note}"
                    ),
                    "metrics": [
                        f"参考年份：{item.get('exam_year') or context.get('latest_year') or '待补充'}",
                        f"最低分：{safe_number(item.get('min_score')) or '待补充'}",
                        f"最低位次：{safe_int(item.get('min_rank')) or '待补充'}",
                        f"录取概率：{item['probability']['label']}",
                        f"计划人数：{item.get('plan_count') or '待补充'}",
                        f"位次差：{rank_gap if rank_gap is not None else '待补充'}",
                        f"分差：{score_gap if score_gap is not None else '待补充'}",
                        f"风险等级：{RISK_LEVEL_LABELS.get(item.get('risk_level') or 'review', '待复核')}",
                    ],
                    "major": f"选科要求：{item.get('requirement_text') or '待结合院校章程复核'}",
                    "reason": (
                        f"{item['rank_result']['note']} {item['score_result']['note']} {item['plan_risk']['note']}"
                        f"{f' {risk_note}' if risk_note else ''}"
                    ),
                }
            )

        columns.append(
            {
                "key": tier["key"],
                "bucket": bucket,
                "title": tier["title"],
                "note": (
                    f"当前正式推荐 {len(cards)} 条，建议按 {tier['title']} 思路配置志愿，"
                    "并继续复核院校专业组、调剂和计划波动。"
                ),
                "tagLabel": tier["tag"],
                "tagVariant": tier["variant"],
                "cards": cards,
            }
        )

    return columns, strategy
