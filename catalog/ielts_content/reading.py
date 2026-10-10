"""Original IELTS-style reading passages and question sets."""

P1 = """A  For most of the twentieth century, city planners treated bicycles as a nostalgic leftover. Roads were widened for cars, and cycling fell to under two per cent of urban journeys in many European cities by 1975.
B  The turnaround began with fuel shortages in the 1970s. Some Dutch and Danish cities experimented with painted cycle lanes, and when usage rose quickly, they replaced paint with kerbs that physically separated cyclists from traffic.
C  Research since then has shown that separation, not enthusiasm, is the key factor. Surveys repeatedly find that a majority of non-cyclists would ride if they felt safe, and that perceived danger matters more than distance or weather.
D  Cities that copied only the paint, without protection, saw modest growth. Seville, by contrast, built 80 kilometres of protected lanes in under two years after 2006 and saw daily trips rise roughly tenfold.
E  Critics argue that cycling infrastructure benefits mainly young professionals. However, data from several cities show the fastest growth among women, older riders and children once protected networks connect schools and shops.
F  The next challenge is integration: secure parking at stations, bicycles on trains and shared bikes for the 'last mile' are now seen as just as important as the lanes themselves."""

P2 = """Honeybees are often praised as the world's most important pollinators, but recent field studies suggest that wild bees, hoverflies and even moths do much of the work. In a survey of 41 crop systems worldwide, wild insects increased fruit set in every system, while honeybee visits increased it in only 14 per cent.
Researchers believe the difference lies in behaviour. Honeybees tend to visit the same plant repeatedly, transferring pollen between flowers of one individual. Wild species move more widely and carry pollen between different plants, which many crops require.
This does not mean managed hives are useless. They are reliable, can be moved to where crops flower and are vital for almonds and some fruits. But the studies suggest that farms relying only on hives may be missing a free and more effective service.
Protecting wild pollinators is relatively cheap: strips of wildflowers at field edges, hedgerows and reduced pesticide spraying during flowering all help. The authors argue that such measures should be considered as part of normal crop management rather than environmental extras."""

P3 = """The idea that a 'growth mindset' – the belief that ability can be developed – improves school results became hugely popular in the 2010s. Schools bought training programmes, and posters praising effort appeared in classrooms around the world.
Large replication studies have since produced a more cautious picture. A national experiment involving over 12,000 teenagers found that a short online mindset session raised grades only for lower-achieving students, and the effect was small. Other trials found no measurable effect at all.
Supporters reply that the original idea was misunderstood. In their view, mindset messages work only when the school environment backs them up – for instance, when teachers allow students to revise work after feedback. Simply telling children to 'try harder' is not the same thing.
The author's view is that the debate shows a wider problem in education: promising laboratory results are often scaled up before they are properly tested in real classrooms. A modest, well-targeted intervention may still be worthwhile, but it should not be sold as a cure for low achievement."""

