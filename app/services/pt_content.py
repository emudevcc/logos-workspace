"""Curated PT-BR study content: words, grammar rules, pronunciation data.

All datasets are deterministic (no LLM, no cost). Every item carries a short
Spanish scaffolding note (``nota_es``) targeting the transfer traps of a native
Spanish speaker learning Brazilian Portuguese at an intermediate/advanced level.
"""

from __future__ import annotations

import random
from collections import deque
from dataclasses import dataclass
from datetime import date

from app.schemas.pt import (
    PtGrammarRule,
    PtMinimalPair,
    PtPitfall,
    PtSentence,
    PtWordCategory,
    PtWordOfDay,
)


@dataclass(frozen=True, slots=True)
class _Word:
    expression: str
    category: PtWordCategory
    definition_pt: str
    nota_es: str
    examples: tuple[str, str]


_WORDS: tuple[_Word, ...] = (
    _Word(
        "dar certo",
        "expressao",
        "Funcionar como esperado; alcançar o resultado desejado.",
        "¡Ojo! No significa 'dar por cierto'; equivale a 'salir bien / funcionar'.",
        ("A ideia até que deu certo no piloto.", "Espero que a apresentação dê certo amanhã."),
    ),
    _Word(
        "valer a pena",
        "expressao",
        "Ser útil ou recompensador, apesar do esforço.",
        "= 'merecer la pena' en español.",
        ("Vale a pena estudar um pouco todo dia.", "Não valeu a pena acordar tão cedo."),
    ),
    _Word(
        "ficar de olho",
        "expressao",
        "Observar com atenção; vigiar de perto.",
        "Literal 'quedarse de ojo': significa 'estar atento / vigilar'.",
        ("Fica de olho no prazo do projeto.", "Vou ficar de olho nas novidades."),
    ),
    _Word(
        "fazer sentido",
        "expressao",
        "Ser lógico, compreensível ou coerente.",
        "= 'tener sentido'. A construção é com o verbo 'fazer'.",
        ("Essa explicação não faz sentido.", "Faz sentido começar pelo mais simples."),
    ),
    _Word(
        "a gente",
        "expressao",
        "Forma coloquial de 'nós' — sempre com o verbo na 3ª pessoa do singular.",
        "Como en español 'la gente', pero en PT 'a gente' = 'nosotros'.",
        ("A gente se vê amanhã?", "A gente estava falando sobre você."),
    ),
    _Word(
        "de repente",
        "expressao",
        "No Brasil, muitas vezes significa 'talvez, por acaso'.",
        "En España 'de repente' = 'de pronto'; en Brasil suele ser 'tal vez'.",
        ("De repente ele não vem hoje.", "De repente a gente pode marcar outro dia."),
    ),
    _Word(
        "pelo visto",
        "expressao",
        "Parece que; segundo as aparências.",
        "= 'por lo visto' en español.",
        ("Pelo visto a reunião foi adiada.", "Pelo visto você gostou do livro."),
    ),
    _Word(
        "tanto faz",
        "expressao",
        "Tanto uma opção quanto a outra; não importa.",
        "= 'me da igual'. Resposta neutra para escolhas.",
        ("— Café ou chá? — Tanto faz.", "Tanto faz o dia, desde que a gente se veja."),
    ),
    _Word(
        "com certeza",
        "expressao",
        "Com toda segurança; claro que sim.",
        "= 'claro que sí / por supuesto'.",
        ("Você vem na festa? Com certeza!", "Com certeza vamos visitar você."),
    ),
    _Word(
        "por enquanto",
        "expressao",
        "No momento atual; por ora.",
        "= 'por ahora' en español.",
        ("Por enquanto está tudo certo.", "Por enquanto, prefiro ficar em casa."),
    ),
    _Word(
        "sem querer",
        "expressao",
        "Sem intenção; por acidente.",
        "Mantém o sentido do espanhol 'sin querer'.",
        ("Sem querer, apaguei o arquivo.", "Ele sem querer derrubou o copo."),
    ),
    _Word(
        "saudade",
        "palavra",
        "Sentimento de falta de algo ou alguém; desejo de rever.",
        "≈ 'morriña' gallega; não há tradução exata em espanhol.",
        ("Sinto saudade da minha cidade.", "Que saudade de você!"),
    ),
    _Word(
        "jeito",
        "palavra",
        "Modo, maneira; também habilidade ou traço.",
        "Não é o espanhol 'hecho'; 'do jeito que' = 'tal como'.",
        ("Faz do jeito que você achar melhor.", "Ele tem um jeito muito calmo."),
    ),
    _Word(
        "esquisito",
        "palavra",
        "Estranho, raro, diferente do comum.",
        "Falso amigo: o espanhol 'exquisito' = 'requintado/excelente', não 'esquisito'.",
        ("Que som esquisito é esse?", "O filme é bom, mas o final é esquisito."),
    ),
    _Word(
        "atender",
        "palavra",
        "Responder (telefone), receber (cliente), dar atenção a um pedido.",
        "PT 'atender' = atender llamada/cliente; 'prestar atenção' = 'atender' en español.",
        ("Não atendi porque estava em reunião.", "A recepcionista atendeu todo mundo."),
    ),
    _Word(
        "realizar",
        "palavra",
        "Executar, levar a cabo.",
        "Não significa 'darse cuenta'! PT: 'perceber/notar'.",
        ("A equipe realizou o sonho de lançar o app.", "Percebi que esqueci a chave."),
    ),
    _Word(
        "data",
        "palavra",
        "Indicação do dia, mês e ano; dia marcado.",
        "PT 'data' = 'fecha'; o espanhol 'dato' = PT 'dado'.",
        ("Qual é a data da viagem?", "Marque uma data para a reunião."),
    ),
    _Word(
        "caro",
        "palavra",
        "De preço alto; custoso.",
        "Falso amigo: espanhol 'caro' = 'querido' (PT: querido/amado).",
        ("Esse restaurante é muito caro.", "O aluguel aqui ficou mais caro."),
    ),
    _Word(
        "cansativo",
        "palavra",
        "Que causa cansaço; exaustivo.",
        "Não confundir com 'cansado' (estado): 'estou cansado' / 'trabalho cansativo'.",
        ("O dia foi bem cansativo.", "Viagem longa é sempre cansativa."),
    ),
    _Word(
        "fazer falta",
        "colocacao",
        "Ser necessário ou sentido como ausente.",
        "≈ 'echar de menos / hacer falta'. 'Sinto sua falta' também é comum.",
        ("Você vai fazer falta no time.", "O dinheiro fez falta no fim do mês."),
    ),
    _Word(
        "ter razão",
        "colocacao",
        "Estar certo sobre algo.",
        "= 'tener razón'. A forma interrogativa: 'você tem razão?'.",
        ("Você tem razão, eu errei.", "Ele tinha razão sobre o risco."),
    ),
    _Word(
        "trocar uma ideia",
        "expressao",
        "Conversar informalmente; bater um papo.",
        "≈ 'charlar / intercambiar ideas'.",
        ("Bora trocar uma ideia sobre o projeto?", "A gente trocou uma ideia no café."),
    ),
    _Word(
        "pegar no sono",
        "expressao",
        "Conseguir dormir; adormecer.",
        "= 'quedarse dormido'. 'Pegar' tem muitos usos em PT.",
        ("Demorei para pegar no sono ontem.", "Ele pegou no sono no sofá."),
    ),
    _Word(
        "por um triz",
        "expressao",
        "Por muito pouco; quase.",
        "= 'por un pelo'. Muito comum na fala.",
        ("Por um triz não perdi o voo.", "A bola passou por um triz da trave."),
    ),
)


