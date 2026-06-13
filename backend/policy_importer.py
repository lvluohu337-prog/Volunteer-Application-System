from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET

from backend.database import db_session


PROJECT_ROOT = Path(__file__).resolve().parents[1]
HENAN_POLICY_ROOT = PROJECT_ROOT / "河南-2026志愿填报资料" / "1、河南26招生政策汇总【持续更新】"
WORD_NAMESPACE = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


POLICY_DOCUMENTS = [
    {
        "policy_key": "henan_2026_general_regulation",
        "file_name": "河南省2026年普通高等学校招生工作规定.pdf",
        "exam_year": 2026,
        "province": "河南",
        "trend_type": "admission_regulation",
        "impact_scope": "all_candidates",
        "summary_statements": [
            "所有考生均须参加体检，高校可在通用规定基础上补充专业身体条件要求。",
            "正式填报前需结合院校招生章程复核体检、单科、培养方式等补充限制。",
        ],
        "summary_keywords": ["身体健康状况检查", "招生章程", "补充要求", "电子档案", "报名"],
        "rule_mode": "global_only",
        "risk_rules": [
            {
                "risk_type": "charter_review",
                "display_label": "招生章程补充要求",
                "risk_level": "high",
                "trigger": {
                    "match_any": [
                        {"field": "plan_notes", "contains_any": ["招生章程", "详见招生章程", "身体条件"]},
                        {"field": "major_name", "contains_any": ["飞行", "航海", "临床", "公安"]},
                    ]
                },
                "keywords": ["招生章程", "补充要求"],
                "default_message": "省级招生规定明确：高校可在通用体检要求基础上提出补充身体条件要求，正式填报前必须复核院校招生章程。",
                "mitigation_suggestion": "把招生章程中的身体条件、单科要求、培养方式作为最终校验依据。",
            },
            {
                "risk_type": "physical_review",
                "display_label": "体检结果复核",
                "risk_level": "medium",
                "trigger": {
                    "match_any": [
                        {"field": "plan_notes", "contains_any": ["色盲", "色弱", "视力", "身高", "体检"]},
                        {"field": "batch_code", "contains_any": ["提前批"]},
                    ]
                },
                "keywords": ["身体健康状况检查", "体检"],
                "default_message": "省级招生规定要求所有考生参加体检，高校可据章程补充专业身体条件要求；涉及视力、色觉、身高等限制的志愿需重点复核。",
                "mitigation_suggestion": "对涉及身体条件限制的志愿，先核对体检结论，再核对院校章程。",
            },
        ],
    },
    {
        "policy_key": "henan_2025_military_colleges",
        "file_name": "2025年军队院校招生相关事宜及特别提醒.docx",
        "exam_year": 2025,
        "province": "河南",
        "trend_type": "special_batch_rule",
        "impact_scope": "military_colleges",
        "summary_keywords": ["报考条件", "只招英语语种", "政治考核", "面试", "体检", "本科提前批"],
        "rule_mode": "institution_and_global",
        "institution_keywords": ["军队", "军校", "国防", "武警", "飞行学员"],
        "risk_rules": [
            {
                "risk_type": "military_review",
                "display_label": "军校政治考核与面试体检",
                "risk_level": "high",
                "trigger": {
                    "match_any": [
                        {"field": "batch_code", "contains_any": ["军队院校", "飞行学员"]},
                        {"field": "plan_notes", "contains_any": ["军队院校", "军校", "政治考核", "面试", "体检"]},
                    ]
                },
                "keywords": ["政治考核", "面试", "体检"],
                "default_message": "军队院校须通过政治考核、面试和体检，未参加或不合格者不得录取。",
                "mitigation_suggestion": "把政治考核、体检、面试时间节点单独列入填报清单，避免只看分数漏掉资格流程。",
            },
            {
                "risk_type": "military_language",
                "display_label": "军校英语语种限制",
                "risk_level": "high",
                "trigger": {
                    "match_any": [
                        {"field": "batch_code", "contains_any": ["军队院校", "飞行学员"]},
                        {"field": "plan_notes", "contains_any": ["英语语种", "只招英语"]},
                    ]
                },
                "keywords": ["只招英语语种"],
                "default_message": "军队院校政策明确：所有招生专业只招英语语种考生。",
                "mitigation_suggestion": "确认考生外语语种后再保留相关志愿。",
            },
            {
                "risk_type": "military_batch",
                "display_label": "军校提前批规则",
                "risk_level": "medium",
                "trigger": {
                    "match_any": [
                        {"field": "batch_code", "contains_any": ["军队院校", "提前批"]},
                        {"field": "plan_notes", "contains_any": ["本科提前批"]},
                    ]
                },
                "keywords": ["本科提前批", "不得兼报"],
                "default_message": "军队院校安排在本科提前批，填报与投档节奏独立，且不得兼报本科提前批其他类别志愿。",
                "mitigation_suggestion": "把军校志愿单独作为策略方案，不要和普通本科批混在同一套冲稳保里理解。",
            },
        ],
        "institution_rule": {
            "rule_type": "military_charter",
            "rule_title": "军队院校章程级录取要求",
            "keywords": ["政治考核", "面试", "体检", "英语语种", "提前批", "复审复查"],
        },
    },
    {
        "policy_key": "henan_2025_sergeant",
        "file_name": "2025年定向培养军士招生相关事宜及特别提醒.docx",
        "exam_year": 2025,
        "province": "河南",
        "trend_type": "special_batch_rule",
        "impact_scope": "directed_sergeant",
        "summary_keywords": ["定向培养军士", "政治考核", "体格检查", "面试", "定向培养"],
        "rule_mode": "institution_and_global",
        "institution_keywords": ["定向培养军士", "军士"],
        "risk_rules": [
            {
                "risk_type": "sergeant_review",
                "display_label": "定向培养军士资格审核",
                "risk_level": "high",
                "trigger": {
                    "match_any": [
                        {"field": "plan_notes", "contains_any": ["定向培养军士", "政治考核", "面试", "体检"]},
                        {"field": "batch_code", "contains_any": ["定向培养军士"]},
                    ]
                },
                "keywords": ["政治考核", "面试", "体格检查"],
                "default_message": "定向培养军士需通过政治考核、面试和体格检查，资格审核未通过不能进入录取。",
                "mitigation_suggestion": "把资格审核流程和后续培养约束单独向家长解释清楚。",
            },
            {
                "risk_type": "sergeant_commitment",
                "display_label": "定向培养与履约约束",
                "risk_level": "high",
                "trigger": {
                    "match_any": [
                        {"field": "plan_notes", "contains_any": ["定向培养军士", "定向"]},
                        {"field": "batch_code", "contains_any": ["定向培养军士"]},
                    ]
                },
                "keywords": ["定向培养军士", "培养"],
                "default_message": "定向培养军士属于带有明确培养和后续履约要求的特殊志愿，不适合把它当作普通专科替代项。",
                "mitigation_suggestion": "正式填报前确认家庭是否接受后续服役和培养管理要求。",
            },
        ],
        "institution_rule": {
            "rule_type": "sergeant_charter",
            "rule_title": "定向培养军士章程级要求",
            "keywords": ["政治考核", "面试", "体检", "定向培养"],
        },
    },
    {
        "policy_key": "henan_2025_special_plan",
        "file_name": "我省2025年重点高校招生专项计划报名资格审核工作启动.docx",
        "exam_year": 2025,
        "province": "河南",
        "trend_type": "eligibility_rule",
        "impact_scope": "special_plan_candidates",
        "summary_statements": [
            "国家专项、高校专项、地方专项都以资格审核通过为前提，不能按普通志愿理解。",
            "专项计划通常同时要求户籍、学籍、实际就读地等条件符合官方范围。",
        ],
        "summary_keywords": ["专项计划", "报名资格审核", "资格审核"],
        "rule_mode": "global_only",
        "risk_rules": [
            {
                "risk_type": "special_plan_eligibility",
                "display_label": "专项计划资格审核",
                "risk_level": "high",
                "trigger": {
                    "match_any": [
                        {"field": "batch_code", "contains_any": ["国家专项", "高校专项", "地方专项", "专项计划"]},
                        {"field": "plan_notes", "contains_any": ["专项计划", "高校专项", "国家专项", "地方专项"]},
                    ]
                },
                "keywords": ["资格审核", "专项计划"],
                "default_message": "专项计划志愿以资格审核通过为前提，未通过资格审核即使分数满足也不能录取。",
                "mitigation_suggestion": "先确认专项资格再保留专项志愿，避免把专项志愿误当普通志愿。",
            },
        ],
    },
    {
        "policy_key": "henan_2025_high_level_sports",
        "file_name": "河南2025年高校专项、高水平运动队招生专业信息.pdf",
        "exam_year": 2025,
        "province": "河南",
        "trend_type": "special_talent_rule",
        "impact_scope": "high_level_sports_candidates",
        "summary_statements": [
            "高水平运动队属于特殊类型招生，需结合公布专业范围、专项资格和测试要求判断。",
            "不能把高水平运动队志愿当作普通本科志愿替代项，文化课与专项条件都要同时满足。",
        ],
        "summary_keywords": ["高水平运动队", "招生专业", "专项"],
        "rule_mode": "global_only",
        "risk_rules": [
            {
                "risk_type": "high_level_sports_qualification",
                "display_label": "高水平运动队资格要求",
                "risk_level": "high",
                "trigger": {
                    "match_any": [
                        {"field": "plan_notes", "contains_any": ["高水平运动队"]},
                        {"field": "batch_code", "contains_any": ["高水平运动队"]},
                    ]
                },
                "keywords": ["高水平运动队"],
                "default_message": "高水平运动队属于特殊类型招生，须满足专项资格和测试要求，不能按普通志愿理解。",
                "mitigation_suggestion": "把资格审核、测试结果和文化课要求一起纳入最终判断。",
            },
        ],
    },
    {
        "policy_key": "henan_2025_police",
        "file_name": "河南省2025年公安院校公安专业招生有关事项提醒.docx",
        "exam_year": 2025,
        "province": "河南",
        "trend_type": "special_batch_rule",
        "impact_scope": "police_colleges",
        "summary_keywords": ["公安院校", "公安专业", "政治考察", "面试", "体检", "体能测评"],
        "rule_mode": "institution_and_global",
        "institution_keywords": ["公安", "警察", "司法警官"],
        "risk_rules": [
            {
                "risk_type": "police_review",
                "display_label": "公安类政审面试体检体测",
                "risk_level": "high",
                "trigger": {
                    "match_any": [
                        {"field": "institution_name", "contains_any": ["公安", "警察"]},
                        {"field": "plan_notes", "contains_any": ["公安", "政治考察", "体能测评", "面试", "体检"]},
                    ]
                },
                "keywords": ["政治考察", "面试", "体检", "体能测评"],
                "default_message": "公安院校公安专业通常叠加政治考察、面试、体检和体能测评，不能只按文化分判断。",
                "mitigation_suggestion": "正式填报前逐项确认政审、体测和身体条件要求。",
            },
            {
                "risk_type": "police_physical",
                "display_label": "公安类身体条件限制",
                "risk_level": "high",
                "trigger": {
                    "match_any": [
                        {"field": "institution_name", "contains_any": ["公安", "警察"]},
                        {"field": "plan_notes", "contains_any": ["身高", "视力", "色觉", "体检"]},
                    ]
                },
                "keywords": ["体检", "身体条件"],
                "default_message": "公安类专业对视力、色觉、身高等身体条件通常有更严格要求。",
                "mitigation_suggestion": "体检结论边缘的学生不要把公安类院校作为唯一稳妥方案。",
            },
        ],
        "institution_rule": {
            "rule_type": "police_charter",
            "rule_title": "公安专业章程级审核要求",
            "keywords": ["政治考察", "面试", "体检", "体能测评"],
        },
    },
    {
        "policy_key": "henan_2025_tibet_employment",
        "file_name": "河南省2025年普通高校招生非西藏生源定向西藏就业计划报考资格审核工作有关事项提醒.docx",
        "exam_year": 2025,
        "province": "河南",
        "trend_type": "eligibility_rule",
        "impact_scope": "tibet_employment_plan",
        "summary_keywords": ["定向西藏就业", "资格审核", "报考资格"],
        "rule_mode": "global_only",
        "risk_rules": [
            {
                "risk_type": "tibet_eligibility",
                "display_label": "定向西藏就业资格审核",
                "risk_level": "high",
                "trigger": {
                    "match_any": [
                        {"field": "plan_notes", "contains_any": ["西藏就业", "定向西藏"]},
                        {"field": "batch_code", "contains_any": ["西藏"]},
                    ]
                },
                "keywords": ["资格审核", "定向西藏就业"],
                "default_message": "非西藏生源定向西藏就业计划属于资格审核型志愿，需先满足报考资格与后续就业约束。",
                "mitigation_suggestion": "确认家庭能接受定向就业安排后再保留相关志愿。",
            },
        ],
    },
    {
        "policy_key": "henan_2026_registration_faq",
        "file_name": "河南省2026年普通高招报名工作相关事宜问答.docx",
        "exam_year": 2026,
        "province": "河南",
        "trend_type": "registration_rule",
        "impact_scope": "special_admission_candidates",
        "summary_statements": [
            "高招报名实行网上报名与现场确认结合，资格审核贯穿全流程。",
            "单招、运动训练、保送等特殊类型招生只有在完成统一报名和资格审核后才具备报考基础。",
        ],
        "summary_keywords": ["报名资格审核", "高职单招", "运动训练", "资格审核", "现场确认"],
        "rule_mode": "global_only",
        "risk_rules": [
            {
                "risk_type": "special_registration_review",
                "display_label": "特殊类型招生报名资格复核",
                "risk_level": "high",
                "trigger": {
                    "match_any": [
                        {"field": "batch_code", "contains_any": ["单招", "运动训练", "武术", "保送", "消防救援"]},
                        {"field": "plan_notes", "contains_any": ["高职单招", "运动训练", "武术与民族传统体育", "保送", "消防救援"]},
                    ]
                },
                "keywords": ["报名资格审核", "高职单招", "运动训练", "武术与民族传统体育专业单招"],
                "default_message": "特殊类型招生并非只满足分数即可报考，还要求考生已完成全省统一报名、现场确认和资格审核。",
                "mitigation_suggestion": "遇到单招、运动训练、武术类或其他特殊招生项目时，先复核报名类别与资格审核状态，再保留志愿。",
            },
        ],
    },
    {
        "policy_key": "henan_2026_sports_exam",
        "file_name": "河南省2026年普通高校招生体育类专业招生考试相关事宜提醒.docx",
        "exam_year": 2026,
        "province": "河南",
        "trend_type": "professional_exam_rule",
        "impact_scope": "sports_candidates",
        "summary_statements": [
            "体育类志愿需同时看专业测试、文化成绩和提前批投档规则，不能只按普通分数线判断。",
            "体育类提前批志愿不得兼报同批次其他类别，正式方案要单独核算。",
        ],
        "summary_keywords": ["体育类专业", "招生考试", "考试"],
        "rule_mode": "global_only",
        "risk_rules": [
            {
                "risk_type": "sports_exam",
                "display_label": "体育类专业考试要求",
                "risk_level": "high",
                "trigger": {
                    "match_any": [
                        {"field": "batch_code", "contains_any": ["体育"]},
                        {"field": "major_name", "contains_any": ["体育"]},
                    ]
                },
                "keywords": ["体育类专业", "考试"],
                "default_message": "体育类专业需同时满足专业考试与文化成绩规则，不能按普通文化类专业理解。",
                "mitigation_suggestion": "将专业考试成绩、合格线和文化课要求一并纳入风险判断。",
            },
            {
                "risk_type": "sports_score_structure",
                "display_label": "体育类文化课与专业成绩并行",
                "risk_level": "medium",
                "trigger": {
                    "match_any": [
                        {"field": "batch_code", "contains_any": ["体育"]},
                        {"field": "major_name", "contains_any": ["体育"]},
                    ]
                },
                "keywords": ["体育类专业", "招生考试", "考试"],
                "default_message": "体育类志愿的录取判断需要同时看专业测试和文化课，不适合只按普通分数线理解“稳妥”程度。",
                "mitigation_suggestion": "把体育专业测试表现、文化课达线情况和批次投档办法放在同一张核验清单里复核。",
            },
        ],
    },
    {
        "policy_key": "henan_2026_arts_exam",
        "file_name": "河南省2026年普通高校招生艺术类专业考试有关事宜的说明.docx",
        "exam_year": 2026,
        "province": "河南",
        "trend_type": "professional_exam_rule",
        "impact_scope": "arts_candidates",
        "summary_statements": [
            "艺术类招生按不同科类分别组织考试与投档，不能把一个类别的结果直接套到所有艺术志愿上。",
            "艺术类志愿仍需同步满足报名、体检、文化课考试和对应专业类别要求。",
        ],
        "summary_keywords": ["艺术类专业", "考试", "艺术类"],
        "rule_mode": "global_only",
        "risk_rules": [
            {
                "risk_type": "arts_exam",
                "display_label": "艺术类专业考试要求",
                "risk_level": "high",
                "trigger": {
                    "match_any": [
                        {"field": "batch_code", "contains_any": ["艺术"]},
                        {"field": "major_name", "contains_any": ["艺术", "设计", "音乐", "美术", "舞蹈"]},
                    ]
                },
                "keywords": ["艺术类专业", "考试"],
                "default_message": "艺术类专业录取同时依赖专业考试与文化成绩规则，填报前需复核对应类别的考试与投档办法。",
                "mitigation_suggestion": "把专业合格情况与文化分同时作为保留艺术志愿的前提。",
            },
            {
                "risk_type": "arts_category_alignment",
                "display_label": "艺术类专业类别匹配",
                "risk_level": "medium",
                "trigger": {
                    "match_any": [
                        {"field": "batch_code", "contains_any": ["艺术"]},
                        {"field": "major_name", "contains_any": ["艺术", "设计", "音乐", "美术", "舞蹈"]},
                    ]
                },
                "keywords": ["艺术类专业", "考试", "艺术类"],
                "default_message": "艺术类不同专业类别的考试办法、合格要求和投档规则可能不同，不能把一个类别的结果直接套到所有艺术志愿上。",
                "mitigation_suggestion": "逐个核对专业所属艺术类别、专业合格状态和对应投档办法，避免跨类别误判。",
            },
        ],
    },
    {
        "policy_key": "henan_2025_single_exam",
        "file_name": "河南省教育厅关于做好2025年高等职业教育单独考试招生和技能拔尖人才免试入学工作的通知- 文件通知 - 河南省教育厅.pdf",
        "exam_year": 2025,
        "province": "河南",
        "trend_type": "special_batch_rule",
        "impact_scope": "single_exam_candidates",
        "summary_statements": [
            "高职单招仅在获批高校范围内实施，且专业范围、考试方式和章程差异明显。",
            "高职单招通常还要结合职业技能测试或职业适应性测试，不能按普通批多志愿逻辑理解。",
        ],
        "summary_keywords": ["高职单招", "招生章程", "志愿填报", "职业技能测试", "免文化素质考试"],
        "rule_mode": "global_only",
        "risk_rules": [
            {
                "risk_type": "single_exam_one_choice",
                "display_label": "高职单招仅限单校志愿",
                "risk_level": "high",
                "trigger": {
                    "match_any": [
                        {"field": "batch_code", "contains_any": ["单招"]},
                        {"field": "plan_notes", "contains_any": ["高职单招", "单独考试招生"]},
                    ]
                },
                "keywords": ["志愿填报", "高职单招"],
                "default_message": "高职单招通常只能填报一所高校志愿，且修改次数和填报时间窗口都很有限，不能按普通批多志愿逻辑理解。",
                "mitigation_suggestion": "把高职单招单独做成一套方案，先确认唯一志愿选择和时间节点，再决定是否保留。",
            },
            {
                "risk_type": "single_exam_skill_test",
                "display_label": "高职单招职业技能测试要求",
                "risk_level": "high",
                "trigger": {
                    "match_any": [
                        {"field": "batch_code", "contains_any": ["单招"]},
                        {"field": "plan_notes", "contains_any": ["高职单招", "职业技能测试", "职业适应性测试"]},
                    ]
                },
                "keywords": ["职业技能测试", "职业适应性测试", "文化素质"],
                "default_message": "高职单招不是只看文化课，通常还要参加职业技能测试或职业适应性测试，且技能测试分值占比较高。",
                "mitigation_suggestion": "正式保留高职单招志愿前，先核对目标院校章程中的测试方式、考试时间和成绩构成。",
            },
            {
                "risk_type": "single_exam_charter_review",
                "display_label": "高职单招章程差异大",
                "risk_level": "medium",
                "trigger": {
                    "match_any": [
                        {"field": "batch_code", "contains_any": ["单招"]},
                        {"field": "plan_notes", "contains_any": ["高职单招", "招生章程"]},
                    ]
                },
                "keywords": ["招生章程", "考试科目", "录取规则"],
                "default_message": "高职单招章程会分别写明考试科目、录取规则、学费与资助政策，学校之间差异较大，不能简单套用同类院校经验。",
                "mitigation_suggestion": "把目标院校的单招章程作为最终依据，逐项复核考试科目、录取规则、学费和资助说明。",
            },
        ],
    },
    {
        "policy_key": "henan_2026_counterpart_work",
        "file_name": "河南省教育厅关于做好2026年普通高等学校对口招收中等职业学校毕业生工作的通知- 文件通知 - 河南省教育厅.pdf",
        "exam_year": 2026,
        "province": "河南",
        "trend_type": "special_batch_rule",
        "impact_scope": "counterpart_candidates",
        "summary_statements": [
            "对口招生要求中职学籍、报名资格和专业对照关系同时成立，不能作为普通高考平替方案。",
            "对口体育类、艺术类等专业还要结合专项考试与对应投档规则单独判断。",
        ],
        "summary_keywords": ["对口招生", "报名资格审核", "专业对照", "体育类专业", "音乐与舞蹈类专业", "美术与设计类专业"],
        "rule_mode": "global_only",
        "risk_rules": [
            {
                "risk_type": "counterpart_eligibility",
                "display_label": "对口招生资格审核",
                "risk_level": "high",
                "trigger": {
                    "match_any": [
                        {"field": "batch_code", "contains_any": ["对口"]},
                        {"field": "plan_notes", "contains_any": ["对口招生", "中等职业学校毕业生"]},
                    ]
                },
                "keywords": ["报名资格审核", "中等职业学校学籍", "资格审核贯穿全过程"],
                "default_message": "对口招生不是普通高考平替，考生必须具备对应中职学籍与报名资格，且资格审核贯穿报名、考试和录取全过程。",
                "mitigation_suggestion": "保留对口志愿前先核对学籍状态、报名类别和资格审核结论，避免后续被取消资格。",
            },
            {
                "risk_type": "counterpart_major_alignment",
                "display_label": "对口招生专业对照要求",
                "risk_level": "high",
                "trigger": {
                    "match_any": [
                        {"field": "batch_code", "contains_any": ["对口"]},
                        {"field": "plan_notes", "contains_any": ["对口招生", "专业对照"]},
                    ]
                },
                "keywords": ["专业对照", "所学专业与报考专业应符合"],
                "default_message": "对口招生要求考生所学中职专业与报考高校专业满足官方专业对照关系，不是所有中职专业都能自由跨报。",
                "mitigation_suggestion": "先对照官方专业对照表确认可报专业范围，再做冲稳保筛选。",
            },
            {
                "risk_type": "counterpart_sports_exam",
                "display_label": "对口体育类专项考试",
                "risk_level": "high",
                "trigger": {
                    "match_any": [
                        {"field": "batch_code", "contains_any": ["对口", "体育"]},
                        {"field": "major_name", "contains_any": ["体育"]},
                    ]
                },
                "keywords": ["体育类专业", "身体素质", "统一考试"],
                "default_message": "对口体育类专业除文化课外，还要按统一标准完成身体素质测试，录取判断不能只看文化分。",
                "mitigation_suggestion": "对口体育志愿要把身体素质项目、文化课和统一考试标准放在一起评估。",
            },
            {
                "risk_type": "counterpart_arts_exam",
                "display_label": "对口艺术类专项考试",
                "risk_level": "high",
                "trigger": {
                    "match_any": [
                        {"field": "batch_code", "contains_any": ["对口"]},
                        {"field": "major_name", "contains_any": ["音乐", "舞蹈", "美术", "设计", "艺术"]},
                    ]
                },
                "keywords": ["音乐与舞蹈类专业", "美术与设计类专业", "专业主科"],
                "default_message": "对口艺术类专业通常还包含视唱、专业主科或造型基础等专项考试，不能把普通文化类位次直接套用到这类志愿上。",
                "mitigation_suggestion": "逐项核对艺术类别、专项考试科目与分值，再判断该志愿是否还能保留在正式方案中。",
            },
        ],
    },
    {
        "policy_key": "henan_2026_counterpart_faq",
        "file_name": "河南省2026年普通高等学校对口招收中等职业学校毕业生工作相关事宜问答.docx",
        "exam_year": 2026,
        "province": "河南",
        "trend_type": "registration_rule",
        "impact_scope": "counterpart_candidates",
        "summary_statements": [
            "对口招生报名实行网上采集与现场确认结合，只有具备河南中职学籍的应届毕业生才能按要求报名。",
            "对口志愿实行本科6个、专科12个平行院校志愿，并需同步复核体检、专业考试和资格条件申报。",
        ],
        "summary_keywords": ["对口招生", "网上信息采集", "现场确认", "资格条件申报", "平行志愿"],
        "rule_mode": "global_only",
        "risk_rules": [],
    },
]