READING_ACADEMIC = [
    {
        "code": "R_HEAD",
        "part": 1,
        "title": "Passage 1: The return of the urban cyclist – headings",
        "passage": P1,
        "instructions": "Choose the correct heading for paragraphs B–F from the list i–viii.",
        "context": "i Who really benefits  ii A crisis creates an opportunity  iii Safety above all  iv The cost of cycle lanes  v Copying the wrong thing  vi Beyond the lane  vii Weather and distance  viii A forgotten vehicle",
        "items": [
            {
                "n": n,
                "text": f"Paragraph {p}",
                "options": ["i", "ii", "iii", "iv", "v", "vi", "vii", "viii"],
            }
            for n, p in zip(range(1, 6), "BCDEF")
        ],
        "answers": {"1": "ii", "2": "iii", "3": "v", "4": "i", "5": "vi"},
    },
    {
        "code": "R_TFNG",
        "part": 1,
        "title": "Passage 1: The return of the urban cyclist – T/F/NG",
        "passage": P1,
        "instructions": "Do the statements agree with the information in the passage? Write TRUE, FALSE or NOT GIVEN.",
        "items": [
            {"n": n, "text": t, "options": ["TRUE", "FALSE", "NOT GIVEN"]}
            for n, t in [
                (
                    6,
                    "Cycling accounted for less than two per cent of journeys in many European cities by 1975.",
                ),
                (7, "The first Dutch cycle lanes were protected by kerbs."),
                (8, "Weather is the main reason people give for not cycling."),
                (9, "Seville's network cost less than similar projects elsewhere."),
                (10, "Children's cycling increased when networks linked schools."),
            ]
        ],
        "answers": {
            "6": "TRUE",
            "7": "FALSE",
            "8": "FALSE",
            "9": "NOT GIVEN",
            "10": "TRUE",
        },
    },
    {
        "code": "R_SENT",
        "part": 1,
        "title": "Passage 1: The return of the urban cyclist – sentences",
        "passage": P1,
        "instructions": "Complete the sentences. Choose NO MORE THAN TWO WORDS from the passage.",
        "word_limit": 2,
        "items": [
            {"n": 11, "text": "Early lanes in the 1970s were simply ____ on the road."},
            {"n": 12, "text": "Seville's daily trips grew about ____ after 2006."},
            {"n": 13, "text": "Shared bikes help with the ____ of a journey."},
        ],
        "answers": {"11": ["painted", "paint"], "12": ["tenfold"], "13": ["last mile"]},
    },
    {
        "code": "R_MCQ",
        "part": 2,
        "title": "Passage 2: Who really pollinates our crops? – multiple choice",
        "passage": P2,
        "instructions": "Choose the correct letter, A, B, C or D.",
        "items": [
            {
                "n": 14,
                "text": "In the survey of 41 crop systems, honeybees",
                "options": [
                    "A improved fruit set in every system",
                    "B improved fruit set in a minority of systems",
                    "C were absent from most systems",
                    "D reduced fruit set",
                ],
            },
            {
                "n": 15,
                "text": "Wild insects are more effective mainly because they",
                "options": [
                    "A visit more flowers",
                    "B fly in colder weather",
                    "C move pollen between different plants",
                    "D are more numerous",
                ],
            },
            {
                "n": 16,
                "text": "The writer says managed hives",
                "options": [
                    "A should be replaced",
                    "B are still important for some crops",
                    "C are too expensive",
                    "D spread disease",
                ],
            },
            {
                "n": 17,
                "text": "The authors want wildflower strips to be seen as",
                "options": [
                    "A an environmental extra",
                    "B a government duty",
                    "C part of normal farming",
                    "D a temporary measure",
                ],
            },
        ],
        "answers": {"14": "B", "15": "C", "16": "B", "17": "C"},
    },
    {
        "code": "R_SUMM",
        "part": 2,
        "title": "Passage 2: Who really pollinates our crops? – summary",
        "passage": P2,
        "instructions": "Complete the summary. Choose ONE WORD ONLY from the passage.",
        "word_limit": 1,
        "items": [
            {"n": 18, "text": "Honeybees often stay on one ____ plant."},
            {"n": 19, "text": "Hives can be ____ to flowering crops."},
            {"n": 20, "text": "Edges planted with ____ support wild species."},
            {"n": 21, "text": "Farmers can also cut ____ use during flowering."},
        ],
        "answers": {
            "18": ["individual"],
            "19": ["moved"],
            "20": ["wildflowers", "hedgerows"],
            "21": ["pesticide"],
        },
    },
    {
        "code": "R_MATCH_INFO",
        "part": 2,
        "title": "Passage 2: Who really pollinates our crops? – matching information",
        "passage": P2,
        "instructions": "Which paragraph (1–4) contains the following information?",
        "items": [
            {"n": n, "text": t, "options": ["1", "2", "3", "4"]}
            for n, t in [
                (22, "a list of low-cost protective measures"),
                (23, "a statistic comparing two groups of insects"),
                (24, "an explanation based on insect behaviour"),
                (25, "a crop that depends on managed hives"),
                (26, "a recommendation about farm management"),
            ]
        ],
        "answers": {"22": "4", "23": "1", "24": "2", "25": "3", "26": "4"},
    },
    {
        "code": "R_YNNG",
        "part": 3,
        "title": "Passage 3: Rethinking the growth mindset – writer's views",
        "passage": P3,
        "instructions": "Do the statements agree with the views of the writer? Write YES, NO or NOT GIVEN.",
        "items": [
            {"n": n, "text": t, "options": ["YES", "NO", "NOT GIVEN"]}
            for n, t in [
                (
                    27,
                    "Mindset programmes were adopted widely before strong evidence existed.",
                ),
                (28, "The national experiment proved mindset training is useless."),
                (29, "Teachers dislike mindset posters."),
                (30, "Small, targeted interventions can still be worthwhile."),
                (
                    31,
                    "Laboratory findings should be tested in classrooms before wide use.",
                ),
            ]
        ],
        "answers": {
            "27": "YES",
            "28": "NO",
            "29": "NOT GIVEN",
            "30": "YES",
            "31": "YES",
        },
    },
    {
        "code": "R_END",
        "part": 3,
        "title": "Passage 3: Rethinking the growth mindset – sentence endings",
        "passage": P3,
        "instructions": "Complete each sentence with the correct ending, A–F.",
        "context": "A only for lower-achieving students.  B when teachers allow revision after feedback.  C by selling training programmes.  D before proper classroom testing.  E for all age groups.  F with no change in grades.",
        "items": [
            {
                "n": 32,
                "text": "The online session improved grades",
                "options": list("ABCDEF"),
            },
            {
                "n": 33,
                "text": "Supporters say mindset messages work",
                "options": list("ABCDEF"),
            },
            {"n": 34, "text": "Some other trials ended", "options": list("ABCDEF")},
            {
                "n": 35,
                "text": "Education ideas are often scaled up",
                "options": list("ABCDEF"),
            },
        ],
        "answers": {"32": "A", "33": "B", "34": "F", "35": "D"},
    },
    {
        "code": "R_SHORT",
        "part": 3,
        "title": "Passage 3: Rethinking the growth mindset – short answers",
        "passage": P3,
        "instructions": "Answer the questions. Choose NO MORE THAN THREE WORDS AND/OR A NUMBER from the passage.",
        "word_limit": 3,
        "items": [
            {"n": 36, "text": "In which decade did the idea become popular?"},
            {
                "n": 37,
                "text": "How many teenagers took part in the national experiment?",
            },
            {"n": 38, "text": "What format did the short mindset session use?"},
            {"n": 39, "text": "What appeared in classrooms praising effort?"},
            {"n": 40, "text": "What should an intervention not be sold as?"},
        ],
        "answers": {
            "36": ["2010s", "the 2010s"],
            "37": ["12,000", "over 12,000"],
            "38": ["online"],
            "39": ["posters"],
            "40": ["a cure", "cure"],
        },
    },
]

