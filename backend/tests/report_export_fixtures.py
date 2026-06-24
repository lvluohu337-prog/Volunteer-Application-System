from __future__ import annotations

from copy import deepcopy

from backend.compliance import COMPLIANCE_DISCLAIMER, INTERFACE_BOUNDARY_NOTE


_MINIMAL_REPORT_DATA = {
    "reportTitle": "胡祥荟 志愿规划报告",
    "reportSubtitle": "河南 2026 届高考考生 / 399 报告预览",
    "activeProductLabel": "399 元标准版报告",
    "ruleSummary": {
        "scoreLevel": "可冲可稳",
        "scoreComment": "当前有效总分 612，位次 12543，适合采用稳妥型策略。",
        "riskLevel": "medium",
        "riskItems": ["计划波动需要复核", "调剂边界需要确认"],
        "topRisks": ["计划波动需要复核", "调剂边界需要确认"],
        "matchedCount": 48,
        "latestAdmissionYear": 2025,
        "rankSource": "official",
        "strategy": {
            "name": "稳妥型",
            "total_choice_target": 48,
            "note": "险5 / 冲5 / 稳16 / 保12 / 垫5 / 兜5",
        },
        "finalConclusion": "建议采用稳妥型，围绕 48 个院校专业组形成正式方案。第一志愿优先关注 郑州大学 - 自动化类，正式填报前继续复核招生章程、组内专业接受度和调剂边界。",
        "reviewChecklist": [
            "招生章程",
            "组内 6 个专业接受度",
            "是否服从调剂",
            "体检/单科/语种/性别限制",
            "当年招生计划变化",
            "最终志愿系统录入顺序",
        ],
    },
    "resultSource": {
        "mode": "real",
        "label": "真实招生结果",
        "isRealData": True,
        "matchedCandidateCount": 48,
        "rankSource": "official",
        "latestAdmissionYear": 2025,
    },
    "portraitRecommendation": {
        "preferredDirection": "自动化与智能制造",
        "recommendedMajorDirections": ["自动化类", "计算机科学与技术", "电子信息类"],
        "parentConcernMatch": {
            "details": "家庭关注就业稳定性与省内发展路径，本方案优先保留郑州及周边产业资源。"
        },
    },
    "reportJson": {
        "studentSnapshot": {
            "name": "胡祥荟",
            "province": "河南",
            "examYear": 2026,
            "subjectGroup": "物理类",
            "totalScore": 612,
            "rank": 12543,
        }
    },
    "recommendationTable": [
        {
            "bucket": "steady",
            "institutionName": "郑州大学",
            "institutionCode": "10459",
            "majorName": "自动化类",
            "majorCode": "080801",
            "planGroupCode": "Q04",
            "cityText": "郑州",
            "minScore": 612,
            "minRank": 12543,
            "rankGap": "领先 328",
            "riskLabel": "需复核",
            "riskLevel": "review",
            "planRiskLabel": "计划波动需复核",
            "planCount": 6,
            "subjectRequirement": "首选物理，再选化学",
            "subjectLabel": "选科匹配",
            "probabilityLabel": "录取概率中高",
            "recommendationReason": "当前位次与专业方向匹配度较高，可作为主力志愿样本。",
            "riskSummary": "计划波动需要结合当年招生计划复核。",
            "adjustmentAdvice": {
                "label": "可单独沟通",
                "detail": "正式填报前建议单独确认调剂边界。"
            },
            "cityPathNote": "郑州适合继续围绕自动化与智能制造路径做实习和考研规划。"
        }
    ],
    "firstChoice": {
        "bucket": "steady",
        "institutionName": "郑州大学",
        "institutionCode": "10459",
        "majorName": "自动化类",
        "majorCode": "080801",
        "planGroupCode": "Q04",
        "cityText": "郑州",
        "minScore": 612,
        "minRank": 12543,
        "rankGap": "领先 328",
        "riskLabel": "需复核",
        "riskLevel": "review",
        "planRiskLabel": "计划波动需复核",
        "planCount": 6,
        "subjectRequirement": "首选物理，再选化学",
        "subjectLabel": "选科匹配",
        "probabilityLabel": "录取概率中高",
        "recommendationReason": "适合作为第一志愿主力样本。",
        "riskSummary": "需要结合当年招生计划与专业组变化复核。",
        "adjustmentAdvice": {
            "label": "可单独沟通",
            "detail": "建议和家长明确调剂接受边界。"
        },
        "cityPathNote": "郑州路径清晰，适合围绕自动化继续做升学与就业规划。"
    },
    "alternatives": [
        {
            "bucket": "safe",
            "institutionName": "河南工业大学",
            "institutionCode": "10463",
            "majorName": "计算机科学与技术",
            "majorCode": "080901",
            "planGroupCode": "Q12",
            "cityText": "郑州",
            "riskLabel": "相对稳妥",
            "riskLevel": "low",
            "planRiskLabel": "计划基本稳定",
            "planCount": 12,
            "subjectRequirement": "首选物理，再选不限",
            "subjectLabel": "选科匹配",
            "probabilityLabel": "录取概率较稳",
            "recommendationReason": "适合作为备选方案。",
            "riskSummary": "适合承担补位和保底作用，但仍需确认是否接受组内调剂。",
            "adjustmentAdvice": {
                "label": "可单独沟通",
                "detail": "建议把是否接受组内调剂写进最终确认单。"
            }
        }
    ],
    "notRecommended": [
        {
            "institutionName": "某大学",
            "institutionCode": "99999",
            "majorName": "某专业",
            "majorCode": "000000",
            "planGroupCode": "R09",
            "cityText": "外省",
            "minScore": 635,
            "minRank": 8200,
            "reason": "当前位次和专业边界不适合作为优先填报选项。",
            "notes": [
                "当前位次和该专业近年门槛存在明显差距。",
                "若仍想保留，需重新核对选科要求与调剂规则。"
            ]
        }
    ],
    "sections": [
        {
            "title": "学生基本信息",
            "body": "胡祥荟，河南，2026 届高考考生，当前选科/方向为物理类。"
        }
    ],
    "advisorNotes": [
        {
            "note_title": "联调备注",
            "note_content": "导出测试应生成真实 PDF 与 DOCX 文件，而不是中间 HTML 或 Markdown。"
        }
    ],
    "disclaimer": COMPLIANCE_DISCLAIMER,
    "boundaryNote": INTERFACE_BOUNDARY_NOTE,
}


def build_minimal_report_data() -> dict[str, object]:
    return deepcopy(_MINIMAL_REPORT_DATA)
