"""Original IELTS-style listening sets (scripts are server-only)."""

LISTENING_MOCK_1 = [
    {
        "code": "L_FORM",
        "part": 1,
        "title": "Riverside Community Centre booking form",
        "instructions": "Complete the form below. Write ONE WORD AND/OR A NUMBER for each answer.",
        "word_limit": 1,
        "context": "Riverside Community Centre – Room Booking",
        "items": [
            {"n": 1, "text": "Name of organiser: Maria ____"},
            {"n": 2, "text": "Type of event: ____ class"},
            {"n": 3, "text": "Day: every ____"},
            {"n": 4, "text": "Start time: ____ pm"},
            {"n": 5, "text": "Number of people expected: ____"},
            {"n": 6, "text": "Equipment needed: a ____ system"},
        ],
        "answers": {
            "1": ["Delgado"],
            "2": ["pottery"],
            "3": ["Thursday"],
            "4": ["7", "seven"],
            "5": ["18", "eighteen"],
            "6": ["sound"],
        },
        "transcript": "Receptionist and caller booking a room. The caller, Maria Delgado (D-E-L-G-A-D-O), wants a room for a weekly pottery class on Thursdays from 7 pm for about 18 people and asks for a sound system.",
    },
    {
        "code": "L_MCQ",
        "part": 1,
        "title": "Riverside Community Centre – extra details",
        "instructions": "Choose the correct letter, A, B or C.",
        "items": [
            {
                "n": 7,
                "text": "The room Maria books is on the",
                "options": ["A ground floor", "B first floor", "C second floor"],
            },
            {
                "n": 8,
                "text": "The weekly price includes",
                "options": ["A cleaning", "B parking", "C refreshments"],
            },
            {
                "n": 9,
                "text": "Maria must pay the deposit",
                "options": ["A today", "B by Friday", "C on the first day"],
            },
            {
                "n": 10,
                "text": "Maria will receive confirmation by",
                "options": ["A post", "B text message", "C email"],
            },
        ],
        "answers": {"7": "A", "8": "A", "9": "B", "10": "C"},
        "transcript": "The ground-floor studio is offered; cleaning is included but parking is extra; the deposit is due by Friday; confirmation will be emailed.",
    },
    {
        "code": "L_MAP",
        "part": 2,
        "title": "Greenhill Park visitor map",
        "instructions": "Label the map. Choose the correct letter, A–G.",
        "context": "Map of Greenhill Park with locations A–G around the lake.",
        "items": [
            {"n": n, "text": t, "options": list("ABCDEFG")}
            for n, t in [
                (11, "Café"),
                (12, "Bike hire"),
                (13, "Children's playground"),
                (14, "Bird hide"),
                (15, "First-aid point"),
            ]
        ],
        "answers": {"11": "C", "12": "A", "13": "F", "14": "E", "15": "B"},
        "transcript": "A park ranger describes the new layout: bike hire beside the main gate (A), first aid next to it (B), the café overlooking the lake (C), the bird hide on the north shore (E) and the playground near the west exit (F).",
    },
    {
        "code": "L_MATCH",
        "part": 2,
        "title": "Greenhill Park volunteer roles",
        "instructions": "What does the ranger say about each volunteer role? Choose FIVE answers from the box, A–G.",
        "context": "A suits families  B needs training  C is at weekends only  D involves early mornings  E is indoors  F needs a car  G is new this year",
        "items": [
            {"n": n, "text": t, "options": list("ABCDEFG")}
            for n, t in [
                (16, "Tree planting"),
                (17, "Bird counting"),
                (18, "Visitor centre help"),
                (19, "Litter patrol"),
                (20, "Guided walks"),
            ]
        ],
        "answers": {"16": "C", "17": "D", "18": "E", "19": "A", "20": "B"},
        "transcript": "Tree planting only happens at weekends; bird counts start at dawn; the visitor centre role is indoors; families often do litter patrol; walk leaders attend a training day.",
    },
    {
        "code": "L_MCQ",
        "part": 3,
        "title": "Students planning a transport survey",
        "instructions": "Choose the correct letter, A, B or C.",
        "items": [
            {
                "n": 21,
                "text": "Why did Tom and Aisha choose this topic?",
                "options": [
                    "A Their tutor suggested it",
                    "B It affects their own journeys",
                    "C There is little research on it",
                ],
            },
            {
                "n": 22,
                "text": "They decide to collect data by",
                "options": [
                    "A online questionnaire",
                    "B street interviews",
                    "C traffic counts",
                ],
            },
            {
                "n": 23,
                "text": "Aisha is worried that the sample will be",
                "options": ["A too small", "B too young", "C too local"],
            },
            {
                "n": 24,
                "text": "The tutor advises them to",
                "options": [
                    "A shorten the questions",
                    "B add a pilot study",
                    "C change the deadline",
                ],
            },
            {
                "n": 25,
                "text": "They agree to present their results using",
                "options": ["A a map", "B bar charts", "C a short video"],
            },
        ],
        "answers": {"21": "B", "22": "A", "23": "B", "24": "B", "25": "A"},
        "transcript": "Two students discuss a project on student commuting, which they both find frustrating. They choose an online questionnaire, worry most respondents will be first-years, accept the tutor's pilot-study advice and plan to map journey times.",
    },
    {
        "code": "L_SENT",
        "part": 3,
        "title": "Transport survey – next steps",
        "instructions": "Complete the sentences. Write NO MORE THAN TWO WORDS for each answer.",
        "word_limit": 2,
        "items": [
            {
                "n": 26,
                "text": "The pilot study will involve students from the ____ department.",
            },
            {"n": 27, "text": "Tom will check the questions for ____ language."},
            {"n": 28, "text": "Aisha will book a meeting with the ____ officer."},
            {"n": 29, "text": "Responses must be stored on a ____ drive."},
            {"n": 30, "text": "The final report is due at the end of ____."},
        ],
        "answers": {
            "26": ["engineering"],
            "27": ["biased", "biassed"],
            "28": ["sustainability"],
            "29": ["secure", "university"],
            "30": ["March"],
        },
        "transcript": "They will pilot with engineering students, remove biased language, meet the sustainability officer, keep data on a secure drive and submit by the end of March.",
    },
    {
        "code": "L_FORM",
        "part": 4,
        "title": "Lecture: the history of urban rooftop gardens",
        "instructions": "Complete the notes. Write ONE WORD ONLY for each answer.",
        "word_limit": 1,
        "context": "Urban rooftop gardens – lecture notes",
        "items": [
            {"n": 31, "text": "Early examples grew herbs mainly for ____ use."},
            {"n": 32, "text": "Modern roofs need strong ____ to carry soil weight."},
            {"n": 33, "text": "Plants reduce building ____ in summer."},
            {"n": 34, "text": "Rainwater is slowed, lowering the risk of ____."},
            {"n": 35, "text": "Gardens provide habitat for ____ such as bees."},
            {"n": 36, "text": "Main barrier to growth: high initial ____."},
            {"n": 37, "text": "Some cities now offer ____ to owners."},
            {"n": 38, "text": "Community gardens improve residents' mental ____."},
            {"n": 39, "text": "Researchers measure success using ____ sensors."},
            {"n": 40, "text": "Future designs may combine plants with ____ panels."},
        ],
        "answers": {
            "31": ["medicinal"],
            "32": ["beams", "structures"],
            "33": ["temperatures", "temperature"],
            "34": ["flooding"],
            "35": ["insects"],
            "36": ["cost", "costs"],
            "37": ["grants"],
            "38": ["health", "wellbeing"],
            "39": ["moisture"],
            "40": ["solar"],
        },
        "transcript": "A lecturer traces rooftop gardens from medicinal herb roofs to modern green roofs: reinforced beams, cooler temperatures, less flooding, insect habitats, high costs offset by city grants, better mental health, moisture sensors and solar-green hybrids.",
    },
]

