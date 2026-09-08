"""Curated minimal pairs and pronunciation pitfalls for Spanish speakers.

Deterministic data used by the free pronunciation drill (no LLM, no cost).
"""

from __future__ import annotations

from app.schemas.learning import MinimalPair, Pitfall

MINIMAL_PAIRS: tuple[MinimalPair, ...] = (
    MinimalPair(a="ship", b="sheep", ipa_a="/ʃɪp/", ipa_b="/ʃiːp/"),
    MinimalPair(a="bit", b="beat", ipa_a="/bɪt/", ipa_b="/biːt/"),
    MinimalPair(a="sit", b="seat", ipa_a="/sɪt/", ipa_b="/siːt/"),
    MinimalPair(a="fill", b="feel", ipa_a="/fɪl/", ipa_b="/fiːl/"),
    MinimalPair(a="live", b="leave", ipa_a="/lɪv/", ipa_b="/liːv/"),
    MinimalPair(a="it", b="eat", ipa_a="/ɪt/", ipa_b="/iːt/"),
    MinimalPair(a="van", b="ban", ipa_a="/væn/", ipa_b="/bæn/"),
    MinimalPair(a="vest", b="best", ipa_a="/vest/", ipa_b="/best/"),
    MinimalPair(a="very", b="berry", ipa_a="/ˈveri/", ipa_b="/ˈberi/"),
    MinimalPair(a="think", b="sink", ipa_a="/θɪŋk/", ipa_b="/sɪŋk/"),
    MinimalPair(a="thick", b="sick", ipa_a="/θɪk/", ipa_b="/sɪk/"),
    MinimalPair(a="three", b="tree", ipa_a="/θriː/", ipa_b="/triː/"),
    MinimalPair(a="cat", b="cut", ipa_a="/kæt/", ipa_b="/kʌt/"),
    MinimalPair(a="hat", b="hut", ipa_a="/hæt/", ipa_b="/hʌt/"),
    MinimalPair(a="bed", b="bad", ipa_a="/bed/", ipa_b="/bæd/"),
    MinimalPair(a="pen", b="pan", ipa_a="/pen/", ipa_b="/pæn/"),
    MinimalPair(a="wish", b="witch", ipa_a="/wɪʃ/", ipa_b="/wɪtʃ/"),
    MinimalPair(a="shoes", b="choose", ipa_a="/ʃuːz/", ipa_b="/tʃuːz/"),
    MinimalPair(a="see", b="she", ipa_a="/siː/", ipa_b="/ʃiː/"),
    MinimalPair(a="work", b="walk", ipa_a="/wɜːk/", ipa_b="/wɔːk/"),
    MinimalPair(a="bird", b="board", ipa_a="/bɜːd/", ipa_b="/bɔːd/"),
    MinimalPair(a="eyes", b="ice", ipa_a="/aɪz/", ipa_b="/aɪs/"),
    # ── extended set (vowel length/quality, /i/-/e/, /uː/-/ʊ/, voicing) ──
    MinimalPair(a="bin", b="bean", ipa_a="/bɪn/", ipa_b="/biːn/"),
    MinimalPair(a="chick", b="cheek", ipa_a="/tʃɪk/", ipa_b="/tʃiːk/"),
    MinimalPair(a="bit", b="bet", ipa_a="/bɪt/", ipa_b="/bet/"),
    MinimalPair(a="did", b="dead", ipa_a="/dɪd/", ipa_b="/ded/"),
    MinimalPair(a="pin", b="pen", ipa_a="/pɪn/", ipa_b="/pen/"),
    MinimalPair(a="fool", b="full", ipa_a="/fuːl/", ipa_b="/fʊl/"),
    MinimalPair(a="pool", b="pull", ipa_a="/puːl/", ipa_b="/pʊl/"),
    MinimalPair(a="food", b="foot", ipa_a="/fuːd/", ipa_b="/fʊt/"),
    MinimalPair(a="cup", b="cop", ipa_a="/kʌp/", ipa_b="/kɒp/"),
    MinimalPair(a="luck", b="lock", ipa_a="/lʌk/", ipa_b="/lɒk/"),
    MinimalPair(a="bat", b="but", ipa_a="/bæt/", ipa_b="/bʌt/"),
    MinimalPair(a="ten", b="tan", ipa_a="/ten/", ipa_b="/tæn/"),
    MinimalPair(a="fail", b="fell", ipa_a="/feɪl/", ipa_b="/fel/"),
    MinimalPair(a="late", b="let", ipa_a="/leɪt/", ipa_b="/let/"),
    MinimalPair(a="ship", b="chip", ipa_a="/ʃɪp/", ipa_b="/tʃɪp/"),
    MinimalPair(a="shop", b="chop", ipa_a="/ʃɒp/", ipa_b="/tʃɒp/"),
    MinimalPair(a="jet", b="yet", ipa_a="/dʒet/", ipa_b="/jet/"),
    MinimalPair(a="sue", b="zoo", ipa_a="/suː/", ipa_b="/zuː/"),
    MinimalPair(a="bet", b="bed", ipa_a="/bet/", ipa_b="/bed/"),
    MinimalPair(a="bit", b="bid", ipa_a="/bɪt/", ipa_b="/bɪd/"),
    MinimalPair(a="cap", b="cape", ipa_a="/kæp/", ipa_b="/keɪp/"),
    MinimalPair(a="man", b="main", ipa_a="/mæn/", ipa_b="/meɪn/"),
)

SPANISH_PITFALLS: tuple[Pitfall, ...] = (
    Pitfall(issue="/v/ vs /b/", tip="'very' vs 'berry': keep /v/ voiced, lips and teeth."),
    Pitfall(issue="/θ/ vs /s/", tip="'think' vs 'sink': tongue between teeth for 'th'."),
    Pitfall(issue="Short vs long vowels", tip="Lengthen 'sheep' vs 'ship', 'beat' vs 'bit'."),
    Pitfall(issue="Initial s + consonant", tip="Say 'Spain', not 'eSpain': no vowel before sp."),
    Pitfall(issue="Final consonant clusters", tip="Say every consonant in 'asked' and 'texts'."),
    Pitfall(issue="Silent h", tip="Silent in 'hour', 'honest'; keep it in 'house', 'hotel'."),
    Pitfall(issue="/ʃ/ vs /tʃ/", tip="'sheep' vs 'cheap': /ʃ/ smooth, /tʃ/ starts with a stop."),
    Pitfall(issue="/s/ vs /z/ endings", tip="'ice' ends in /s/, 'eyes' in /z/."),
    Pitfall(issue="Word stress", tip="Stress 'DE-ve-lop' but 'in-for-MA-tion'."),
    Pitfall(issue="/d/ vs /ð/", tip="'day' vs 'they': /ð/ is a soft voiced 'th'."),
)
