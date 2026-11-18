"""
Database seeder for tutor curriculum
Populates the database with lessons matching the frontend curriculum
"""
import asyncio
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import AsyncSessionLocal, init_db
from app.models.lesson import (
    Lesson, LessonContent, ContentType, FocusArea, CEFRLevel
)


# Curriculum data matching frontend
CURRICULUM_DATA = [
    # A1 - Beginner
    {
        "id": "a1-greetings",
        "title": "Greetings & Introductions",
        "description": "Learn essential greetings, farewells, and how to introduce yourself naturally.",
        "language": "es",
        "level": CEFRLevel.A1,
        "focus_area": FocusArea.CONVERSATION,
        "duration": 15,
        "xp_reward": 50,
        "prerequisites": [],
        "tags": ["basics", "greetings", "conversation", "formal", "informal"],
        "order": 1,
        "target_age_group": "adult",
        "gamification_level": "medium",
        "content": [
            {
                "content_id": "c1",
                "type": ContentType.DIALOGUE,
                "title": "Meeting Someone New",
                "order": 1,
                "estimated_time": 5,
                "data": {
                    "dialogue": [
                        {"speaker": "Person A", "text": "¡Hola! ¿Cómo te llamas?", "translation": "Hi! What's your name?"},
                        {"speaker": "Person B", "text": "Me llamo María. ¿Y tú?", "translation": "My name is María. And you?"},
                        {"speaker": "Person A", "text": "Me llamo Juan. Mucho gusto.", "translation": "My name is Juan. Nice to meet you."},
                        {"speaker": "Person B", "text": "Igualmente. ¿De dónde eres?", "translation": "Likewise. Where are you from?"},
                    ],
                    "key_phrases": [
                        {"phrase": "¿Cómo te llamas?", "translation": "What's your name?"},
                        {"phrase": "Me llamo...", "translation": "My name is..."},
                        {"phrase": "Mucho gusto", "translation": "Nice to meet you"},
                        {"phrase": "¿De dónde eres?", "translation": "Where are you from?"},
                    ],
                },
            },
            {
                "content_id": "c2",
                "type": ContentType.EXERCISE,
                "title": "Greeting Practice",
                "order": 2,
                "estimated_time": 5,
                "data": {
                    "exercises": [
                        {
                            "type": "multiple_choice",
                            "question": "How do you say 'Good morning' in Spanish?",
                            "options": ["Buenos días", "Buenas noches", "Buenas tardes", "Hola"],
                            "correct": 0,
                            "explanation": "Buenos días is used in the morning until around noon.",
                        },
                        {
                            "type": "fill_blank",
                            "question": "Complete: '_____ llamo Ana.'",
                            "answer": "Me",
                            "explanation": "Use 'Me llamo' to say 'My name is'.",
                        },
                    ],
                },
            },
            {
                "content_id": "c3",
                "type": ContentType.PRONUNCIATION,
                "title": "Vowel Sounds in Greetings",
                "order": 3,
                "estimated_time": 5,
                "data": {
                    "target_words": ["Hola", "Buenos", "días", "tardes", "noches"],
                    "focus": "Spanish vowels are pure - a, e, i, o, u",
                    "tips": [
                        "a - like 'father' but shorter",
                        "e - like 'bed' but purer",
                        "i - like 'see' but shorter",
                        "o - like 'go' but without the glide",
                        "u - like 'food' but shorter",
                    ],
                },
            },
        ],
    },
    {
        "id": "a1-numbers",
        "title": "Numbers 1-100",
        "description": "Master Spanish numbers from 1 to 100 with pronunciation and listening practice.",
        "language": "es",
        "level": CEFRLevel.A1,
        "focus_area": FocusArea.VOCABULARY,
        "duration": 20,
        "xp_reward": 75,
        "prerequisites": ["a1-greetings"],
        "tags": ["numbers", "pronunciation", "vocabulary", "listening"],
        "order": 2,
        "content": [
            {
                "content_id": "c1",
                "type": ContentType.AUDIO,
                "title": "Numbers 1-20",
                "order": 1,
                "estimated_time": 7,
                "data": {
                    "numbers": [
                        {"number": 1, "spanish": "uno", "pronunciation": "OO-noh"},
                        {"number": 2, "spanish": "dos", "pronunciation": "dohs"},
                        {"number": 3, "spanish": "tres", "pronunciation": "trehs"},
                        {"number": 4, "spanish": "cuatro", "pronunciation": "KWAH-troh"},
                        {"number": 5, "spanish": "cinco", "pronunciation": "SEEN-koh"},
                        {"number": 6, "spanish": "seis", "pronunciation": "seh-ees"},
                        {"number": 7, "spanish": "siete", "pronunciation": "SYEH-teh"},
                        {"number": 8, "spanish": "ocho", "pronunciation": "OH-choh"},
                        {"number": 9, "spanish": "nueve", "pronunciation": "NWEH-beh"},
                        {"number": 10, "spanish": "diez", "pronunciation": "DYEHS"},
                    ],
                },
            },
            {
                "content_id": "c2",
                "type": ContentType.EXERCISE,
                "title": "Number Recognition",
                "order": 2,
                "estimated_time": 6,
                "data": {
                    "exercises": [
                        {
                            "type": "multiple_choice",
                            "audio_prompt": True,
                            "question": "What number do you hear?",
                            "options": ["cinco", "seis", "siete", "ocho"],
                            "correct": 2,
                        },
                    ],
                },
            },
            {
                "content_id": "c3",
                "type": ContentType.PRONUNCIATION,
                "title": "Number Pronunciation Patterns",
                "order": 3,
                "estimated_time": 7,
                "data": {
                    "patterns": [
                        "11-15: unique forms (once, doce, trece, catorce, quince)",
                        "16-19: diez + y + unit (dieciséis, diecisiete...)",
                        "20-29: veinti + unit (veintiuno, veintidós...)",
                        "30, 40, 50...: treinta, cuarenta, cincuenta...",
                        "31-99: tens + y + unit (treinta y uno, cuarenta y dos...)",
                    ],
                },
            },
        ],
    },
    {
        "id": "a1-ar-verbs",
        "title": "Present Tense -AR Verbs",
        "description": "Conjugate and use regular -AR verbs in the present tense with confidence.",
        "language": "es",
        "level": CEFRLevel.A1,
        "focus_area": FocusArea.GRAMMAR,
        "duration": 25,
        "xp_reward": 100,
        "prerequisites": ["a1-greetings"],
        "tags": ["grammar", "verbs", "conjugation", "present tense", "writing"],
        "order": 3,
        "content": [
            {
                "content_id": "c1",
                "type": ContentType.TEXT,
                "title": "AR Verb Conjugation Rules",
                "order": 1,
                "estimated_time": 8,
                "data": {
                    "rule": "Remove -ar, add endings: -o, -as, -a, -amos, -áis, -an",
                    "example_verb": "hablar (to speak)",
                    "conjugation": {
                        "yo": "hablo",
                        "tú": "hablas",
                        "él/ella": "habla",
                        "nosotros": "hablamos",
                        "vosotros": "habláis",
                        "ellos/ellas": "hablan",
                    },
                    "common_verbs": [
                        "hablar (to speak)", "estudiar (to study)", "trabajar (to work)",
                        "caminar (to walk)", "escuchar (to listen)", "mirar (to watch)",
                        "comprar (to buy)", "pagar (to pay)", "llegar (to arrive)",
                    ],
                },
            },
            {
                "content_id": "c2",
                "type": ContentType.EXERCISE,
                "title": "Conjugation Drills",
                "order": 2,
                "estimated_time": 10,
                "data": {
                    "exercises": [
                        {
                            "type": "fill_blank",
                            "question": "Yo ______ (hablar) español.",
                            "answer": "hablo",
                        },
                        {
                            "type": "fill_blank",
                            "question": "Nosotros ______ (estudiar) mucho.",
                            "answer": "estudiamos",
                        },
                    ],
                },
            },
            {
                "content_id": "c3",
                "type": ContentType.WRITING,
                "title": "Write Your Daily Routine",
                "order": 3,
                "estimated_time": 7,
                "data": {
                    "prompt": "Describe tu rutina diaria usando 5 verbos -AR.",
                    "min_words": 50,
                    "template": "Por la mañana yo ______. Luego yo ______. Por la tarde yo ______. Por la noche yo ______.",
                    "vocabulary_hints": [
                        {"word": "despertar", "translation": "to wake up"},
                        {"word": "levantar", "translation": "to get up"},
                        {"word": "desayunar", "translation": "to have breakfast"},
                        {"word": "trabajar", "translation": "to work"},
                        {"word": "cenar", "translation": "to have dinner"},
                        {"word": "dormir", "translation": "to sleep"},
                    ],
                },
            },
        ],
    },
    {
        "id": "a1-pronunciation-vowels",
        "title": "Spanish Pronunciation: Vowels",
        "description": "Perfect your Spanish vowel sounds with native speaker examples and feedback.",
        "language": "es",
        "level": CEFRLevel.A1,
        "focus_area": FocusArea.PRONUNCIATION,
        "duration": 15,
        "xp_reward": 50,
        "prerequisites": [],
        "tags": ["pronunciation", "vowels", "basics", "native-speaker"],
        "order": 4,
        "content": [
            {
                "content_id": "c1",
                "type": ContentType.VIDEO,
                "title": "Vowel Sounds Overview",
                "order": 1,
                "estimated_time": 5,
                "data": {
                    "video_url": "https://example.com/vowel-overview",
                    "transcript": "Spanish has 5 vowel sounds...",
                    "key_points": [
                        "Vowels are always pronounced the same way",
                        "No diphthongs like in English",
                        "Each vowel is distinct and clear",
                    ],
                },
            },
            {
                "content_id": "c2",
                "type": ContentType.PRONUNCIATION,
                "title": "Practice Each Vowel",
                "order": 2,
                "estimated_time": 5,
                "data": {
                    "exercises": [
                        {"vowel": "a", "words": ["casa", "mamá", "papa", "amigo"]},
                        {"vowel": "e", "words": ["mesa", "tres", "leche", "perro"]},
                        {"vowel": "i", "words": ["sí", "mi", "ti", "vin"]},
                        {"vowel": "o", "words": ["hola", "dos", "no", "oso"]},
                        {"vowel": "u", "words": ["tu", "uno", "mucho", "luz"]},
                    ],
                },
            },
            {
                "content_id": "c3",
                "type": ContentType.EXERCISE,
                "title": "Minimal Pairs",
                "order": 3,
                "estimated_time": 5,
                "data": {
                    "pairs": [
                        ["casa", "cosa"],
                        ["mesa", "misa"],
                        ["peso", "piso"],
                        ["lobo", "lobo"],
                    ],
                },
            },
        ],
    },
    {
        "id": "a1-family",
        "title": "Family & Relationships",
        "description": "Talk about your family, describe people, and express relationships.",
        "language": "es",
        "level": CEFRLevel.A1,
        "focus_area": FocusArea.VOCABULARY,
        "duration": 20,
        "xp_reward": 80,
        "prerequisites": ["a1-greetings", "a1-numbers"],
        "tags": ["family", "vocabulary", "descriptions", "conversation"],
        "order": 5,
        "content": [
            {
                "content_id": "c1",
                "type": ContentType.FLASHCARD,
                "title": "Family Vocabulary",
                "order": 1,
                "estimated_time": 8,
                "data": {
                    "cards": [
                        {"front": "madre", "back": "mother", "audio": "madre.mp3"},
                        {"front": "padre", "back": "father", "audio": "padre.mp3"},
                        {"front": "hermano", "back": "brother", "audio": "hermano.mp3"},
                        {"front": "hermana", "back": "sister", "audio": "hermana.mp3"},
                        {"front": "abuelo", "back": "grandfather", "audio": "abuelo.mp3"},
                        {"front": "abuela", "back": "grandmother", "audio": "abuela.mp3"},
                        {"front": "tío", "back": "uncle", "audio": "tio.mp3"},
                        {"front": "tía", "back": "aunt", "audio": "tia.mp3"},
                        {"front": "primo", "back": "cousin (m)", "audio": "primo.mp3"},
                        {"front": "prima", "back": "cousin (f)", "audio": "prima.mp3"},
                    ],
                },
            },
            {
                "content_id": "c2",
                "type": ContentType.DIALOGUE,
                "title": "Describing Your Family",
                "order": 2,
                "estimated_time": 7,
                "data": {
                    "dialogue": [
                        {"speaker": "A", "text": "¿Tienes hermanos?", "translation": "Do you have siblings?"},
                        {"speaker": "B", "text": "Sí, tengo un hermano y una hermana.", "translation": "Yes, I have a brother and a sister."},
                        {"speaker": "A", "text": "¿Cómo se llaman?", "translation": "What are their names?"},
                        {"speaker": "B", "text": "Mi hermano se llama Carlos y mi hermana se llama Ana.", "translation": "My brother is Carlos and my sister is Ana."},
                    ],
                },
            },
        ],
    },
    {
        "id": "a1-food",
        "title": "Food & Dining",
        "description": "Essential vocabulary and phrases for ordering food and dining out.",
        "language": "es",
        "level": CEFRLevel.A1,
        "focus_area": FocusArea.CONVERSATION,
        "duration": 20,
        "xp_reward": 80,
        "prerequisites": ["a1-greetings"],
        "tags": ["food", "restaurant", "practical", "ordering"],
        "order": 6,
        "content": [
            {
                "content_id": "c1",
                "type": ContentType.DIALOGUE,
                "title": "At the Restaurant",
                "order": 1,
                "estimated_time": 8,
                "data": {
                    "dialogue": [
                        {"speaker": "Waiter", "text": "¿Qué desea comer?", "translation": "What would you like to eat?"},
                        {"speaker": "Customer", "text": "Quiero la paella, por favor.", "translation": "I want the paella, please."},
                        {"speaker": "Waiter", "text": "¿Algo de beber?", "translation": "Something to drink?"},
                        {"speaker": "Customer", "text": "Una agua mineral, gracias.", "translation": "A mineral water, thank you."},
                    ],
                },
            },
            {
                "content_id": "c2",
                "type": ContentType.EXERCISE,
                "title": "Menu Items & Dietary Needs",
                "order": 2,
                "estimated_time": 6,
                "data": {
                    "vocabulary": [
                        {"spanish": "la carta", "english": "the menu"},
                        {"spanish": "el plato del día", "english": "the dish of the day"},
                        {"spanish": "soy vegetariano/a", "english": "I'm vegetarian"},
                        {"spanish": "sin gluten", "english": "gluten-free"},
                        {"spanish": "la cuenta, por favor", "english": "the check, please"},
                    ],
                },
            },
        ],
    },
    # A2 - Elementary
    {
        "id": "a2-past-tense",
        "title": "Preterite vs Imperfect",
        "description": "Master the two main past tenses and when to use each one.",
        "language": "es",
        "level": CEFRLevel.A2,
        "focus_area": FocusArea.GRAMMAR,
        "duration": 30,
        "xp_reward": 150,
        "prerequisites": ["a1-ar-verbs"],
        "tags": ["grammar", "past tense", "preterite", "imperfect", "advanced"],
        "order": 7,
        "content": [
            {
                "content_id": "c1",
                "type": ContentType.VIDEO,
                "title": "Preterite vs Imperfect Explained",
                "order": 1,
                "estimated_time": 10,
                "data": {
                    "video_url": "https://example.com/preterite-imperfect",
                    "key_rules": [
                        "Preterite: completed actions, specific time",
                        "Imperfect: ongoing, habitual, descriptions",
                    ],
                },
            },
        ],
    },
    {
        "id": "a2-subjunctive-intro",
        "title": "Introduction to Subjunctive",
        "description": "Learn when and how to use the present subjunctive mood.",
        "language": "es",
        "level": CEFRLevel.A2,
        "focus_area": FocusArea.GRAMMAR,
        "duration": 25,
        "xp_reward": 125,
        "prerequisites": ["a2-past-tense"],
        "tags": ["grammar", "subjunctive", "mood", "advanced"],
        "order": 8,
        "content": [
            {
                "content_id": "c1",
                "type": ContentType.TEXT,
                "title": "WEIRDO Triggers",
                "order": 1,
                "estimated_time": 8,
                "data": {
                    "acronym": "WEIRDO",
                    "triggers": {
                        "W": "Wishes (quiero que...)",
                        "E": "Emotions (me gusta que...)",
                        "I": "Impersonal expressions (es importante que...)",
                        "R": "Requests/Recommendations (recomiendo que...)",
                        "D": "Doubt/Denial (dudo que...)",
                        "O": "Ojalá (ojalá que...)",
                    },
                },
            },
        ],
    },
    {
        "id": "a2-travel",
        "title": "Travel & Transportation",
        "description": "Navigate airports, trains, taxis, and ask for directions like a local.",
        "language": "es",
        "level": CEFRLevel.A2,
        "focus_area": FocusArea.CONVERSATION,
        "duration": 25,
        "xp_reward": 100,
        "prerequisites": ["a1-food"],
        "tags": ["travel", "transportation", "airport", "directions", "practical"],
        "order": 9,
        "content": [
            {
                "content_id": "c1",
                "type": ContentType.DIALOGUE,
                "title": "At the Airport",
                "order": 1,
                "estimated_time": 8,
                "data": {
                    "dialogue": [
                        {"speaker": "Agent", "text": "¿Pasaporte, por favor?", "translation": "Passport, please?"},
                        {"speaker": "Traveler", "text": "Aquí tiene. ¿Puerta de embarque?", "translation": "Here you go. Boarding gate?"},
                    ],
                },
            },
        ],
    },
    # B1 - Intermediate
    {
        "id": "b1-conditionals",
        "title": "Conditional Tense & If Clauses",
        "description": "Express hypothetical situations, make polite requests, and discuss possibilities.",
        "language": "es",
        "level": CEFRLevel.B1,
        "focus_area": FocusArea.GRAMMAR,
        "duration": 30,
        "xp_reward": 200,
        "prerequisites": ["a2-subjunctive-intro"],
        "tags": ["grammar", "conditionals", "hypothetical", "polite-requests"],
        "order": 10,
        "content": [],
    },
    {
        "id": "b1-work",
        "title": "Professional Spanish",
        "description": "Business vocabulary, formal emails, meetings, and workplace conversations.",
        "language": "es",
        "level": CEFRLevel.B1,
        "focus_area": FocusArea.CONVERSATION,
        "duration": 35,
        "xp_reward": 250,
        "prerequisites": ["b1-conditionals"],
        "tags": ["business", "formal", "workplace", "emails", "meetings"],
        "order": 11,
        "content": [],
    },
    {
        "id": "b1-news",
        "title": "News & Current Events",
        "description": "Understand news broadcasts, read articles, and discuss current events.",
        "language": "es",
        "level": CEFRLevel.B1,
        "focus_area": FocusArea.LISTENING,
        "duration": 30,
        "xp_reward": 200,
        "prerequisites": ["b1-work"],
        "tags": ["news", "current events", "listening", "reading", "discussion"],
        "order": 12,
        "content": [],
    },
    # B2 - Upper Intermediate
    {
        "id": "b2-subjunctive-advanced",
        "title": "Advanced Subjunctive Uses",
        "description": "Master imperfect subjunctive, past perfect subjunctive, and complex structures.",
        "language": "es",
        "level": CEFRLevel.B2,
        "focus_area": FocusArea.GRAMMAR,
        "duration": 40,
        "xp_reward": 300,
        "prerequisites": ["b1-conditionals"],
        "tags": ["grammar", "advanced subjunctive", "imperfect", "perfect", "complex-sentences"],
        "order": 13,
        "content": [],
    },
    {
        "id": "b2-idioms",
        "title": "Idioms & Colloquial Expressions",
        "description": "Sound like a native with common idioms, slang, and regional expressions.",
        "language": "es",
        "level": CEFRLevel.B2,
        "focus_area": FocusArea.VOCABULARY,
        "duration": 30,
        "xp_reward": 250,
        "prerequisites": ["b2-subjunctive-advanced"],
        "tags": ["idioms", "slang", "colloquial", "native-speaker", "culture"],
        "order": 14,
        "content": [],
    },
    {
        "id": "b2-debate",
        "title": "Debate & Argumentation",
        "description": "Structure arguments, express opinions, and participate in formal debates.",
        "language": "es",
        "level": CEFRLevel.B2,
        "focus_area": FocusArea.CONVERSATION,
        "duration": 35,
        "xp_reward": 300,
        "prerequisites": ["b2-idioms"],
        "tags": ["debate", "argumentation", "critical-thinking", "formal-speech"],
        "order": 15,
        "content": [],
    },
    # C1 - Advanced
    {
        "id": "c1-literature",
        "title": "Spanish Literature & Analysis",
        "description": "Read and analyze works by Cervantes, Borges, García Márquez, and more.",
        "language": "es",
        "level": CEFRLevel.C1,
        "focus_area": FocusArea.READING,
        "duration": 45,
        "xp_reward": 400,
        "prerequisites": ["b2-debate"],
        "tags": ["literature", "analysis", "classics", "culture", "advanced-reading"],
        "order": 16,
        "content": [],
    },
    {
        "id": "c1-academic",
        "title": "Academic & Technical Writing",
        "description": "Write research papers, technical reports, and formal academic Spanish.",
        "language": "es",
        "level": CEFRLevel.C1,
        "focus_area": FocusArea.WRITING,
        "duration": 40,
        "xp_reward": 350,
        "prerequisites": ["c1-literature"],
        "tags": ["academic", "technical", "research", "formal-writing", "citations"],
        "order": 17,
        "content": [],
    },
    # C2 - Proficient
    {
        "id": "c2-native",
        "title": "Native-Level Mastery",
        "description": "Refine your Spanish to native-like fluency across all registers and contexts.",
        "language": "es",
        "level": CEFRLevel.C2,
        "focus_area": FocusArea.CONVERSATION,
        "duration": 60,
        "xp_reward": 500,
        "prerequisites": ["c1-academic"],
        "tags": ["native-level", "fluency", "accents", "culture", "mastery"],
        "order": 18,
        "content": [],
    },

    # =============================================================================
    # ENGLISH A1 - ADULT TRACK
    # =============================================================================
    {
        "id": "en-a1-greetings-adult",
        "title": "Greetings & Introductions",
        "description": "Learn essential English greetings, farewells, and introductions for everyday situations.",
        "language": "en",
        "level": CEFRLevel.A1,
        "focus_area": FocusArea.CONVERSATION,
        "duration": 15,
        "xp_reward": 50,
        "prerequisites": [],
        "tags": ["basics", "greetings", "conversation", "formal", "informal"],
        "order": 1,
        "target_age_group": "adult",
        "gamification_level": "medium",
        "content": [
            {
                "content_id": "en_a1_greet_c1",
                "type": ContentType.DIALOGUE,
                "title": "Meeting Someone New",
                "order": 1,
                "estimated_time": 5,
                "data": {
                    "dialogue": [
                        {"speaker": "Person A", "text": "Hello! What's your name?", "translation": ""},
                        {"speaker": "Person B", "text": "My name is Sarah. And you?", "translation": ""},
                        {"speaker": "Person A", "text": "I'm John. Nice to meet you.", "translation": ""},
                        {"speaker": "Person B", "text": "Nice to meet you too. Where are you from?", "translation": ""},
                    ],
                    "key_phrases": [
                        {"phrase": "What's your name?", "translation": ""},
                        {"phrase": "My name is...", "translation": ""},
                        {"phrase": "Nice to meet you", "translation": ""},
                        {"phrase": "Where are you from?", "translation": ""},
                    ],
                },
            },
            {
                "content_id": "en_a1_greet_c2",
                "type": ContentType.EXERCISE,
                "title": "Greeting Practice",
                "order": 2,
                "estimated_time": 5,
                "data": {
                    "exercises": [
                        {
                            "type": "multiple_choice",
                            "question": "How do you say 'Good morning' in English?",
                            "options": ["Good morning", "Good night", "Good afternoon", "Hello"],
                            "correct": 0,
                            "explanation": "Good morning is used in the morning until around noon.",
                        },
                        {
                            "type": "fill_blank",
                            "question": "Complete: '_____ name is Anna.'",
                            "answer": "My",
                            "explanation": "Use 'My name is' to introduce yourself.",
                        },
                    ],
                },
            },
            {
                "content_id": "en_a1_greet_c3",
                "type": ContentType.PRONUNCIATION,
                "title": "Key Sounds in Greetings",
                "order": 3,
                "estimated_time": 5,
                "data": {
                    "phonemes": [
                        {"symbol": "/h/", "examples": ["hello", "hi", "how"], "tip": "Breath out gently"},
                        {"symbol": "/n/", "examples": ["name", "nice", "noon"], "tip": "Tongue touches roof of mouth"},
                        {"symbol": "/m/", "examples": ["meet", "morning", "my"], "tip": "Lips together, hum"},
                    ],
                    "practice_words": ["hello", "name", "nice", "meet", "morning"],
                },
            },
        ],
    },
    {
        "id": "en-a1-numbers-adult",
        "title": "Numbers 1-20 & Basic Math",
        "description": "Learn to count from 1 to 20 and use numbers in practical situations.",
        "language": "en",
        "level": CEFRLevel.A1,
        "focus_area": FocusArea.VOCABULARY,
        "duration": 20,
        "xp_reward": 60,
        "prerequisites": ["en-a1-greetings-adult"],
        "tags": ["numbers", "counting", "vocabulary", "practical"],
        "order": 2,
        "target_age_group": "adult",
        "gamification_level": "medium",
        "content": [
            {
                "content_id": "en_a1_num_c1",
                "type": ContentType.FLASHCARD,
                "title": "Numbers 1-20",
                "order": 1,
                "estimated_time": 7,
                "data": {
                    "flashcards": [
                        {"front": "1", "back": "one"}, {"front": "2", "back": "two"}, {"front": "3", "back": "three"},
                        {"front": "4", "back": "four"}, {"front": "5", "back": "five"}, {"front": "6", "back": "six"},
                        {"front": "7", "back": "seven"}, {"front": "8", "back": "eight"}, {"front": "9", "back": "nine"},
                        {"front": "10", "back": "ten"}, {"front": "11", "back": "eleven"}, {"front": "12", "back": "twelve"},
                        {"front": "13", "back": "thirteen"}, {"front": "14", "back": "fourteen"}, {"front": "15", "back": "fifteen"},
                        {"front": "16", "back": "sixteen"}, {"front": "17", "back": "seventeen"}, {"front": "18", "back": "eighteen"},
                        {"front": "19", "back": "nineteen"}, {"front": "20", "back": "twenty"},
                    ],
                },
            },
            {
                "content_id": "en_a1_num_c2",
                "type": ContentType.EXERCISE,
                "title": "Counting Practice",
                "order": 2,
                "estimated_time": 5,
                "data": {
                    "exercises": [
                        {"type": "sequence", "question": "What comes after twelve?", "answer": "thirteen"},
                        {"type": "sequence", "question": "What comes before twenty?", "answer": "nineteen"},
                        {"type": "multiple_choice", "question": "How do you spell 15?", "options": ["fiveteen", "fifteen", "fifty", "fifth"], "correct": 1},
                    ],
                },
            },
            {
                "content_id": "en_a1_num_c3",
                "type": ContentType.READING,
                "title": "Prices & Phone Numbers",
                "order": 3,
                "estimated_time": 8,
                "data": {
                    "text": "Practical English: When shopping, you'll hear prices like 'It's five dollars' or 'That's twelve fifty'. Phone numbers are read digit by digit: 'My number is five-five-five, one-two-three-four.'",
                    "questions": [
                        {"question": "How do you say $12.50?", "answer": "twelve fifty or twelve dollars fifty"},
                        {"question": "How do you read 555-1234?", "answer": "five five five, one two three four"},
                    ],
                },
            },
        ],
    },
    {
        "id": "en-a1-basic-verbs-adult",
        "title": "Essential Verbs: Be, Have, Do",
        "description": "Master the three most important English verbs and their basic forms.",
        "language": "en",
        "level": CEFRLevel.A1,
        "focus_area": FocusArea.GRAMMAR,
        "duration": 25,
        "xp_reward": 80,
        "prerequisites": ["en-a1-greetings-adult"],
        "tags": ["verbs", "grammar", "be", "have", "do", "foundation"],
        "order": 3,
        "target_age_group": "adult",
        "gamification_level": "medium",
        "content": [
            {
                "content_id": "en_a1_verb_c1",
                "type": ContentType.EXERCISE,
                "title": "Verb 'To Be' - Present Simple",
                "order": 1,
                "estimated_time": 8,
                "data": {
                    "explanation": "The verb 'to be' changes: I am, you are, he/she/it is, we are, they are.",
                    "exercises": [
                        {"type": "fill_blank", "question": "I _____ a teacher.", "answer": "am"},
                        {"type": "fill_blank", "question": "She _____ from Spain.", "answer": "is"},
                        {"type": "fill_blank", "question": "We _____ friends.", "answer": "are"},
                        {"type": "multiple_choice", "question": "Choose correct: 'They _____ happy.'", "options": ["is", "am", "are", "be"], "correct": 2},
                    ],
                },
            },
            {
                "content_id": "en_a1_verb_c2",
                "type": ContentType.EXERCISE,
                "title": "Verbs 'Have' & 'Do'",
                "order": 2,
                "estimated_time": 8,
                "data": {
                    "explanation": "Have: I have, you have, he/she/it has. Do: I do, you do, he/she/it does.",
                    "exercises": [
                        {"type": "fill_blank", "question": "He _____ a car.", "answer": "has"},
                        {"type": "fill_blank", "question": "They _____ their homework.", "answer": "do"},
                        {"type": "multiple_choice", "question": "She _____ two sisters.", "options": ["have", "has", "had", "having"], "correct": 1},
                    ],
                },
            },
            {
                "content_id": "en_a1_verb_c3",
                "type": ContentType.QUIZ,
                "title": "Verb Mastery Quiz",
                "order": 3,
                "estimated_time": 9,
                "data": {
                    "questions": [
                        {"type": "multiple_choice", "question": "I _____ 25 years old.", "options": ["am", "is", "are", "have"], "correct": 0},
                        {"type": "multiple_choice", "question": "We _____ a big house.", "options": ["has", "have", "am", "is"], "correct": 1},
                        {"type": "multiple_choice", "question": "_____ you like coffee?", "options": ["Do", "Does", "Are", "Is"], "correct": 0},
                    ],
                },
            },
        ],
    },
    {
        "id": "en-a1-pronunciation-adult",
        "title": "English Vowel Sounds",
        "description": "Master the 12 English vowel sounds that don't exist in many other languages.",
        "language": "en",
        "level": CEFRLevel.A1,
        "focus_area": FocusArea.PRONUNCIATION,
        "duration": 20,
        "xp_reward": 70,
        "prerequisites": ["en-a1-greetings-adult"],
        "tags": ["pronunciation", "vowels", "phonetics", "accent"],
        "order": 4,
        "target_age_group": "adult",
        "gamification_level": "medium",
        "content": [
            {
                "content_id": "en_a1_pron_c1",
                "type": ContentType.PRONUNCIATION,
                "title": "Short vs Long Vowels",
                "order": 1,
                "estimated_time": 7,
                "data": {
                    "phonemes": [
                        {"symbol": "/ɪ/", "examples": ["sit", "bit", "ship"], "tip": "Short, relaxed"},
                        {"symbol": "/i:/", "examples": ["seat", "beat", "sheep"], "tip": "Long, smile wide"},
                        {"symbol": "/ʌ/", "examples": ["cup", "but", "sun"], "tip": "Open mouth, drop jaw"},
                        {"symbol": "/ɑ:/", "examples": ["car", "far", "heart"], "tip": "Long, open wide"},
                    ],
                    "minimal_pairs": [
                        ["sit", "seat"], ["bit", "beat"], ["ship", "sheep"],
                        ["cup", "carp"], ["but", "bart"], ["sun", "sarn"],
                    ],
                },
            },
            {
                "content_id": "en_a1_pron_c2",
                "type": ContentType.AUDIO,
                "title": "Listen & Repeat: Vowel Drills",
                "order": 2,
                "estimated_time": 7,
                "data": {
                    "audio_exercises": [
                        {"word": "sit", "ipa": "/sɪt/"},
                        {"word": "seat", "ipa": "/siːt/"},
                        {"word": "cup", "ipa": "/kʌp/"},
                        {"word": "car", "ipa": "/kɑːr/"},
                    ],
                },
            },
            {
                "content_id": "en_a1_pron_c3",
                "type": ContentType.EXERCISE,
                "title": "Vowel Sound Identification",
                "order": 3,
                "estimated_time": 6,
                "data": {
                    "exercises": [
                        {"type": "listening", "question": "Which word has /i:/ sound?", "options": ["bit", "beat", "bet", "bat"], "correct": 1},
                        {"type": "listening", "question": "Which word has /ʌ/ sound?", "options": ["cat", "cut", "cart", "coat"], "correct": 1},
                    ],
                },
            },
        ],
    },
    {
        "id": "en-a1-family-adult",
        "title": "Family & Relationships",
        "description": "Talk about your family, describe relationships, and ask about others' families.",
        "language": "en",
        "level": CEFRLevel.A1,
        "focus_area": FocusArea.CONVERSATION,
        "duration": 20,
        "xp_reward": 65,
        "prerequisites": ["en-a1-basic-verbs-adult"],
        "tags": ["family", "relationships", "conversation", "personal"],
        "order": 5,
        "target_age_group": "adult",
        "gamification_level": "medium",
        "content": [
            {
                "content_id": "en_a1_fam_c1",
                "type": ContentType.DIALOGUE,
                "title": "Talking About Family",
                "order": 1,
                "estimated_time": 6,
                "data": {
                    "dialogue": [
                        {"speaker": "A", "text": "Do you have any brothers or sisters?"},
                        {"speaker": "B", "text": "Yes, I have one brother and two sisters."},
                        {"speaker": "A", "text": "Are they older or younger?"},
                        {"speaker": "B", "text": "My brother is older. My sisters are younger."},
                    ],
                    "vocabulary": [
                        {"word": "brother", "translation": ""}, {"word": "sister", "translation": ""},
                        {"word": "older", "translation": ""}, {"word": "younger", "translation": ""},
                        {"word": "parents", "translation": ""}, {"word": "children", "translation": ""},
                    ],
                },
            },
            {
                "content_id": "en_a1_fam_c2",
                "type": ContentType.EXERCISE,
                "title": "Family Tree Practice",
                "order": 2,
                "estimated_time": 7,
                "data": {
                    "exercises": [
                        {"type": "matching", "pairs": [
                            {"left": "mother's brother", "right": "uncle"},
                            {"left": "father's sister", "right": "aunt"},
                            {"left": "uncle's child", "right": "cousin"},
                            {"left": "sibling's child", "right": "niece/nephew"},
                        ]},
                        {"type": "fill_blank", "question": "My mother's mother is my _____.", "answer": "grandmother"},
                    ],
                },
            },
            {
                "content_id": "en_a1_fam_c3",
                "type": ContentType.WRITING,
                "title": "Describe Your Family",
                "order": 3,
                "estimated_time": 7,
                "data": {
                    "prompt": "Write 5 sentences about your family. Use: have, be, brother, sister, mother, father.",
                    "example": "I have one brother. He is older than me. My mother is a teacher. My father works in an office. We are a happy family.",
                },
            },
        ],
    },
    {
        "id": "en-a1-food-adult",
        "title": "Food, Drinks & Ordering",
        "description": "Essential vocabulary for restaurants, cafes, and grocery shopping.",
        "language": "en",
        "level": CEFRLevel.A1,
        "focus_area": FocusArea.VOCABULARY,
        "duration": 20,
        "xp_reward": 60,
        "prerequisites": ["en-a1-family-adult"],
        "tags": ["food", "restaurant", "ordering", "shopping", "daily-life"],
        "order": 6,
        "target_age_group": "adult",
        "gamification_level": "medium",
        "content": [
            {
                "content_id": "en_a1_food_c1",
                "type": ContentType.FLASHCARD,
                "title": "Common Foods & Drinks",
                "order": 1,
                "estimated_time": 6,
                "data": {
                    "flashcards": [
                        {"front": " [apple]", "back": "apple"}, {"front": " [U+1F35E]", "back": "bread"},
                        {"front": " [U+1F95B]", "back": "milk"}, {"front": "☕", "back": "coffee"},
                        {"front": " [U+1F357]", "back": "chicken"}, {"front": " [U+1F957]", "back": "salad"},
                        {"front": " [U+1F35A]", "back": "rice"}, {"front": " [U+1F954]", "back": "potato"},
                        {"front": " [U+1F9C0]", "back": "cheese"}, {"front": " [U+1F373]", "back": "egg"},
                    ],
                },
            },
            {
                "content_id": "en_a1_food_c2",
                "type": ContentType.DIALOGUE,
                "title": "At a Restaurant",
                "order": 2,
                "estimated_time": 7,
                "data": {
                    "dialogue": [
                        {"speaker": "Waiter", "text": "Are you ready to order?"},
                        {"speaker": "Customer", "text": "Yes, I'd like the chicken salad, please."},
                        {"speaker": "Waiter", "text": "Would you like anything to drink?"},
                        {"speaker": "Customer", "text": "Water, please. No ice."},
                    ],
                    "key_phrases": [
                        {"phrase": "I'd like...", "translation": ""},
                        {"phrase": "Can I have...?", "translation": ""},
                        {"phrase": "Would you like...?", "translation": ""},
                        {"phrase": "The bill, please.", "translation": ""},
                    ],
                },
            },
            {
                "content_id": "en_a1_food_c3",
                "type": ContentType.EXERCISE,
                "title": "Ordering Practice",
                "order": 3,
                "estimated_time": 7,
                "data": {
                    "exercises": [
                        {"type": "multiple_choice", "question": "Polite way to order: '_____ the fish, please.'", "options": ["Give me", "I want", "I'd like", "Bring me"], "correct": 2},
                        {"type": "fill_blank", "question": "_____ you like dessert?", "answer": "Would"},
                    ],
                },
            },
        ],
    },

    # =============================================================================
    # ENGLISH A1 - CHILD TRACK (Gamified, Playful, Shorter Sessions)
    # =============================================================================
    {
        "id": "en-a1-greetings-child",
        "title": "Hello Friends!  [wave]",
        "description": "Learn to say hello and make new friends in English with fun characters!",
        "language": "en",
        "level": CEFRLevel.A1,
        "focus_area": FocusArea.CONVERSATION,
        "duration": 10,
        "xp_reward": 50,
        "prerequisites": [],
        "tags": ["basics", "greetings", "fun", "characters", "kids"],
        "order": 1,
        "target_age_group": "child",
        "gamification_level": "full",
        "content": [
            {
                "content_id": "en_a1_greet_ch_c1",
                "type": ContentType.DIALOGUE,
                "title": "Meet Buddy the Bear!  [U+1F43B]",
                "order": 1,
                "estimated_time": 4,
                "data": {
                    "dialogue": [
                        {"speaker": "Buddy", "text": "Hello! I'm Buddy! What's your name?"},
                        {"speaker": "You", "text": "I'm [Your Name]!"},
                        {"speaker": "Buddy", "text": "Nice to meet you! Let's play!"},
                    ],
                    "key_phrases": [
                        {"phrase": "Hello!", "emoji": " [wave]"},
                        {"phrase": "What's your name?", "emoji": "❓"},
                        {"phrase": "Nice to meet you!", "emoji": " [U+1F60A]"},
                    ],
                },
            },
            {
                "content_id": "en_a1_greet_ch_c2",
                "type": ContentType.EXERCISE,
                "title": "Greeting Game!  [U+1F3AE]",
                "order": 2,
                "estimated_time": 3,
                "data": {
                    "exercises": [
                        {
                            "type": "game",
                            "name": "Match the Greeting",
                            "question": "Drag the greeting to the right time!",
                            "items": [
                                {"greeting": "Good morning! ☀", "time": "Morning"},
                                {"greeting": "Good afternoon!  [U+1F324]", "time": "Afternoon"},
                                {"greeting": "Good evening!  [U+1F319]", "time": "Evening"},
                                {"greeting": "Good night!  [U+1F31F]", "time": "Bedtime"},
                            ],
                        },
                    ],
                },
            },
            {
                "content_id": "en_a1_greet_ch_c3",
                "type": ContentType.PRONUNCIATION,
                "title": "Silly Sounds with Buddy!  [U+1F3B5]",
                "order": 3,
                "estimated_time": 3,
                "data": {
                    "phonemes": [
                        {"symbol": "/h/", "examples": ["hello", "hi", "happy"], "tip": "Blow out a candle!  [U+1F56F]"},
                        {"symbol": "/n/", "examples": ["name", "nice", "no"], "tip": "Touch your nose!  [U+1F443]"},
                    ],
                    "game": "Say each word 3 times fast! Buddy will give you stars! ⭐",
                },
            },
        ],
    },
    {
        "id": "en-a1-numbers-child",
        "title": "Counting Adventure! 123",
        "description": "Count from 1 to 10 with fun animals and earn rainbow stars!",
        "language": "en",
        "level": CEFRLevel.A1,
        "focus_area": FocusArea.VOCABULARY,
        "duration": 12,
        "xp_reward": 60,
        "prerequisites": ["en-a1-greetings-child"],
        "tags": ["numbers", "counting", "animals", "game", "kids"],
        "order": 2,
        "target_age_group": "child",
        "gamification_level": "full",
        "content": [
            {
                "content_id": "en_a1_num_ch_c1",
                "type": ContentType.FLASHCARD,
                "title": "Animal Counting!  [U+1F436] [U+1F431] [U+1F42D]",
                "order": 1,
                "estimated_time": 5,
                "data": {
                    "flashcards": [
                        {"front": "1  [U+1F436]", "back": "one dog"}, {"front": "2  [U+1F431]", "back": "two cats"},
                        {"front": "3  [U+1F42D]", "back": "three mice"}, {"front": "4  [U+1F430]", "back": "four bunnies"},
                        {"front": "5  [U+1F438]", "back": "five frogs"}, {"front": "6  [U+1F437]", "back": "six pigs"},
                        {"front": "7  [U+1F42E]", "back": "seven cows"}, {"front": "8  [U+1F414]", "back": "eight chickens"},
                        {"front": "9  [U+1F411]", "back": "nine sheep"}, {"front": "10  [U+1F434]", "back": "ten horses"},
                    ],
                },
            },
            {
                "content_id": "en_a1_num_ch_c2",
                "type": ContentType.EXERCISE,
                "title": "Feed the Animals!  [apple]",
                "order": 2,
                "estimated_time": 4,
                "data": {
                    "exercises": [
                        {
                            "type": "game",
                            "name": "Count & Feed",
                            "question": "Give each animal the right number of treats!",
                            "items": [
                                {"animal": " [U+1F436]", "treats": 3, "instruction": "Three bones for the dog!"},
                                {"animal": " [U+1F431]", "treats": 5, "instruction": "Five fish for the cat!"},
                                {"animal": " [U+1F430]", "treats": 2, "instruction": "Two carrots for the bunny!"},
                            ],
                        },
                    ],
                },
            },
            {
                "content_id": "en_a1_num_ch_c3",
                "type": ContentType.AUDIO,
                "title": "Number Song!  [U+1F3B5]",
                "order": 3,
                "estimated_time": 3,
                "data": {
                    "song": {
                        "title": "Ten Little Animals",
                        "lyrics": "One little, two little, three little animals...\nFour little, five little, six little animals...\nSeven little, eight little, nine little animals...\nTen little animals dancing around!  [tada]",
                    },
                },
            },
        ],
    },
    {
        "id": "en-a1-colors-child",
        "title": "Rainbow Colors!  [U+1F308]",
        "description": "Learn all the colors of the rainbow with magical color friends!",
        "language": "en",
        "level": CEFRLevel.A1,
        "focus_area": FocusArea.VOCABULARY,
        "duration": 10,
        "xp_reward": 55,
        "prerequisites": ["en-a1-numbers-child"],
        "tags": ["colors", "rainbow", "magic", "game", "kids"],
        "order": 3,
        "target_age_group": "child",
        "gamification_level": "full",
        "content": [
            {
                "content_id": "en_a1_col_ch_c1",
                "type": ContentType.FLASHCARD,
                "title": "Meet the Color Friends!  [U+1F3A8]",
                "order": 1,
                "estimated_time": 4,
                "data": {
                    "flashcards": [
                        {"front": "❤", "back": "Red"}, {"front": " [U+1F9E1]", "back": "Orange"},
                        {"front": " [U+1F49B]", "back": "Yellow"}, {"front": " [U+1F49A]", "back": "Green"},
                        {"front": " [U+1F499]", "back": "Blue"}, {"front": " [U+1F49C]", "back": "Purple"},
                        {"front": " [U+1FA77]", "back": "Pink"}, {"front": " [U+1F90E]", "back": "Brown"},
                    ],
                },
            },
            {
                "content_id": "en_a1_col_ch_c2",
                "type": ContentType.EXERCISE,
                "title": "Color Hunt!  [search]",
                "order": 2,
                "estimated_time": 3,
                "data": {
                    "exercises": [
                        {
                            "type": "game",
                            "name": "I Spy with My Little Eye",
                            "question": "Find something RED in your room!  [U+1F534]",
                            "items": [
                                {"color": "Red", "emoji": " [U+1F534]", "examples": ["apple", "fire truck", "strawberry"]},
                                {"color": "Blue", "emoji": " [U+1F535]", "examples": ["sky", "blueberry", "jeans"]},
                                {"color": "Yellow", "emoji": " [U+1F7E1]", "examples": ["sun", "banana", "duck"]},
                            ],
                        },
                    ],
                },
            },
            {
                "content_id": "en_a1_col_ch_c3",
                "type": ContentType.PRONUNCIATION,
                "title": "Color Sounds!  [U+1F3B6]",
                "order": 3,
                "estimated_time": 3,
                "data": {
                    "phonemes": [
                        {"symbol": "/r/", "examples": ["red", "rainbow", "rose"], "tip": "Growl like a tiger!  [U+1F42F]"},
                        {"symbol": "/l/", "examples": ["yellow", "blue", "green"], "tip": "Lift your tongue up!  [U+1F445]"},
                    ],
                    "game": "Say each color while jumping!  [U+1F998]",
                },
            },
        ],
    },
    {
        "id": "en-a1-animals-child",
        "title": "Animal Friends!  [U+1F981] [U+1F418] [U+1F412]",
        "description": "Meet wild animals from around the world and learn their English names!",
        "language": "en",
        "level": CEFRLevel.A1,
        "focus_area": FocusArea.VOCABULARY,
        "duration": 12,
        "xp_reward": 65,
        "prerequisites": ["en-a1-colors-child"],
        "tags": ["animals", "wild", "zoo", "sounds", "kids"],
        "order": 4,
        "target_age_group": "child",
        "gamification_level": "full",
        "content": [
            {
                "content_id": "en_a1_ani_ch_c1",
                "type": ContentType.DIALOGUE,
                "title": "Zoo Adventure!  [U+1F992]",
                "order": 1,
                "estimated_time": 5,
                "data": {
                    "dialogue": [
                        {"speaker": "Guide", "text": "Welcome to the Magic Zoo! Look, a lion!  [U+1F981]"},
                        {"speaker": "You", "text": "Wow! The lion says ROAR!"},
                        {"speaker": "Guide", "text": "And here's an elephant!  [U+1F418]"},
                        {"speaker": "You", "text": "The elephant goes TRUMPET!"},
                    ],
                    "vocabulary": [
                        {"word": "lion", "sound": "ROAR!  [U+1F981]"},
                        {"word": "elephant", "sound": "TRUMPET!  [U+1F418]"},
                        {"word": "monkey", "sound": "OOH OOH!  [U+1F412]"},
                        {"word": "giraffe", "sound": "*munch munch*  [U+1F992]"},
                        {"word": "zebra", "sound": "*neigh*  [U+1F993]"},
                    ],
                },
            },
            {
                "content_id": "en_a1_ani_ch_c2",
                "type": ContentType.EXERCISE,
                "title": "Animal Sounds Game!  [U+1F3AE]",
                "order": 2,
                "estimated_time": 4,
                "data": {
                    "exercises": [
                        {
                            "type": "game",
                            "name": "Guess the Animal Sound",
                            "question": "Listen and pick the right animal!",
                            "items": [
                                {"sound": "ROAR!", "options": ["lion", "cat", "dog"], "correct": "lion"},
                                {"sound": "MOO!", "options": ["cow", "pig", "sheep"], "correct": "cow"},
                                {"sound": "QUACK!", "options": ["duck", "chicken", "bird"], "correct": "duck"},
                            ],
                        },
                    ],
                },
            },
            {
                "content_id": "en_a1_ani_ch_c3",
                "type": ContentType.READING,
                "title": "My Favorite Animal Book  [book]",
                "order": 3,
                "estimated_time": 3,
                "data": {
                    "story": {
                        "title": "The Lion Who Loved Colors",
                        "pages": [
                            "Leo the Lion loved RED apples.  [apple]",
                            "Leo the Lion loved BLUE skies.  [U+1F324]",
                            "Leo the Lion loved YELLOW sun. ☀",
                            "Leo loved ALL the colors!  [U+1F308]",
                        ],
                    },
                },
            },
        ],
    },
    {
        "id": "en-a1-actions-child",
        "title": "Action Heroes!  [U+1F3C3] [male] [U+1F938] [female]",
        "description": "Run, jump, dance, and sing! Learn action words by moving your body!",
        "language": "en",
        "level": CEFRLevel.A1,
        "focus_area": FocusArea.CONVERSATION,
        "duration": 15,
        "xp_reward": 70,
        "prerequisites": ["en-a1-animals-child"],
        "tags": ["actions", "verbs", "movement", "game", "kids", "TPR"],
        "order": 5,
        "target_age_group": "child",
        "gamification_level": "full",
        "content": [
            {
                "content_id": "en_a1_act_ch_c1",
                "type": ContentType.DIALOGUE,
                "title": "Simon Says with Super Simon!  [U+1F9B8]",
                "order": 1,
                "estimated_time": 5,
                "data": {
                    "dialogue": [
                        {"speaker": "Super Simon", "text": "Simon says... JUMP!  [U+1F938]"},
                        {"speaker": "You", "text": "*Jumps high* Wheee!"},
                        {"speaker": "Super Simon", "text": "Simon says... DANCE!  [U+1F483]"},
                        {"speaker": "You", "text": "*Dances* La la la!"},
                    ],
                    "actions": [
                        {"verb": "jump", "emoji": " [U+1F938]"},
                        {"verb": "run", "emoji": " [U+1F3C3]"},
                        {"verb": "dance", "emoji": " [U+1F483]"},
                        {"verb": "clap", "emoji": " [U+1F44F]"},
                        {"verb": "stomp", "emoji": " [U+1F9B6]"},
                        {"verb": "spin", "emoji": " [U+1F300]"},
                    ],
                },
            },
            {
                "content_id": "en_a1_act_ch_c2",
                "type": ContentType.EXERCISE,
                "title": "Action Hero Training!  [U+1F3CB]",
                "order": 2,
                "estimated_time": 5,
                "data": {
                    "exercises": [
                        {
                            "type": "game",
                            "name": "Do What I Say!",
                            "question": "Super Simon shows an action. Do it and say the word!",
                            "items": [
                                {"action": "Touch your toes!  [U+1F447]", "word": "touch"},
                                {"action": "Wave your hands!  [wave]", "word": "wave"},
                                {"action": "March in place!  [U+1F6B6]", "word": "march"},
                                {"action": "Fly like a bird!  [U+1F426]", "word": "fly"},
                            ],
                        },
                    ],
                },
            },
            {
                "content_id": "en_a1_act_ch_c3",
                "type": ContentType.AUDIO,
                "title": "Action Song: Head, Shoulders, Knees & Toes!  [U+1F3B5]",
                "order": 3,
                "estimated_time": 5,
                "data": {
                    "song": {
                        "title": "Head, Shoulders, Knees and Toes",
                        "lyrics": "Head, shoulders, knees and toes, knees and toes!  [U+1F3B6]\nHead, shoulders, knees and toes, knees and toes!\nEyes and ears and mouth and nose!\nHead, shoulders, knees and toes, knees and toes!  [tada]",
                        "actions": ["head", "shoulders", "knees", "toes", "eyes", "ears", "mouth", "nose"],
                    },
                },
            },
        ],
    },
    {
        "id": "en-a1-family-child",
        "title": "My Family Tree!  [U+1F468] [U+1F469] [U+1F467] [U+1F466]",
        "description": "Meet Mom, Dad, Grandma, Grandpa and make your own family portrait!",
        "language": "en",
        "level": CEFRLevel.A1,
        "focus_area": FocusArea.CONVERSATION,
        "duration": 12,
        "xp_reward": 65,
        "prerequisites": ["en-a1-actions-child"],
        "tags": ["family", "parents", "grandparents", "love", "kids"],
        "order": 6,
        "target_age_group": "child",
        "gamification_level": "full",
        "content": [
            {
                "content_id": "en_a1_fam_ch_c1",
                "type": ContentType.DIALOGUE,
                "title": "Family Photo Album!  [U+1F4F8]",
                "order": 1,
                "estimated_time": 4,
                "data": {
                    "dialogue": [
                        {"speaker": "Mom", "text": "This is Daddy! He's strong!  [flex]"},
                        {"speaker": "Dad", "text": "This is Grandma! She bakes cookies!  [U+1F36A]"},
                        {"speaker": "Grandma", "text": "This is Grandpa! He tells great stories!  [U+1F4D6]"},
                        {"speaker": "You", "text": "I love my family! ❤"},
                    ],
                    "vocabulary": [
                        {"word": "mommy", "emoji": " [U+1F469]"}, {"word": "daddy", "emoji": " [U+1F468]"},
                        {"word": "grandma", "emoji": " [U+1F475]"}, {"word": "grandpa", "emoji": " [U+1F474]"},
                        {"word": "brother", "emoji": " [U+1F466]"}, {"word": "sister", "emoji": " [U+1F467]"},
                    ],
                },
            },
            {
                "content_id": "en_a1_fam_ch_c2",
                "type": ContentType.EXERCISE,
                "title": "Build Your Family Tree!  [U+1F333]",
                "order": 2,
                "estimated_time": 4,
                "data": {
                    "exercises": [
                        {
                            "type": "game",
                            "name": "Drag & Drop Family",
                            "question": "Put each family member on the tree!",
                            "items": [
                                {"position": "top", "role": "Grandma & Grandpa  [U+1F475] [U+1F474]"},
                                {"position": "middle", "role": "Mommy & Daddy  [U+1F469] [U+1F468]"},
                                {"position": "bottom", "role": "You & Siblings  [U+1F466] [U+1F467]"},
                            ],
                        },
                    ],
                },
            },
            {
                "content_id": "en_a1_fam_ch_c3",
                "type": ContentType.WRITING,
                "title": "Draw & Label Your Family!  [U+1F3A8]",
                "order": 3,
                "estimated_time": 4,
                "data": {
                    "prompt": "Draw your family! Write the English word under each person.",
                    "template": "This is my _____. (mommy/daddy/grandma/grandpa/brother/sister)",
                },
            },
        ],
    },
]