@dataclass(frozen=True, slots=True)
class _Rule:
    title: str
    regra_pt: str
    nota_es: str
    exemplo_ok: str
    exemplo_err: str | None


_RULES: tuple[_Rule, ...] = (
    _Rule(
        "Estar + gerúndio: o contínuo brasileiro",
        "Use 'estar + gerúndio' para ações em andamento: 'estou estudando'. "
        "Para uma mudança de estado, use 'ficar + gerúndio'.",
        "Coincide com 'estar + gerundio' do espanhol; cuidado com o pretérito.",
        "Estava assistindo quando você ligou.",
        "Estou a fazer a lição. (forma europeia; no Brasil: estou fazendo)",
    ),
    _Rule(
        "A gente = nós (verbo na 3ª pessoa)",
        "'A gente' equivale a 'nós', mas o verbo fica na 3ª pessoa do singular: "
        "'a gente vai'. Nunca 'a gente vamos'.",
        "El verbo concuerda en 3ª singular, como 'la gente' en español.",
        "A gente vai ao cinema hoje.",
        "A gente vamos ao cinema hoje.",
    ),
    _Rule(
        "'Faz tempo que…' é impessoal",
        "Para tempo decorrido use 'faz' sem sujeito: 'faz três anos que moro aqui'. "
        "'Eu faço anos' só no sentido de completar aniversário.",
        "El español 'hace tres años' no se traduce como 'faço três anos'.",
        "Faz três anos que trabalho aqui.",
        "Faço três anos que trabalho aqui.",
    ),
    _Rule(
        "'Há' vs 'a' para tempo",
        "Use 'há' para tempo passado ('há muitos anos') e 'a' para distância ou "
        "tempo futuro ('daqui a dois dias').",
        "'Há' viene de 'haver' (haber impersonal).",
        "Há anos que não o vejo; volto daqui a dois dias.",
        "A muitos anos que não o vejo.",
    ),
    _Rule(
        "Subjuntivo após 'espero que', 'quero que'",
        "Depois de 'que' com desejo/dúvida, use o presente do subjuntivo: "
        "'espero que você venha', 'quero que ele entenda'.",
        "El español usa subjuntivo igual; el error es quedarse en indicativo.",
        "Espero que você possa vir à festa.",
        "Espero que você pode vir à festa.",
    ),
    _Rule(
        "Futuro do subjuntivo em frases condicionais",
        "Depois de 'se' e 'quando' com futuro, o português usa o futuro do "
        "subjuntivo: 'se você quiser', 'quando eu puder'.",
        "El español usa presente de subjuntivo ('si quieres'); el PT exige futuro.",
        "Se você quiser, eu te ajudo amanhã.",
        "Se você quiser, eu te ajudo amanhã. → correto; 'se você quer' muda o sentido",
    ),
    _Rule(
        "Por vs para",
        "'Por' indica causa, meio ou passagem ('obrigado por', 'passei por lá'); "
        "'para' indica destino, prazo ou finalidade ('vou para São Paulo').",
        "Coincide bastante con el español, pero revisa 'por causa de'.",
        "Vou para o Rio a trabalho; obrigado por tudo.",
        "Vou por o Rio a trabalho. (use 'para' com destino)",
    ),
    _Rule(
        "Contração de preposição + artigo (no, na, do, da)",
        "Com artigo definido, 'em' contrai: 'no Brasil', 'na escola', 'do amigo'. "
        "Sem artigo: 'em casa', 'em Portugal'.",
        "El español nunca contrae 'en'; en PT es obligatorio con artículo.",
        "Moro no Brasil e trabalho na mesma escola.",
        "Moro em o Brasil. / Estou em a escola.",
    ),
    _Rule(
        "'Estar com' para estados e sensações",
        "Sensações e estados temporários usam 'estar com': 'estou com fome', "
        "'estou com pressa', 'estou com medo'.",
        "El español 'tener hambre' no se traduce con 'ter'.",
        "Estou com fome e com sede.",
        "Tenho fome e tenho sede. (tradução direta do espanhol)",
    ),
    _Rule(
        "Todo vs tudo",
        "'Tudo' = 'todo (ello)' (tudo bem); 'todo' = cada um / inteiro ('todo dia').",
        "El español usa 'todo' para ambos; el PT distingue.",
        "Tudo bem? Eu trabalho todo dia.",
        "Todo bem? Eu trabalho tudo dia.",
    ),
    _Rule(
        "Concordância com 'você'",
        "'Você' pede verbo na 3ª pessoa: 'você quer', 'você é'. Evite formas de "
        "'tu' misturadas na mesma frase.",
        "En España 'tú' es 2ª persona; con 'você' siempre 3ª.",
        "Você quer vir com a gente?",
        "Você queres vir? / Você é legal, tu sabes.",
    ),
    _Rule(
        "Lembrar-se de / esquecer-se de",
        "Os verbos pronominais pedem a preposição 'de': 'eu me lembro de você', "
        "'esqueci-me do nome' (ou 'esqueci o nome').",
        "Como 'acordarse de' en español: la preposición no se omite.",
        "Eu me lembro de você da faculdade.",
        "Eu me lembro você da faculdade.",
    ),
)


