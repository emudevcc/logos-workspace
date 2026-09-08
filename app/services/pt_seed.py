"""Idempotent seeding of the Português cockpit SRS decks (cockpit='pt').

Two starter decks target a native Spanish speaker at intermediate/advanced
PT-BR: essential vocabulary and ES→PT false cognates. Every card carries a
``l1_hint`` with a short Spanish scaffolding note.
"""

from __future__ import annotations

import json

from app.core.db import Database
from app.core.timeutil import iso_utc, utc_now

PT_VOCAB_DECK_SLUG = "pt-vocabulario"
PT_VOCAB_DECK_NAME = "Vocabulário essencial PT-BR"
PT_VOCAB_DECK_DESCRIPTION = (
    "Palavras e usos frequentes com dica em espanhol (transferência direta)."
)

PT_COGNATES_DECK_SLUG = "pt-falsos-cognatos"
PT_COGNATES_DECK_NAME = "Falsos cognatos ES → PT"
PT_COGNATES_DECK_DESCRIPTION = (
    "Palavras parecidas com o espanhol, mas com significado diferente."
)

# (front, back, l1_hint, register_tag)
PT_VOCAB_CARDS: tuple[tuple[str, str, str, str], ...] = (
    (
        "pesquisar",
        "Buscar informações (na internet, num estudo).",
        "'pesquisar' = buscar información; não é 'investigar' policial.",
        "Vocabulário",
    ),
    (
        "procurar",
        "Buscar algo perdido; procurar emprego.",
        "='buscar'; nunca 'procurar por' com sentido de buscar.",
        "Vocabulário",
    ),
    (
        "perceber",
        "Dar-se conta; notar.",
        "'perceber' = darse cuenta; 'realizar' = llevar a cabo.",
        "Vocabulário",
    ),
    (
        "costumar",
        "Ter por hábito; soler.",
        "'costumo acordar cedo' = 'suelo levantarme temprano'.",
        "Vocabulário",
    ),
    (
        "acostumar",
        "Acostumbrar(se).",
        "'acostumar-se com' exige a preposição 'com'.",
        "Vocabulário",
    ),
    (
        "aposentar",
        "Jubilar(se).",
        "'aposentar-se' = 'jubilarse' (ES).",
        "Vocabulário",
    ),
    (
        "brincar",
        "Jugar (crianças); bromear.",
        "'brincar' = jugar/bromear; esportes usam 'jogar'.",
        "Vocabulário",
    ),
    (
        "jogar",
        "Jugar (esporte, jogo).",
        "'jogar' = jugar; 'jogar fora' = tirar.",
        "Vocabulário",
    ),
    (
        "andar",
        "Caminhar; andar de.",
        "'andar' = caminar; progressivo: 'estou andando'.",
        "Vocabulário",
    ),
    (
        "demorar",
        "Tardar; levar tempo.",
        "'quanto demora?' = '¿cuánto tarda?'.",
        "Vocabulário",
    ),
    (
        "atrasar",
        "Atrasar; chegar tarde.",
        "'estou atrasado' = 'voy tarde'.",
        "Vocabulário",
    ),
    (
        "adiantar",
        "Adelantar; ser útil.",
        "'não adianta' = 'no vale la pena / no sirve'.",
        "Vocabulário",
    ),
    (
        "cuidar",
        "Cuidar; ter cuidado.",
        "'cuidar de' pede 'de'; 'cuidado!' = '¡ojo!'.",
        "Vocabulário",
    ),
    (
        "estranhar",
        "Extrañarse; achar estranho.",
        "'estranhar' ≠ 'extrañar' (= sentir saudade).",
        "Vocabulário",
    ),
    (
        "emprestar",
        "Prestar (dar emprestado).",
        "'pegar emprestado' = 'pedir prestado'.",
        "Vocabulário",
    ),
    (
        "tomar",
        "Tomar (bebida, decisão, transporte).",
        "'tomar banho' = 'ducharse'.",
        "Vocabulário",
    ),
    (
        "conseguir",
        "Lograr; poder.",
        "'não consigo' = 'no logro / no puedo'.",
        "Vocabulário",
    ),
    (
        "achar",
        "Encontrar; opinar.",
        "'acho que sim' = 'creo que sí'.",
        "Vocabulário",
    ),
)