GT_S1 = """Westbridge Leisure Centre – Summer timetable
Swimming: Lane swimming 6:30–9:00 every weekday. Family swim Saturday 10:00–12:00 (children under 8 must be with an adult in the water).
Fitness: New members must book a free induction before using the gym. Inductions run Tuesdays and Thursdays at 18:00.
Courses: Beginner tennis (6 weeks, £45) starts 3 June. First-aid certificate (one day, £60) on 15 June – places limited to 12.
Lockers: £1 coin returned after use. The centre is closed on public holidays."""

GT_S2 = """New staff guide: requesting annual leave
All full-time staff receive 25 days' annual leave plus public holidays. Leave must be requested through the online HR portal at least two weeks in advance; requests for more than ten consecutive days need your manager's approval one month ahead.
Up to five unused days may be carried into the next year but must be taken by the end of March. Unused days beyond this are lost. Part-time staff receive leave in proportion to their contracted hours.
If you are ill during booked leave, inform your manager on the first day and those days can be reclassified as sick leave with a doctor's note."""

READING_GENERAL = [
    {
        "code": "R_TFNG",
        "part": 1,
        "title": "Section 1: Leisure centre timetable",
        "passage": GT_S1,
        "instructions": "Do the statements agree with the information in the text? Write TRUE, FALSE or NOT GIVEN.",
        "items": [
            {"n": n, "text": t, "options": ["TRUE", "FALSE", "NOT GIVEN"]}
            for n, t in [
                (1, "Lane swimming is available at weekends."),
                (2, "Young children may swim alone during family swim."),
                (3, "Gym inductions cost extra."),
                (4, "The first-aid course takes one day."),
                (5, "The tennis course is suitable for advanced players."),
                (6, "Locker coins are refunded."),
            ]
        ],
        "answers": {
            "1": "FALSE",
            "2": "FALSE",
            "3": "FALSE",
            "4": "TRUE",
            "5": "NOT GIVEN",
            "6": "TRUE",
        },
    },
    {
        "code": "R_MATCH_INFO",
        "part": 1,
        "title": "Section 1: Leisure centre timetable – matching information",
        "passage": GT_S1,
        "instructions": "Which part of the timetable (A Swimming, B Fitness, C Courses, D Lockers) contains the following information?",
        "items": [
            {"n": n, "text": t, "options": list("ABCD")}
            for n, t in [
                (7, "a limit on the number of participants"),
                (8, "a rule about adult supervision"),
                (9, "a requirement for new members"),
                (10, "a small payment that is returned"),
                (11, "a course lasting several weeks"),
                (12, "sessions held early in the morning"),
                (13, "days when the centre does not open"),
            ]
        ],
        "answers": {
            "7": "C",
            "8": "A",
            "9": "B",
            "10": "D",
            "11": "C",
            "12": "A",
            "13": "D",
        },
    },
    {
        "code": "R_SENT",
        "part": 2,
        "title": "Section 2: Requesting annual leave",
        "passage": GT_S2,
        "instructions": "Complete the sentences. Choose NO MORE THAN TWO WORDS AND/OR A NUMBER from the text.",
        "word_limit": 2,
        "items": [
            {"n": 14, "text": "Full-time staff get ____ days of annual leave."},
            {"n": 15, "text": "Requests are made using the online ____."},
            {"n": 16, "text": "Long holidays need approval one ____ ahead."},
            {"n": 17, "text": "Carried-over days must be used by the end of ____."},
            {"n": 18, "text": "Sick days during leave require a ____."},
        ],
        "answers": {
            "14": ["25"],
            "15": ["HR portal"],
            "16": ["month"],
            "17": ["March"],
            "18": ["doctor's note"],
        },
    },
    {
        "code": "R_TFNG",
        "part": 2,
        "title": "Section 2: Requesting annual leave – T/F/NG",
        "passage": GT_S2,
        "instructions": "Do the statements agree with the information in the text? Write TRUE, FALSE or NOT GIVEN.",
        "items": [
            {"n": n, "text": t, "options": ["TRUE", "FALSE", "NOT GIVEN"]}
            for n, t in [
                (19, "Public holidays are included in the 25 days."),
                (20, "Short leave requests need two weeks' notice."),
                (21, "Managers can refuse any leave request."),
                (22, "Staff may carry over up to five days."),
                (23, "Unused days beyond the carry-over limit are paid."),
                (24, "Part-time staff get the same leave as full-time staff."),
                (25, "Illness during leave must be reported on the first day."),
                (26, "Sick leave during holidays needs a doctor's note."),
            ]
        ],
        "answers": {
            "19": "FALSE",
            "20": "TRUE",
            "21": "NOT GIVEN",
            "22": "TRUE",
            "23": "FALSE",
            "24": "FALSE",
            "25": "TRUE",
            "26": "TRUE",
        },
    },
] + [
    dict(s, part=3)
    for s in READING_ACADEMIC
    if s["code"] in ("R_YNNG", "R_END", "R_SHORT")
]