@dataclass(frozen=True, slots=True)
class _Pair:
    a: str
    b: str
    nota_es: str


_PAIRS: tuple[_Pair, ...] = (
    _Pair("avó", "avô", "Vogal aberta /ɔ/ (avó, mãe do pai) vs fechada /o/ (avô)."),
    _Pair("pão", "pau", "Nasal /ɐ̃w/ (pão) vs oral /aw/ (pau): deixe o ar sair pelo nariz."),
    _Pair("mão", "mau", "Nasal /ɐ̃w/ (mão, mãozinha) vs ditongo oral /aw/ (mau, bom/mau)."),
    _Pair(
        "sim",
        "sem",
        "Nasais finais: /sĩ/ vs /sẽ/ — a vogal nasal nunca fecha igual ao espanhol.",
    ),
    _Pair("tia", "dia", "Antes de /i/, o T vira ≈'tch' e o D ≈'dj' (padrão brasileiro)."),
    _Pair("ela", "ilha", "L simples (ela) vs LH palatal (ilha) — o LH é um único som."),
    _Pair("carro", "caro", "RR forte ≈ /x/~/h/ (carro) vs R simples /ɾ/ (caro)."),
    _Pair("sol", "só", "L no fim de sílaba vira /w/ (sol ≈ 'sou'); compare com o 'sol' espanhol."),
    _Pair("cheio", "seio", "CH = /ʃ/ (cheio) vs S = /s/ (seio)."),
    _Pair("leite", "leiti", "E átono final reduz para /i/ (leite ≈ 'leiti', dente ≈ 'denti')."),
    _Pair("novo", "novu", "O átono final reduz para /u/ (novo ≈ 'novu', todo ≈ 'todu')."),
    _Pair("peixe", "peito", "X ≈ /ʃ/ (peixe) vs T oclusivo (peito) — não pronuncie o X como /ks/."),
)