def _normalize_text(value: str | None) -> str:
    text = (value or "").replace("\u3000", " ").strip()
    return re.sub(r"[ \t]+", " ", text)


def _is_noise_line(text: str) -> bool:
    normalized = _normalize_text(text)
    if not normalized:
        return True
    noise_tokens = (
        "用户中心",
        "中国政府网",
        "教育部",
        "河南省政府网",
        "设为首页",
        "加入收藏",
        "进入适老模式",
        "无障碍阅读",
        "首页 >",
        "分享：",
        "浏览字号",
        "来源：",
        "首页",
        "首 页",
        "教育动态",
        "政务公开",
        "政务服务",
        "交流互动",
        "专题子站",
    )
    return any(token in normalized for token in noise_tokens)


def _compact_lines(text: str) -> list[str]:
    return [
        _normalize_text(line)
        for line in text.splitlines()
        if _normalize_text(line) and not _is_noise_line(line)
    ]


def _extract_docx_text(path: Path) -> str:
    with ZipFile(path) as zip_file:
        document_xml = zip_file.read("word/document.xml")
    root = ET.fromstring(document_xml)
    paragraphs: list[str] = []
    for paragraph in root.findall(".//w:p", WORD_NAMESPACE):
        parts = [node.text or "" for node in paragraph.findall(".//w:t", WORD_NAMESPACE)]
        text = _normalize_text("".join(parts))
        if text:
            paragraphs.append(text)
    return "\n".join(paragraphs)


