"""Original IELTS-style writing tasks and speaking prompts."""

WRITING_ACADEMIC = [
    {
        "code": "TASK1",
        "part": 1,
        "title": "Task 1: Household energy use by source, 2000–2020",
        "prompt": (
            "The table below shows the percentage of household energy that came from four sources "
            "in one country in 2000, 2010 and 2020. Summarise the information by selecting and "
            "reporting the main features, and make comparisons where relevant."
        ),
        "data_table": {
            "columns": ["Source", "2000", "2010", "2020"],
            "rows": [
                ["Gas", "52%", "45%", "34%"],
                ["Electricity (grid)", "30%", "33%", "31%"],
                ["Solar", "2%", "9%", "24%"],
                ["Wood/other", "16%", "13%", "11%"],
            ],
        },
        "min_words": 150,
    },
    {
        "code": "TASK2",
        "part": 2,
        "title": "Task 2: Working from home",
        "prompt": (
            "Some people believe that working from home benefits both employees and companies, "
            "while others think it harms teamwork and productivity. Discuss both views and give "
            "your own opinion. Give reasons for your answer and include any relevant examples "
            "from your own knowledge or experience."
        ),
        "min_words": 250,
    },
]

WRITING_GENERAL = [
    {
        "code": "TASK1",
        "part": 1,
        "title": "Task 1: Letter to a neighbour",
        "prompt": (
            "Your neighbour has been doing building work that is causing problems for you. "
            "Write a letter to your neighbour. In your letter: describe the problems; explain how "
            "they are affecting you; suggest what could be done. Begin your letter: Dear ..."
        ),
        "min_words": 150,
    },
    WRITING_ACADEMIC[1],
]

WRITING_PRACTICE = [
    {
        "code": "TASK1",
        "title": "Practice Task 1: Library visitors by age group",
        "prompt": "The chart shows the number of library visitors in three age groups from 2015 to 2023. Summarise the main features.",
        "data_table": {
            "columns": ["Age", "2015", "2023"],
            "rows": [
                ["Under 18", "40k", "55k"],
                ["18–60", "70k", "48k"],
                ["Over 60", "25k", "38k"],
            ],
        },
        "min_words": 150,
    },
    {
        "code": "TASK2",
        "title": "Practice Task 2: Public transport should be free",
        "prompt": "Some people think public transport in cities should be free for everyone. To what extent do you agree or disagree?",
        "min_words": 250,
    },
]

SPEAKING_MOCK_1 = [
    {
        "code": "SP1",
        "part": 1,
        "title": "Part 1: Hometown and free time",
        "questions": [
            "Where is your hometown?",
            "What do you like most about it?",
            "Has it changed much in recent years?",
            "What do you usually do in your free time?",
            "Do you prefer spending free time alone or with others?",
            "Is there a hobby you would like to try in the future?",
        ],
    },
    {
        "code": "SP2",
        "part": 2,
        "title": "Part 2: Describe a skill you learned outside school",
        "cue_card": {
            "topic": "Describe a useful skill you learned outside school.",
            "points": [
                "what the skill is",
                "who taught you or how you learned it",
                "how long it took to learn",
            ],
            "explain": "and explain why this skill is useful to you.",
        },
        "prep_sec": 60,
        "talk_sec": 120,
    },
    {
        "code": "SP3",
        "part": 3,
        "title": "Part 3: Learning and skills",
        "questions": [
            "Which skills do you think schools should teach that they currently don't?",
            "Is it better to learn practical skills from family or from professionals?",
            "How has technology changed the way people learn new skills?",
            "Do you think employers value qualifications more than experience?",
        ],
    },
]

SPEAKING_PRACTICE = [
    {
        "code": "SP1",
        "title": "Practice Part 1: Weather",
        "questions": [
            "What's the weather like where you live?",
            "Do you prefer hot or cold weather?",
            "Does the weather affect your mood?",
        ],
    },
    {
        "code": "SP2",
        "title": "Practice Part 2: Describe a memorable journey",
        "cue_card": {
            "topic": "Describe a journey you remember well.",
            "points": ["where you went", "who you went with", "what happened"],
            "explain": "and explain why you remember it.",
        },
        "prep_sec": 60,
        "talk_sec": 120,
    },
    {
        "code": "SP3",
        "title": "Practice Part 3: Travel and tourism",
        "questions": [
            "Why do people enjoy travelling?",
            "What problems can tourism cause for local communities?",
        ],
    },
]