READING_PRACTICE = [
    {
        "code": "R_FEAT",
        "title": "Practice: matching features – inventors",
        "passage": "Ada designed early calculating programs. Karl improved bicycle gears. Lin developed a cheap water filter. Omar built the first solar oven for schools.",
        "instructions": "Match each achievement with the correct person, A–D.",
        "context": "A Ada  B Karl  C Lin  D Omar",
        "items": [
            {
                "n": 1,
                "text": "made clean water more affordable",
                "options": list("ABCD"),
            },
            {"n": 2, "text": "worked on a form of transport", "options": list("ABCD")},
            {"n": 3, "text": "helped schools use the sun", "options": list("ABCD")},
        ],
        "answers": {"1": "C", "2": "B", "3": "D"},
    },
    {
        "code": "R_DIAG",
        "part": None,
        "title": "Practice: diagram – how a rain garden works",
        "passage": "Rainwater runs from the roof into a shallow basin. A top layer of mulch traps debris, sandy soil below filters the water, and a gravel base stores it before it soaks into the ground.",
        "instructions": "Label the diagram. Choose ONE WORD ONLY from the text.",
        "word_limit": 1,
        "items": [
            {"n": 1, "text": "Top layer: ____"},
            {"n": 2, "text": "Middle layer: sandy ____"},
            {"n": 3, "text": "Base: ____"},
        ],
        "answers": {"1": ["mulch"], "2": ["soil"], "3": ["gravel"]},
    },
    {
        "code": "R_TFNG",
        "title": "Practice: T/F/NG – the city library",
        "passage": "The city library opened in 1902 and moved to its current glass building in 2015. It now lends tools as well as books, and membership is free for residents.",
        "instructions": "Write TRUE, FALSE or NOT GIVEN.",
        "items": [
            {"n": n, "text": t, "options": ["TRUE", "FALSE", "NOT GIVEN"]}
            for n, t in [
                (1, "The library has always been in a glass building."),
                (2, "Residents pay a small fee."),
                (3, "Tools can be borrowed."),
            ]
        ],
        "answers": {"1": "FALSE", "2": "FALSE", "3": "TRUE"},
    },
]

