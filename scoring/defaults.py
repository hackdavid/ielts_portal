"""Default practice-scoring configuration (copied into ScoringConfig.weights).

Band tables are practice approximations of commonly published conversions,
not official IELTS tables. Rows are [min_raw_out_of_40, band], highest first.
"""

DEFAULT_VERSION = "2026.10.1"

LISTENING_BANDS = [
    [39, 9.0],
    [37, 8.5],
    [35, 8.0],
    [32, 7.5],
    [30, 7.0],
    [26, 6.5],
    [23, 6.0],
    [18, 5.5],
    [16, 5.0],
    [13, 4.5],
    [10, 4.0],
    [8, 3.5],
    [6, 3.0],
    [4, 2.5],
    [2, 2.0],
    [1, 1.0],
    [0, 0.0],
]
READING_ACADEMIC_BANDS = [
    [39, 9.0],
    [37, 8.5],
    [35, 8.0],
    [33, 7.5],
    [30, 7.0],
    [27, 6.5],
    [23, 6.0],
    [19, 5.5],
    [15, 5.0],
    [13, 4.5],
    [10, 4.0],
    [8, 3.5],
    [6, 3.0],
    [4, 2.5],
    [2, 2.0],
    [1, 1.0],
    [0, 0.0],
]
READING_GENERAL_BANDS = [
    [40, 9.0],
    [39, 8.5],
    [37, 8.0],
    [36, 7.5],
    [34, 7.0],
    [32, 6.5],
    [30, 6.0],
    [27, 5.5],
    [23, 5.0],
    [19, 4.5],
    [15, 4.0],
    [12, 3.5],
    [9, 3.0],
    [6, 2.5],
    [3, 2.0],
    [1, 1.0],
    [0, 0.0],
]

COMMON = {
    "multi_mcq_scheme": "right_minus_wrong",
    "reorder_scheme": "adjacent_pairs",
    "hiw_scheme": "right_minus_wrong",
    "wfd_scheme": "lcs_ordered",
    "ignore_articles": True,
    "enforce_word_limit": True,
}

IELTS = {
    **COMMON,
    "scale": "ielts_band",
    "band_raw_total": 40,
    "band_tables": {"listening": LISTENING_BANDS, "reading": READING_ACADEMIC_BANDS},
    "writing_task_weights": {"TASK1": 1, "TASK2": 2},
    "writing_traits": [
        "Task Achievement / Response",
        "Coherence & Cohesion",
        "Lexical Resource",
        "Grammatical Range & Accuracy",
    ],
    "speaking_traits": [
        "Fluency & Coherence",
        "Lexical Resource",
        "Grammatical Range & Accuracy",
        "Pronunciation",
    ],
    "speaking_bytes_per_sec": 2000,
}

PTE = {
    **COMMON,
    "scale": "pte_10_90",
    "item_weights": {},
    "section_weights": {"listening": 1, "reading": 1, "speaking": 1, "writing": 1},
    "pte_scale": {"offset": 10, "factor": 0.8, "min": 10, "max": 90},
    "speaking_traits": {"content": 0.4, "oral_fluency": 0.3, "pronunciation": 0.3},
    "writing_traits": {
        "content": 0.4,
        "form": 0.2,
        "grammar": 0.2,
        "vocabulary": 0.1,
        "spelling": 0.1,
    },
    "enabling": {
        "Oral fluency": ["oral_fluency"],
        "Pronunciation": ["pronunciation"],
        "Grammar": ["grammar"],
        "Vocabulary": ["vocabulary"],
        "Spelling": ["spelling"],
        "Written discourse": ["form", "content"],
    },
    "speaking_bytes_per_sec": 2000,
}


def defaults_for(exam):
    if exam.kind == "ielts":
        weights = {**IELTS, "band_tables": dict(IELTS["band_tables"])}
        if exam.code == "IELTS_GENERAL":
            weights["band_tables"]["reading"] = READING_GENERAL_BANDS
        return weights
    return dict(PTE)
