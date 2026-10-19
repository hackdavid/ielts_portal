# ruff: noqa: E501
"""Static exam-format guidance shown around the catalogue and player.

Facts follow the published IELTS and Pearson PTE formats. Durations shown to
students come from mock-pack section plans where available.
"""

EXAMS = {
    "ielts": {
        "scale": "Band 0–9 in half bands",
        "delivery": "Computer or paper",
        "length": "About 2 h 45 min",
        "tagline": "Four skills, each with its own timer and its own band.",
        "facts": [
            "Listening, Reading and Writing are taken in one sitting with no break.",
            "Speaking is a face-to-face interview with an examiner, often on another day.",
            "Your overall band is the average of the four section bands, rounded to the nearest half band.",
        ],
    },
    "pte": {
        "scale": "Score 10–90",
        "delivery": "Computer at a test centre",
        "length": "About 2 hours",
        "tagline": "One sitting on a computer, with many items scoring more than one skill.",
        "facts": [
            "The test runs in three parts: Speaking & Writing, Reading, then Listening.",
            "Every response is scored automatically, so you speak into a headset microphone.",
            "Many tasks are integrated: one answer can count towards two skills.",
        ],
    },
}

SECTIONS = {
    "listening": {
        "what": "Recordings of conversations, talks and lectures with questions to answer while you listen.",
        "ielts": "4 parts, 40 questions. Each recording plays once; use the reading time to scan ahead.",
        "pte": "Short lectures and conversations. Some tasks play once with a short pause before audio starts.",
        "tip": "Read the questions before the audio starts and listen for paraphrases, not the exact words.",
    },
    "reading": {
        "what": "Long texts from books, journals and magazines with a range of question formats.",
        "ielts": "3 passages, 40 questions in 60 minutes. No extra time to transfer answers.",
        "pte": "Academic texts with fill-in-the-blank, multiple choice and re-order tasks.",
        "tip": "Skim the whole passage first, then scan for keywords. Don't spend too long on one question.",
    },
    "writing": {
        "what": "Extended responses marked on task response, coherence, vocabulary and grammar.",
        "ielts": "Task 1 (150+ words) and Task 2 (250+ words) in 60 minutes. Task 2 counts double.",
        "pte": "Summaries and an essay or email typed on screen, with a live word count.",
        "tip": "Plan for two or three minutes before typing, and leave time to check grammar and spelling.",
    },
    "speaking": {
        "what": "Spoken answers recorded and assessed on fluency, pronunciation, vocabulary and grammar.",
        "ielts": "3 parts in 11–14 minutes: interview, a 2-minute long turn with 1 minute to prepare, and a discussion.",
        "pte": "Short timed tasks recorded through the microphone. Recording starts automatically after a tone.",
        "tip": "Keep talking at a natural pace. Short pauses are fine; long silences cost marks.",
    },
}