_TEA = (
    "1  Tea was first drunk as a medicine before it became an everyday drink.\n"
    "2  Traders carried tea along mountain routes, often swapping it for horses.\n"
    "3  Today, machines pick most tea, but the finest leaves are still picked by hand."
)

READING_PRACTICE += [
    {
        "code": "R_HEAD",
        "title": "Practice: matching headings – a short history of tea",
        "passage": _TEA,
        "instructions": "Choose the correct heading for paragraphs 1–3 from the list i–v.",
        "context": "i Hand versus machine  ii From cure to custom  iii The price of tea  iv Trading on the mountains  v Tea and health today",
        "items": [
            {"n": n, "text": f"Paragraph {n}", "options": ["i", "ii", "iii", "iv", "v"]}
            for n in (1, 2, 3)
        ],
        "answers": {"1": "ii", "2": "iv", "3": "i"},
    },
    {
        "code": "R_MCQ",
        "title": "Practice: multiple choice – a short history of tea",
        "passage": _TEA,
        "instructions": "Choose the correct letter, A, B, C or D.",
        "items": [
            {
                "n": 1,
                "text": "Traders often exchanged tea for",
                "options": ["A silk", "B horses", "C salt", "D medicine"],
            },
            {
                "n": 2,
                "text": "The best tea leaves are",
                "options": [
                    "A picked by machine",
                    "B imported",
                    "C picked by hand",
                    "D dried in the sun",
                ],
            },
        ],
        "answers": {"1": "B", "2": "C"},
    },
    {
        "code": "R_SUMM",
        "title": "Practice: summary completion – a short history of tea",
        "passage": _TEA,
        "instructions": "Complete the summary. Choose ONE WORD ONLY from the text.",
        "word_limit": 1,
        "items": [
            {"n": 1, "text": "Tea was originally used as a ____."},
            {"n": 2, "text": "It travelled along ____ routes."},
        ],
        "answers": {"1": ["medicine"], "2": ["mountain"]},
    },
]