# (front, back, l1_hint, register_tag)
PT_COGNATE_CARDS: tuple[tuple[str, str, str, str], ...] = (
    (
        "embaraçada",
        "Envergonhada, sem graça.",
        "Parece 'embarazada' (grávida) — mas não é!",
        "Falso cognato",
    ),
    (
        "grávida",
        "Que espera um bebê.",
        "'embarazada' em espanhol; 'embaraçada' é outra palavra.",
        "Falso cognato",
    ),
    (
        "esquisito",
        "Estranho, raro.",
        "Não é 'exquisito' (requintado, delicioso).",
        "Falso cognato",
    ),
    (
        "largo",
        "Largo (de largura).",
        "ES 'largo' = comprido (PT); PT 'largo' = ancho.",
        "Falso cognato",
    ),
    (
        "comprido",
        "Longo, extenso.",
        "ES 'largo' = comprido; não confundir com 'comprado'.",
        "Falso cognato",
    ),
    (
        "data",
        "Fecha do calendário; dia marcado.",
        "ES 'dato' = PT 'dado'.",
        "Falso cognato",
    ),
    (
        "firma",
        "Assinatura; (coloquial) empresa.",
        "ES 'firma' = empresa (PT: empresa/companhia).",
        "Falso cognato",
    ),
    (
        "nota",
        "Nota escolar; cédula de dinheiro.",
        "PT 'nota de 20' = 'billete de 20' (ES).",
        "Falso cognato",
    ),
    (
        "bolsa",
        "Bolsa (acessório), de estudos, de valores.",
        "ES 'bolso' = bolsillo (PT: bolso).",
        "Falso cognato",
    ),
    (
        "cara",
        "Rosto; pessoa ('cara legal').",
        "'cara' ≠ 'caro' (querido em ES).",
        "Falso cognato",
    ),
    (
        "caro",
        "De preço alto.",
        "ES 'caro' = querido → PT 'querido/amado'.",
        "Falso cognato",
    ),
    (
        "prédio",
        "Edifício.",
        "ES 'predio' = terreno/propriedade (PT: terreno).",
        "Falso cognato",
    ),
    (
        "tirar",
        "Sacar; remover; tirar foto.",
        "ES 'tirar' = lanzar → PT 'jogar/arremessar'.",
        "Falso cognato",
    ),
    (
        "ligar",
        "Ligar (telefone, conexão); importar.",
        "'me liga' = 'llámame'; 'não ligo' = 'no me importa'.",
        "Falso cognato",
    ),
    (
        "perguntar",
        "Preguntar.",
        "Não confundir com 'pedir' (solicitar).",
        "Falso cognato",
    ),
    (
        "saco",
        "Saco, bolsa grande.",
        "PT 'sacola' = bolsa de compras; cuidado com usos grosseiros.",
        "Falso cognato",
    ),
    (
        "fechar",
        "Cerrar.",
        "'fecha' (data em ES) = PT 'data'.",
        "Falso cognato",
    ),
    (
        "atender",
        "Atender telefone/cliente; responder.",
        "ES 'atender' (prestar atenção) = PT 'prestar atenção'.",
        "Falso cognato",
    ),
)


async def seed_pt_decks(db: Database) -> None:
    """Insert the Português decks and cards once; a no-op if they already exist."""
    await _seed_deck(
        db,
        slug=PT_VOCAB_DECK_SLUG,
        name=PT_VOCAB_DECK_NAME,
        description=PT_VOCAB_DECK_DESCRIPTION,
        cards=PT_VOCAB_CARDS,
    )
    await _seed_deck(
        db,
        slug=PT_COGNATES_DECK_SLUG,
        name=PT_COGNATES_DECK_NAME,
        description=PT_COGNATES_DECK_DESCRIPTION,
        cards=PT_COGNATE_CARDS,
    )


async def _seed_deck(
    db: Database,
    *,
    slug: str,
    name: str,
    description: str,
    cards: tuple[tuple[str, str, str, str], ...],
) -> None:
    cursor = await db.connection.execute("SELECT id FROM decks WHERE slug = ?", (slug,))
    if await cursor.fetchone() is not None:
        return

    due_at = iso_utc(utc_now())
    async with db.transaction() as conn:
        cursor = await conn.execute(
            "INSERT INTO decks (slug, name, description, cockpit) VALUES (?, ?, ?, 'pt')",
            (slug, name, description),
        )
        deck_id = cursor.lastrowid
        for front, back, l1_hint, register_tag in cards:
            await conn.execute(
                "INSERT INTO cards "
                "(deck_id, front, back, l1_hint, register_tag, examples, due_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (deck_id, front, back, l1_hint, register_tag, json.dumps([]), due_at),
            )