async def seed_curriculum(db: AsyncSession):
    """Seed the curriculum into the database"""
    print("Seeding curriculum...")
    
    for lesson_data in CURRICULUM_DATA:
        # Check if lesson exists
        result = await db.execute(
            select(Lesson).where(Lesson.id == lesson_data["id"])
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            print(f"  Lesson {lesson_data['id']} already exists, updating...")
            for key, value in lesson_data.items():
                if key != "content":
                    setattr(existing, key, value)
            existing.updated_at = datetime.utcnow()
            lesson = existing
        else:
            print(f"  Creating lesson {lesson_data['id']}...")
            content = lesson_data.pop("content", [])
            lesson = Lesson(**lesson_data)
            db.add(lesson)
            await db.flush()
            
            # Add content
            for c in content:
                lesson_content = LessonContent(
                    lesson_id=lesson.id,
                    content_id=c["content_id"],
                    type=c["type"],
                    title=c["title"],
                    order=c["order"],
                    estimated_time=c["estimated_time"],
                    data=c["data"],
                    xp_reward=0,
                )
                db.add(lesson_content)
    
    await db.commit()
    print("Curriculum seeded successfully!")


async def main():
    await init_db()
    async with AsyncSessionLocal() as db:
        await seed_curriculum(db)


if __name__ == "__main__":
    asyncio.run(main())