@dataclass(frozen=True, slots=True)
class _Pitfall:
    issue: str
    tip_pt: str
    nota_es: str


_PITFALLS: tuple[_Pitfall, ...] = (
    _Pitfall(
        "Vogais nasais",
        "Em mãe, pão, sim, o ar sai pela boca E pelo nariz ao mesmo tempo.",
        "El español no tiene vocales nasales: entrena mãe, mão, sim.",
    ),
    _Pitfall(
        "Mas vs mais",
        "'Mas' = però; 'mais' = más. Pronuncia: /mas/ vs /majs/.",
        "No se confundan: 'mais' suena como 'máis' gallego.",
    ),
    _Pitfall(
        "R final fraco ou mudo",
        "Em falar, comer, o R final é fraco ou quase mudo em muitas regiões.",
        "No arrastres la 'r' final como en español.",
    ),
    _Pitfall(
        "S entre vogais = /z/",
        "casa, mesa, usar: o S soa como /z/.",
        "En español la 's' es siempre /s/; en PT cambia entre vocales.",
    ),
    _Pitfall(
        "Palatalização de T e D",
        "Antes de i/e, tia ≈ 'tchia', dia ≈ 'djia' (padrão do Sudeste).",
        "Es el 'yeísmo' al revés: consonante + yod.",
    ),
    _Pitfall(
        "X tem várias pronúncias",
        "peixe = /ʃ/, táxi = /ks/, exame = /z/, xícara = /ʃ/.",
        "No hay regla única: memoriza as palavras.",
    ),
    _Pitfall(
        "LH e NH",
        "milhão, banho: um único som palatal; não vire em 'li'/'ni'.",
        "Se pronuncian como 'll'/'ñ', no como l+i o n+i.",
    ),
    _Pitfall(
        "RR forte",
        "Rio, carro: R inicial ou RR ≈ /x/ ou /h/ suave.",
        "No uses la vibrante múltiple del español; es más fricativa.",
    ),
    _Pitfall(
        "E e O átonos finais",
        "leite ≈ 'leiti', novo ≈ 'novu': o E final vira /i/ e o O vira /u/.",
        "El español mantiene /e/ y /o/; el PT los cierra.",
    ),
    _Pitfall(
        "Ditongos nasais",
        "não, pão, mãe: o 'ão' é nasal e fechado; não diga 'nau'.",
        "Practica el cierre nasal de 'ão' (≈ 'nau' nasal).",
    ),
)


