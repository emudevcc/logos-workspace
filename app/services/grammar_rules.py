"""Curated grammar rules for the deterministic Rule-of-the-Day feature.

Selection is date-based (``date.toordinal()``), so every day yields one stable
rule without any external call, mirroring the Word-of-the-Day rotation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.schemas.learning import GrammarRule


@dataclass(frozen=True, slots=True)
class _Rule:
    id: str
    title: str
    rule: str
    examples: tuple[str, str]
    common_error: str


_RULES: tuple[_Rule, ...] = (
    _Rule(
        "present-perfect-vs-past-simple",
        "Present perfect vs. past simple",
        "Use the present perfect for a past action with present relevance (often with "
        "'ever', 'never', 'already', 'yet', 'since'); use the past simple for a finished "
        "action at a stated past time.",
        (
            "I've already sent the report. (still relevant now)",
            "I sent the report yesterday morning. (finished, stated time)",
        ),
        "Using the present perfect with a finished time phrase: 'I have sent it yesterday.'",
    ),
    _Rule(
        "reported-speech-backshift",
        "Reported speech backshift",
        "When reporting speech after a past reporting verb, shift the tense one step back "
        "and adjust pronouns/time words: present → past, past → past perfect, 'will' → 'would'.",
        (
            "Direct: \"I'll review it tomorrow.\" → Reported: She said she would "
            "review it the next day.",
            "Direct: \"We finished early.\" → Reported: They said they had finished early.",
        ),
        "Keeping 'will' unchanged: 'She said she will review it' when the reporting verb is past.",
    ),
    _Rule(
        "third-conditional",
        "Third conditional (past regret)",
        "Use 'if + past perfect' + 'would have + past participle' to talk about an unreal "
        "past situation and its imagined result.",
        (
            "If we had caught the bug earlier, we would have avoided the outage.",
            "She would have joined the call if the invitation had reached her inbox.",
        ),
        "Mixing the second conditional: 'If we caught it earlier, we would have avoided it.'",
    ),
    _Rule(
        "gerund-vs-infinitive",
        "Gerund vs. infinitive",
        "Some verbs take a gerund (enjoy, avoid, consider, finish, suggest, risk), some an "
        "infinitive (decide, hope, plan, agree, refuse, manage), and some change meaning "
        "(stop, remember, try).",
        (
            "We avoided shipping on Friday. (gerund)",
            "We decided to ship on Monday. (infinitive)",
        ),
        "Using an infinitive after 'suggest': 'She suggested to delay the release.'",
    ),
    _Rule(
        "articles-with-abstract-nouns",
        "Articles with abstract and general nouns",
        "Use no article for general/abstract ideas ('success', 'leadership', 'technology'), "
        "but use 'the' for a specific, already-identified instance.",
        (
            "Innovation drives growth. (general)",
            "The innovation that changed the market was mobile payments. (specific)",
        ),
        "Adding 'the' to general statements: 'The technology is changing fast' (general use).",
    ),
    _Rule(
        "subject-verb-agreement",
        "Subject–verb agreement",
        "The verb agrees with the subject, not the nearest noun. Singular subjects like "
        "'the team', 'everyone', 'each of', and 'neither…nor' (singular options) take a "
        "singular verb.",
        (
            "The list of requirements is long. (subject = 'list')",
            "Each of the reports has a summary. (subject = 'each')",
        ),
        "Agreeing with the nearest noun: 'The list of requirements are long.'",
    ),
    _Rule(
        "relative-clauses",
        "Defining vs. non-defining relative clauses",
        "Use 'that'/'which' without commas for defining clauses (essential), and 'which'/'who' "
        "with commas for non-defining clauses (extra info). Never use 'that' after a comma.",
        (
            "The report that we shipped on Friday raised a red flag. (defining)",
            "The report, which we shipped on Friday, raised a red flag. (non-defining)",
        ),
        "Using 'that' in a non-defining clause: 'The report, that we shipped, raised a flag.'",
    ),
    _Rule(
        "modals-of-deduction",
        "Modals of deduction (past)",
        "Use 'must have' for near-certainty, 'might/may/could have' for possibility, and "
        "'can't have' for impossibility about the past.",
        (
            "The server must have crashed — the logs stopped at 2 a.m.",
            "They can't have finished the migration already.",
        ),
        "Using 'must' for impossibility: 'They mustn't have done it' (use 'can't have').",
    ),
    _Rule(
        "inversion-after-negative-adverbials",
        "Inversion after negative adverbials",
        "Place 'Never', 'Rarely', 'Not only', 'Hardly', 'Seldom', 'No sooner' at the start "
        "of a clause and invert subject and auxiliary verb for a formal, emphatic tone.",
        (
            "Not only did we miss the deadline, but we also lost the client.",
            "Rarely does a single test catch every regression.",
        ),
        "Keeping normal word order: 'Not only we missed the deadline…' (missing inversion).",
    ),
    _Rule(
        "prepositional-phrases",
        "Preposition choice in fixed phrases",
        "Certain verbs and adjectives lock to one preposition: 'depend on', 'responsible for', "
        "'interested in', 'good at', 'afraid of', 'deal with'. Learn them as chunks.",
        (
            "The rollout depends on the data migration being complete.",
            "She is responsible for the quarterly revenue forecast.",
        ),
        "Swapping prepositions: 'depend of', 'responsible of', 'good in'.",
    ),
)

RULE_COUNT: int = len(_RULES)


def list_rules() -> list[GrammarRule]:
    """Return all curated rules (for browsing and testing)."""
    return [
        GrammarRule(
            id=rule.id,
            title=rule.title,
            rule=rule.rule,
            examples=list(rule.examples),
            common_error=rule.common_error,
        )
        for rule in _RULES
    ]


def rule_for_date(day: date) -> GrammarRule:
    """Return the stable Rule-of-the-Day for ``day``."""
    rule = _RULES[day.toordinal() % len(_RULES)]
    return GrammarRule(
        id=rule.id,
        title=rule.title,
        rule=rule.rule,
        examples=list(rule.examples),
        common_error=rule.common_error,
    )