QTYPES = {
    # IELTS Listening
    "L_MCQ": (
        "Choose the correct letter, or the correct letters, from the options for each question.",
        "Underline the key idea in each option; distractors are often mentioned first and then rejected.",
    ),
    "L_MATCH": (
        "Match a list of items, such as people or places, to a set of options.",
        "Options are usually heard in a different order from the list; tick them off as you go.",
    ),
    "L_MAP": (
        "Label a plan, map or diagram using letters or words from the recording.",
        "Find the starting point and follow direction words like 'opposite', 'next to' and 'beyond'.",
    ),
    "L_FORM": (
        "Complete a form, notes, a table or a flow-chart with words you hear.",
        "Predict the type of answer (name, number, date) and check the word limit.",
    ),
    "L_SENT": (
        "Complete sentences that summarise information in the recording.",
        "The sentence must stay grammatical: check plurals and articles.",
    ),
    "L_SHORT": (
        "Answer questions about facts in the recording in a few words.",
        "Write only what is asked; extra words over the limit make the answer wrong.",
    ),
    # IELTS Reading
    "R_MCQ": (
        "Choose the best answer from four or more options about the passage.",
        "Eliminate options that are true but don't answer the question.",
    ),
    "R_TFNG": (
        "Decide whether statements agree with the information in the passage.",
        "'Not Given' means the passage says nothing either way. Don't use your own knowledge.",
    ),
    "R_YNNG": (
        "Decide whether statements agree with the writer's views or claims.",
        "Focus on opinion words such as 'argues', 'believes' and 'unfortunately'.",
    ),
    "R_MATCH_INFO": (
        "Find which paragraph contains a specific piece of information.",
        "Some paragraphs may be used more than once, and some not at all.",
    ),
    "R_HEAD": (
        "Choose the heading that best summarises each paragraph.",
        "Read the first and last sentences of each paragraph to find its main idea.",
    ),
    "R_FEAT": (
        "Match statements or findings to people, places or dates in the passage.",
        "Scan for the names first, then read the text around each one carefully.",
    ),
    "R_END": (
        "Complete each sentence by choosing the correct ending.",
        "Check the grammar and meaning of the whole sentence, not just keywords.",
    ),
    "R_SENT": (
        "Complete sentences using words taken from the passage.",
        "Copy spelling exactly from the passage and respect the word limit.",
    ),
    "R_SUMM": (
        "Complete a summary, notes, table or flow-chart about part of the passage.",
        "Locate the section the summary covers; answers usually appear in order.",
    ),
    "R_DIAG": (
        "Label a diagram using words from the passage.",
        "Answers often come from a single technical paragraph.",
    ),
    "R_SHORT": (
        "Answer questions about details in the passage in a few words.",
        "Question words (who, when, how many) tell you exactly what to look for.",
    ),
    # IELTS Writing & Speaking
    "TASK1": (
        "Report on visual information, or write a letter in General Training, in at least 150 words.",
        "Give an overview of the main trends or purpose; don't describe every number.",
    ),
    "TASK2": (
        "Write an essay of at least 250 words responding to an argument or problem.",
        "Answer every part of the question and support each main idea with an example.",
    ),
    "SP1": (
        "Answer questions about familiar topics such as home, work and interests.",
        "Extend each answer with a reason or an example; avoid one-word replies.",
    ),
    "SP2": (
        "Talk for up to two minutes about a topic on a cue card after one minute of preparation.",
        "Use the minute to note keywords for each bullet point, then cover them in order.",
    ),
    "SP3": (
        "Discuss more abstract ideas linked to the Part 2 topic.",
        "Compare, speculate and give balanced views using phrases like 'on the other hand'.",
    ),
    # PTE Speaking & Writing
    "RA": (
        "Read a short text aloud after 30–40 seconds of preparation.",
        "Read at a steady pace, pause at commas and full stops, and don't go back to correct yourself.",
    ),
    "RS": (
        "Listen to a sentence and repeat it exactly as you heard it.",
        "Focus on the rhythm and meaning; repeating most words fluently beats stopping halfway.",
    ),
    "DI": (
        "Describe a graph, chart, map or picture in about 40 seconds.",
        "Start with the title, cover the key features and finish with a conclusion.",
    ),
    "RL": (
        "Listen to a lecture and retell it in your own words.",
        "Note keywords while listening, then speak in full sentences about the main points.",
    ),
    "RTS": (
        "Respond to an everyday situation described on screen.",
        "Address the person directly and cover every point the situation asks for.",
    ),
    "ASQ": (
        "Answer a short question with a single word or a few words.",
        "Answer immediately; a single correct word is enough.",
    ),
    "SWT": (
        "Summarise a reading passage in one sentence of 5–75 words.",
        "Write one complex sentence that joins the main ideas with connectors.",
    ),
    "WE": (
        "Write a 200–300 word essay on an academic topic.",
        "Use a clear introduction, two body paragraphs and a conclusion.",
    ),
    "WEM": (
        "Write an email of 50–120 words in response to a situation.",
        "Match the tone to the reader and cover each point in the prompt.",
    ),
    # PTE Reading
    "RW_FIB": (
        "Choose the best word for each gap from a drop-down list.",
        "Use collocations and grammar: the word must fit both the meaning and the sentence.",
    ),
    "MCM_R": (
        "Choose all the correct answers about a passage. Wrong choices lose marks.",
        "Only select options you are sure of; guessing can lower your score.",
    ),
    "RO": (
        "Put shuffled paragraphs back into their original order.",
        "Find the opening sentence (it introduces the topic), then follow pronouns and linkers.",
    ),
    "R_FIB": (
        "Drag words from a box into the gaps in a passage.",
        "Read the whole passage first; extra words in the box are distractors.",
    ),
    "MCS_R": (
        "Choose the single best answer about a reading passage.",
        "Read the question first so you know what to look for.",
    ),
    # PTE Listening
    "SST": (
        "Write a 50–70 word summary of a short lecture.",
        "Capture the main point and two or three supporting ideas in your own words.",
    ),
    "MCM_L": (
        "Choose all the correct answers about a recording. Wrong choices lose marks.",
        "Read the options before the audio starts and only select what you clearly heard.",
    ),
    "FIB_L": (
        "Type the missing words in a transcript as you listen.",
        "Type quickly as you hear each word, then correct spelling at the end.",
    ),
    "HCS": (
        "Choose the paragraph that best summarises a recording.",
        "Reject summaries with details that are wrong or that weren't mentioned.",
    ),
    "MCS_L": (
        "Choose the single best answer about a recording.",
        "Listen for the speaker's main purpose or conclusion.",
    ),
    "SMW": (
        "Choose the words that complete a recording that cuts off.",
        "Follow the topic and tone; the last sentence is usually predictable.",
    ),
    "HIW": (
        "Click the words in a transcript that differ from what the speaker says.",
        "Keep your eyes on the text and click as soon as you hear a mismatch.",
    ),
    "WFD": (
        "Type a sentence exactly as you hear it.",
        "Every correct word scores, so write everything you remember even if it isn't perfect.",
    ),
}


def exam_guide(exam):
    return EXAMS.get(getattr(exam, "kind", exam), EXAMS["ielts"])


def section_guide(code, kind="ielts"):
    row = SECTIONS.get(code)
    if not row:
        return None
    return {"what": row["what"], "format": row.get(kind, ""), "tip": row["tip"]}


def qtype_guide(code):
    what, tip = QTYPES.get(code, ("", ""))
    return {"what": what, "tip": tip} if what else None