@dataclass(frozen=True, slots=True)
class _Sentence:
    frase: str
    nota_es: str
    dica: str


_SENTENCES: tuple[_Sentence, ...] = (
    _Sentence(
        "A gente se vê amanhã cedo, combinado?",
        "'A gente' = nosotros; verbo en 3ª persona.",
        "Nasalize o 'ã' de amanhã.",
    ),
    _Sentence(
        "Por um triz eu não perdi o voo de manhã.",
        "'Por um triz' = 'por un pelo'.",
        "Treine o 'não' nasal e o 'voo' com O fechado.",
    ),
    _Sentence(
        "Espero que você consiga chegar a tempo.",
        "Subjuntivo após 'espero que'.",
        "O 'que' + subjuntivo: consiga, chegue.",
    ),
    _Sentence(
        "Se você quiser, a gente marca outro dia.",
        "Futuro do subjuntivo: 'quiser'.",
        "Note 'você' + 3ª pessoa: quiser, marca.",
    ),
    _Sentence(
        "Estou com uma saudade enorme da minha terra.",
        "'Estar com saudade de' ≈ tener morriña.",
        "Nasal: saudade, enorme, terra.",
    ),
    _Sentence(
        "Faz tempo que eu não como uma feijoada caprichada.",
        "'Faz tempo que' = 'hace tiempo que'.",
        "Nasalize o 'não' e o 'ão' de feijoada.",
    ),
    _Sentence(
        "Pelo visto a reunião foi adiada para sexta.",
        "'Pelo visto' = 'por lo visto'.",
        "O 'ão' de reunião? (não há); foque no 'foi' e em 'adiada'.",
    ),
    _Sentence(
        "Você tem razão: a ideia deu certo mesmo.",
        "'Ter razão' = 'tener razón'; 'dar certo' = 'salir bien'.",
        "O R de razão é forte no início.",
    ),
    _Sentence(
        "Sem querer, deixei o celular em casa.",
        "'Sem querer' = 'sin querer'.",
        "O L de celular vira /w/ (celu'lar' ≈ celu'law').",
    ),
    _Sentence(
        "De repente ele não vem, e a gente fica sem plano.",
        "BR: 'de repente' costuma significar 'talvez'.",
        "Treine 'gente' com G suave + E fechado.",
    ),
    _Sentence(
        "O que mais me encanta no Brasil é a simpatia do povo.",
        "'O que mais me encanta' = 'lo que más me encanta'.",
        "O 'ão' de encanta? não; foque no 'povo' (O → /u/ final).",
    ),
    _Sentence(
        "Vou ficar de olho no prazo para não perder a data.",
        "'Ficar de olho em' = 'estar atento a'.",
        "O 'lh' de olho é um som só; 'prazo' com R simples.",
    ),
    _Sentence(
        "Tanto faz o lugar, contanto que a gente esteja junto.",
        "'Tanto faz' = 'me da igual'; 'contanto que' = 'siempre y cuando'.",
        "O 's' de faz no fim é /s/; 'junto' com O final /u/.",
    ),
    _Sentence(
        "Estava assistindo quando você ligou, por isso demorei.",
        "Estar + gerúndio para ação contínua.",
        "O 's' de assistindo é /s/ ou /z/? 'assistindo': s entre vogais → /z/.",
    ),
)


