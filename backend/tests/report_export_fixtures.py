from __future__ import annotations

from copy import deepcopy


_MINIMAL_REPORT_DATA = {
    "reportTitle": "胡祥荟 志愿规划报告",
    "reportSubtitle": "河南 2026 届高考考生 / 399 报告预览",
    "activeProductLabel": "399 咨询版",
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
    "disclaimer": "本报告为高考志愿规划辅助建议，不承诺任何录取结果。"
}


def build_minimal_report_data() -> dict[str, object]:
    return deepcopy(_MINIMAL_REPORT_DATA)