LISTENING_PRACTICE = [
    {
        "code": "L_SHORT",
        "title": "Practice: lost property office",
        "instructions": "Answer the questions. Write NO MORE THAN TWO WORDS AND/OR A NUMBER.",
        "word_limit": 2,
        "items": [
            {"n": 1, "text": "What colour is the lost bag?"},
            {"n": 2, "text": "On which bus route was it left?"},
            {"n": 3, "text": "What valuable item was inside?"},
            {"n": 4, "text": "How many days is property kept?"},
        ],
        "answers": {
            "1": ["dark green", "green"],
            "2": ["42", "route 42"],
            "3": ["laptop", "a laptop"],
            "4": ["30", "thirty"],
        },
        "transcript": "A traveller reports a dark green bag left on the number 42 bus with a laptop inside; items are held for 30 days.",
    },
    {
        "code": "L_FORM",
        "title": "Practice: gym membership enquiry",
        "instructions": "Complete the table. Write ONE WORD AND/OR A NUMBER.",
        "word_limit": 1,
        "items": [
            {"n": 1, "text": "Membership type: ____"},
            {"n": 2, "text": "Monthly fee: £____"},
            {"n": 3, "text": "Free class: ____"},
        ],
        "answers": {"1": ["student"], "2": ["24"], "3": ["yoga"]},
        "transcript": "An enquiry about a student membership at £24 a month including one free yoga class.",
    },
]