_PT_RANDOM_WINDOW = 5
_word_history: deque[_Word] = deque(maxlen=_PT_RANDOM_WINDOW)

WORD_COUNT: int = len(_WORDS)
RULE_COUNT: int = len(_RULES)
PAIR_COUNT: int = len(_PAIRS)
PITFALL_COUNT: int = len(_PITFALLS)
SENTENCE_COUNT: int = len(_SENTENCES)


def _to_word_of_day(day: date, word: _Word) -> PtWordOfDay:
    return PtWordOfDay(
        date=day,
        expression=word.expression,
        category=word.category,
        definition_pt=word.definition_pt,
        nota_es=word.nota_es,
        examples=list(word.examples),
    )


def word_for_date(day: date) -> PtWordOfDay:
    """Stable daily selection from the curated pool."""
    return _to_word_of_day(day, _WORDS[day.toordinal() % len(_WORDS)])


def random_word() -> PtWordOfDay:
    """Random curated entry that avoids recently served items (manual refresh)."""
    recent = {word.expression for word in _word_history}
    candidates = [word for word in _WORDS if word.expression not in recent]
    if not candidates:
        candidates = list(_WORDS)
    word = random.choice(candidates)
    _word_history.append(word)
    return _to_word_of_day(date.today(), word)


def rule_for_date(day: date) -> PtGrammarRule:
    """Stable daily grammar rule."""
    rule = _RULES[day.toordinal() % len(_RULES)]
    return _to_rule(rule)


def all_rules() -> list[PtGrammarRule]:
    return [_to_rule(rule) for rule in _RULES]


def random_rule(exclude_title: str | None = None) -> PtGrammarRule:
    """A random rule different from ``exclude_title`` (for 'Outra regra')."""
    pool = [rule for rule in _RULES if rule.title != exclude_title] or list(_RULES)
    return _to_rule(random.choice(pool))


def _to_rule(rule: _Rule) -> PtGrammarRule:
    return PtGrammarRule(
        title=rule.title,
        regra_pt=rule.regra_pt,
        nota_es=rule.nota_es,
        exemplo_ok=rule.exemplo_ok,
        exemplo_err=rule.exemplo_err,
    )


MINIMAL_PAIRS_PT: tuple[PtMinimalPair, ...] = tuple(
    PtMinimalPair(a=pair.a, b=pair.b, nota_es=pair.nota_es) for pair in _PAIRS
)

PITFALLS_PT: tuple[PtPitfall, ...] = tuple(
    PtPitfall(issue=p.issue, tip_pt=p.tip_pt, nota_es=p.nota_es) for p in _PITFALLS
)

FALLBACK_SENTENCES: tuple[PtSentence, ...] = tuple(
    PtSentence(frase=s.frase, nota_es=s.nota_es, dica=s.dica) for s in _SENTENCES
)