def _extract_pdf_text(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        fallback_paths = [
            os.environ.get("POLICY_IMPORT_PYPDF_PATH"),
            str(PROJECT_ROOT / "data_assets" / "vendor"),
        ]
        for extra_path in fallback_paths:
            if not extra_path or extra_path in sys.path:
                continue
            sys.path.insert(0, extra_path)
            try:
                from pypdf import PdfReader
            except ImportError:
                continue
            reader = PdfReader(str(path))
            return "\n".join(_normalize_text(page.extract_text() or "") for page in reader.pages)
        raise RuntimeError(
            "导入 PDF 政策文件需要 pypdf；请使用带 pypdf 的运行环境执行导入脚本。"
        ) from exc

    reader = PdfReader(str(path))
    return "\n".join(_normalize_text(page.extract_text() or "") for page in reader.pages)


def extract_policy_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".docx":
        return _extract_docx_text(path)
    if suffix == ".pdf":
        return _extract_pdf_text(path)
    raise ValueError(f"Unsupported policy file type: {path}")


def locate_policy_documents() -> dict[str, Path]:
    located: dict[str, Path] = {}
    if not HENAN_POLICY_ROOT.exists():
        return located

    for item in POLICY_DOCUMENTS:
        path = HENAN_POLICY_ROOT / item["file_name"]
        if path.exists():
            located[item["policy_key"]] = path
    return located


def _pick_snippets(text: str, keywords: list[str], limit: int = 3) -> list[str]:
    lines = _compact_lines(text)
    hits: list[str] = []
    seen = set()
    for keyword in keywords:
        for line in lines:
            if keyword in line and line not in seen:
                hits.append(line)
                seen.add(line)
                if len(hits) >= limit:
                    return hits
    for line in lines:
        if line not in seen:
            hits.append(line)
            if len(hits) >= limit:
                break
    return hits


def _clean_snippet(text: str) -> str:
    normalized = _normalize_text(text)
    if not normalized:
        return ""

    normalized = re.sub(r"^[一二三四五六七八九十0-9]+[\.、]\s*", "", normalized)
    normalized = normalized.strip("；;，,。:：")
    banned_prefixes = (
        "的说明和解释",
        "以下简称",
        "发布日期",
        "您好，今天是",
    )
    for prefix in banned_prefixes:
        if normalized.startswith(prefix):
            return ""

    if len(normalized) < 8 and not re.search(r"\d", normalized):
        return ""
    return normalized


def _clean_snippets(snippets: list[str], limit: int = 3) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for snippet in snippets:
        normalized = _clean_snippet(snippet)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        cleaned.append(normalized)
        if len(cleaned) >= limit:
            break
    return cleaned


def _build_trigger_text(trigger: dict[str, object] | None) -> str | None:
    if not trigger:
        return None
    return json.dumps(trigger, ensure_ascii=False, separators=(",", ":"))


def _summary_from_doc(document: dict[str, object], text: str) -> str:
    preferred = _clean_snippets(
        [str(item or "") for item in list(document.get("summary_statements") or [])],
        limit=3,
    )
    if preferred:
        return "；".join(preferred[:3])
    snippets = _clean_snippets(_pick_snippets(text, list(document.get("summary_keywords") or []), limit=5), limit=3)
    if snippets:
        return "；".join(snippets[:3])
    return str(document.get("policy_key") or "政策摘要待补充")


def _rule_message(document: dict[str, object], rule: dict[str, object], text: str) -> str:
    default_message = _normalize_text(str(rule.get("default_message") or ""))
    if default_message:
        return default_message
    snippets = _clean_snippets(_pick_snippets(text, list(rule.get("keywords") or []), limit=4), limit=2)
    if snippets:
        return "；".join(snippets[:2])
    return _summary_from_doc(document, text)


def _find_matching_institutions(province: str, keywords: list[str]) -> list[dict[str, object]]:
    if not keywords:
        return []

    clauses: list[str] = []
    params: list[object] = [province]
    for keyword in keywords:
        like = f"%{keyword}%"
        clauses.append(
            """
            LOWER(COALESCE(i.institution_name, '')) LIKE LOWER(?)
            OR LOWER(COALESCE(ap.plan_notes, '')) LIKE LOWER(?)
            OR LOWER(COALESCE(ap.batch_code, '')) LIKE LOWER(?)
            """
        )
        params.extend([like, like, like])

    with db_session() as connection:
        rows = connection.execute(
            f"""
            SELECT DISTINCT i.id, i.institution_code, i.institution_name
            FROM institutions i
            LEFT JOIN admission_plans ap
              ON ap.institution_id = i.id
             AND ap.province = ?
            WHERE {' OR '.join(f'({item})' for item in clauses)}
            ORDER BY i.institution_name
            """,
            params,
        ).fetchall()
    return [dict(row) for row in rows]


def _build_policy_row(document: dict[str, object], path: Path, text: str, matched_count: int) -> dict[str, object]:
    return {
        "exam_year": document["exam_year"],
        "province": document["province"],
        "policy_key": document["policy_key"],
        "policy_title": path.name,
        "trend_type": document.get("trend_type"),
        "trend_summary": _summary_from_doc(document, text),
        "impact_scope": document.get("impact_scope"),
        "source_url": str(path),
        "notes": f"命中院校 {matched_count} 所；由河南政策/章程资料自动抽取。",
        "source_excerpt": _pick_snippets(text, list(document.get("summary_keywords") or []), limit=4),
    }


def _build_risk_rows(document: dict[str, object], path: Path, text: str) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for rule in document.get("risk_rules", []):
        source_excerpt = _clean_snippets(_pick_snippets(text, list(rule.get("keywords") or []), limit=4), limit=2)
        rows.append(
            {
                "exam_year": document["exam_year"],
                "province": document["province"],
                "institution_id": None,
                "major_id": None,
                "risk_type": rule["risk_type"],
                "risk_level": rule.get("risk_level"),
                "trigger_condition": _build_trigger_text(rule.get("trigger")),
                "risk_message": _rule_message(document, rule, text),
                "mitigation_suggestion": rule.get("mitigation_suggestion"),
                "display_label": rule.get("display_label"),
                "source_url": str(path),
                "policy_key": document["policy_key"],
                "policy_topic": path.stem,
                "source_excerpt": source_excerpt,
            }
        )
    return rows


def _build_institution_rule_rows(
    document: dict[str, object],
    path: Path,
    text: str,
    matched_institutions: list[dict[str, object]],
) -> list[dict[str, object]]:
    config = document.get("institution_rule")
    if not config or not matched_institutions:
        return []

    content = "；".join(_pick_snippets(text, list(config.get("keywords") or []), limit=4))
    if not content:
        content = _summary_from_doc(document, text)

    rows: list[dict[str, object]] = []
    for institution in matched_institutions:
        rows.append(
            {
                "exam_year": document["exam_year"],
                "province": document["province"],
                "institution_id": institution["id"],
                "institution_code": institution.get("institution_code"),
                "institution_name": institution.get("institution_name"),
                "rule_type": config["rule_type"],
                "rule_title": config.get("rule_title"),
                "rule_content": content,
                "source_url": str(path),
                "notes": f"基于 {path.name} 自动归纳的章程级风险摘要。",
                "policy_key": document["policy_key"],
                "policy_topic": path.stem,
                "source_excerpt": _clean_snippets(_pick_snippets(text, list(config.get("keywords") or []), limit=4), limit=2),
            }
        )
    return rows


def load_henan_policy_rule_datasets(limit_documents: int | None = None) -> dict[str, list[dict[str, object]]]:
    located = locate_policy_documents()
    policy_rows: list[dict[str, object]] = []
    risk_rows: list[dict[str, object]] = []
    institution_rule_rows: list[dict[str, object]] = []

    loaded = 0
    for document in POLICY_DOCUMENTS:
        if limit_documents is not None and loaded >= limit_documents:
            break

        path = located.get(document["policy_key"])
        if not path:
            continue

        text = extract_policy_text(path)
        matched_institutions = _find_matching_institutions(
            str(document["province"]),
            list(document.get("institution_keywords") or []),
        ) if document.get("rule_mode") == "institution_and_global" else []

        policy_rows.append(_build_policy_row(document, path, text, len(matched_institutions)))
        risk_rows.extend(_build_risk_rows(document, path, text))
        institution_rule_rows.extend(
            _build_institution_rule_rows(document, path, text, matched_institutions)
        )
        loaded += 1

    return {
        "policy_trends": policy_rows,
        "admission_risk_rules": risk_rows,
        "institution_rules": institution_rule_rows,
    }
