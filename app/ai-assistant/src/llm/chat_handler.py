"""Chat handler for STAR and Pitch coaching conversations."""

import json
import logging
import re
from pathlib import Path

from ..schemas import CoachingType, UserContext
from .providers import LLMConfig, get_llm_provider

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def load_system_prompt(coaching_type: CoachingType = CoachingType.STAR) -> str:
    """Load the system prompt template for the given coaching type."""
    if coaching_type == CoachingType.PITCH:
        prompt_file = PROMPTS_DIR / "pitch_coaching.txt"
    else:
        prompt_file = PROMPTS_DIR / "star_coaching.txt"
    return prompt_file.read_text(encoding="utf-8")


def format_experiences(experiences: list[dict]) -> str:
    """Format experiences list for the prompt."""
    if not experiences:
        return "  (aucune expérience renseignée)"

    lines = []
    for exp in experiences[:5]:  # Limit to 5 most recent
        entity = exp.get("entity", "")
        position = exp.get("position", "")
        dates = exp.get("dates", "")
        description = exp.get("description", "")
        if entity or position:
            line = f"  - {position} chez {entity} ({dates})"
            if description:
                line += f"\n    {description[:200]}..."
            lines.append(line)
    return "\n".join(lines) if lines else "  (aucune expérience renseignée)"


def format_education(education: list[dict]) -> str:
    """Format education list for the prompt."""
    if not education:
        return "  (aucune formation renseignée)"

    lines = []
    for edu in education[:3]:
        entity = edu.get("entity", "")
        degree = edu.get("degree", "")
        dates = edu.get("dates", "")
        if entity or degree:
            lines.append(f"  - {degree} - {entity} ({dates})")
    return "\n".join(lines) if lines else "  (aucune formation renseignée)"


def format_skills(skills: list[str]) -> str:
    """Format skills list for the prompt."""
    if not skills:
        return "  (aucune compétence renseignée)"
    return ", ".join(skills[:10])


def format_interests(interests: list[str]) -> str:
    """Format interests list for the prompt."""
    if not interests:
        return "  (aucun centre d'intérêt renseigné)"
    return "\n".join([f"  - {interest}" for interest in interests[:5]])


def format_existing_successes(successes: list[dict], detailed: bool = False) -> str:
    """Format existing successes for the prompt.

    Args:
        successes: List of success dictionaries.
        detailed: If True, include full STAR data (for pitch coaching).
    """
    if not successes:
        return "  (aucun succès encore formalisé)"

    lines = []
    for success in successes[:5]:
        title = success.get("title", "Sans titre")

        if detailed and any(success.get(k) for k in ["situation", "task", "action", "result"]):
            # Full STAR format for pitch coaching
            lines.append(f"\n  **{title}**")
            if success.get("situation"):
                lines.append(f"    - Situation : {success['situation'][:300]}")
            if success.get("task"):
                lines.append(f"    - Tâche : {success['task'][:200]}")
            if success.get("action"):
                lines.append(f"    - Action : {success['action'][:400]}")
            if success.get("result"):
                lines.append(f"    - Résultat : {success['result'][:300]}")
            if success.get("skills_demonstrated"):
                skills = ", ".join(success["skills_demonstrated"][:5])
                lines.append(f"    - Compétences : {skills}")
        else:
            # Simple title only for STAR coaching
            lines.append(f"  - {title}")

    return "\n".join(lines)


def build_system_prompt(
    user_context: UserContext,
    coaching_type: CoachingType = CoachingType.STAR,
) -> str:
    """Build the complete system prompt with user context."""
    template = load_system_prompt(coaching_type)

    # Common fields
    format_args = {
        "first_name": user_context.first_name or "le candidat",
        "last_name": user_context.last_name or "",
        "location": user_context.location or "(non renseignée)",
        "profile_title": user_context.profile_title or "(aucun profil sélectionné)",
        "experiences": format_experiences(user_context.experiences),
        "interests": format_interests(user_context.interests),
        "autonomy_level": user_context.autonomy_level,
    }

    # Common fields for both coaching types
    format_args["education"] = format_education(user_context.education)
    format_args["skills"] = format_skills(user_context.skills)

    # Both coaching types get detailed successes to avoid duplicates and build on existing work
    format_args["professional_successes"] = format_existing_successes(user_context.existing_successes, detailed=True)

    return template.format(**format_args)


async def get_initial_message_async(
    user_context: UserContext,
    coaching_type: CoachingType = CoachingType.STAR,
    llm_config: LLMConfig | None = None,
) -> str:
    """Generate the initial greeting message using LLM.

    This creates a proactive first message that proposes concrete suggestions
    based on the user's profile data.
    """
    provider = get_llm_provider(llm_config)
    system_prompt = build_system_prompt(user_context, coaching_type)

    # Create a trigger message to get the LLM to generate the opening
    if coaching_type == CoachingType.PITCH:
        trigger = (
            "L'utilisateur vient d'ouvrir la section Pitch. "
            "Génère ton message d'accueil proactif en proposant directement "
            "une première version des pitchs 30s et 3min basée sur son profil et ses succès STAR. "
            "Sois concret et propose du contenu, pas juste des questions."
        )
    else:
        trigger = (
            "L'utilisateur vient d'ouvrir la section Succès professionnels. "
            "Génère ton message d'accueil proactif en proposant des pistes concrètes "
            "basées sur ses expériences. Liste 2-3 expériences qui pourraient donner "
            "de bons succès STAR et demande laquelle il veut travailler."
        )

    try:
        response = provider.chat(
            [{"role": "user", "content": trigger}],
            system_prompt,
        )
        logger.info(f"Generated initial {coaching_type.value} message: {response[:100]}...")
        return response
    except Exception as e:
        logger.error(f"Failed to generate initial message: {e}")
        # Fallback to static message
        return get_initial_message_fallback(user_context, coaching_type)


def get_initial_message(
    user_context: UserContext,
    coaching_type: CoachingType = CoachingType.STAR,
) -> str:
    """Synchronous wrapper - returns fallback message.

    For async LLM generation, use get_initial_message_async instead.
    """
    return get_initial_message_fallback(user_context, coaching_type)


def get_initial_message_fallback(
    user_context: UserContext,
    coaching_type: CoachingType = CoachingType.STAR,
) -> str:
    """Generate a static fallback greeting message."""
    first_name = user_context.first_name or "vous"

    if coaching_type == CoachingType.PITCH:
        successes = user_context.existing_successes
        if successes:
            return (
                f"Bonjour {first_name} ! Je vais t'aider à créer des pitchs percutants "
                f"(30 secondes et 3 minutes). J'ai vu que tu as déjà formalisé {len(successes)} "
                f"succès professionnel(s), c'est une excellente base pour construire un pitch impactant !\n\n"
                f"Pour commencer, dis-moi : dans quel contexte vas-tu utiliser ce pitch ? "
                f"(entretien, salon, événement networking, candidature spontanée...)"
            )
        else:
            return (
                f"Bonjour {first_name} ! Je vais t'aider à créer des pitchs percutants "
                f"(30 secondes et 3 minutes).\n\n"
                f"Pour commencer, dis-moi : dans quel contexte vas-tu utiliser ce pitch ? "
                f"(entretien, salon, événement networking, candidature spontanée...)"
            )
    else:
        if user_context.experiences:
            return (
                f"Bonjour {first_name} ! Je suis là pour t'aider à formaliser un de tes succès "
                f"professionnels avec la méthode STAR. J'ai vu que tu as travaillé notamment "
                f"comme {user_context.experiences[0].get('position', 'professionnel')}. "
                f"Peux-tu me parler d'une réalisation dont tu es particulièrement fier(ère) ?"
            )
        else:
            return (
                f"Bonjour {first_name} ! Je suis là pour t'aider à formaliser un de tes succès "
                f"professionnels avec la méthode STAR. Peux-tu me parler d'une réalisation "
                f"professionnelle dont tu es particulièrement fier(ère) ?"
            )


async def process_chat_message(
    message: str,
    history: list[dict],
    user_context: UserContext,
    coaching_type: CoachingType = CoachingType.STAR,
    llm_config: LLMConfig | None = None,
) -> str:
    """Process a chat message and return the assistant's response.

    Args:
        message: The user's message.
        history: Previous messages in the conversation.
        user_context: User context for personalization.
        coaching_type: Type of coaching (STAR or PITCH).
        llm_config: Optional custom LLM configuration.

    Returns:
        The assistant's response text.
    """
    provider = get_llm_provider(llm_config)
    system_prompt = build_system_prompt(user_context, coaching_type)

    # Build messages list
    messages = []
    for msg in history:
        messages.append(
            {
                "role": msg.get("role", "user"),
                "content": msg.get("content", ""),
            }
        )

    # Add the new user message
    messages.append({"role": "user", "content": message})

    logger.info(f"Processing {coaching_type.value} chat with {len(messages)} messages")

    try:
        response = provider.chat(messages, system_prompt)
        logger.info(f"Got response: {response[:100]}...")
        return response
    except Exception as e:
        logger.error(f"Chat processing failed: {e}")
        raise


def stream_initial_message(
    user_context: UserContext,
    coaching_type: CoachingType = CoachingType.STAR,
    llm_config: LLMConfig | None = None,
):
    """Stream the initial greeting message token by token.

    Yields:
        Response text chunks as they are generated.
    """
    provider = get_llm_provider(llm_config)
    system_prompt = build_system_prompt(user_context, coaching_type)

    # Create a trigger message to get the LLM to generate the opening
    if coaching_type == CoachingType.PITCH:
        trigger = (
            "L'utilisateur vient d'ouvrir la section Pitch. "
            "Génère ton message d'accueil proactif en proposant directement "
            "une première version des pitchs 30s et 3min basée sur son profil et ses succès STAR. "
            "Sois concret et propose du contenu, pas juste des questions."
        )
    else:
        trigger = (
            "L'utilisateur vient d'ouvrir la section Succès professionnels. "
            "Génère ton message d'accueil proactif en proposant des pistes concrètes "
            "basées sur ses expériences. Liste 2-3 expériences qui pourraient donner "
            "de bons succès STAR et demande laquelle il veut travailler."
        )

    logger.info(f"Starting {coaching_type.value} initial message stream")

    try:
        for chunk in provider.chat_stream(  # noqa: UP028 - yield from incompatible with try/except fallback
            [{"role": "user", "content": trigger}],
            system_prompt,
        ):
            yield chunk
    except Exception as e:
        logger.error("Failed to stream initial message: %s", e)
        # Yield fallback message
        yield get_initial_message_fallback(user_context, coaching_type)


def stream_chat_message(
    message: str,
    history: list[dict],
    user_context: UserContext,
    coaching_type: CoachingType = CoachingType.STAR,
    llm_config: LLMConfig | None = None,
):
    """Stream a chat response token by token.

    Args:
        message: The user's message.
        history: Previous messages in the conversation.
        user_context: User context for personalization.
        coaching_type: Type of coaching (STAR or PITCH).
        llm_config: Optional custom LLM configuration.

    Yields:
        Response text chunks as they are generated.
    """
    provider = get_llm_provider(llm_config)
    system_prompt = build_system_prompt(user_context, coaching_type)

    # Build messages list
    messages = []
    for msg in history:
        messages.append(
            {
                "role": msg.get("role", "user"),
                "content": msg.get("content", ""),
            }
        )

    # Add the new user message
    messages.append({"role": "user", "content": message})

    logger.info(f"Starting {coaching_type.value} chat stream with {len(messages)} messages")

    try:
        for chunk in provider.chat_stream(messages, system_prompt):  # noqa: UP028 - yield from incompatible with try/except
            yield chunk
    except Exception as e:
        logger.error("Chat stream failed: %s", e)
        raise


def _parse_json_response(response: str) -> dict:
    """Parse JSON from LLM response, handling markdown code blocks."""
    json_text = response.strip()
    if json_text.startswith("```"):
        match = re.search(r"```(?:json)?\s*([\s\S]*?)```", json_text)
        if match:
            json_text = match.group(1).strip()
    return json.loads(json_text)


# Prompt for extracting STAR data from conversation
STAR_EXTRACTION_PROMPT = """Analyse la conversation ci-dessous et extrais les éléments STAR (Situation, Tâche, Action, Résultat) mentionnés par le candidat.

Retourne un JSON avec cette structure exacte :
{
  "title": "Titre court et accrocheur (avec chiffre clé si possible)",
  "situation": "Le contexte décrit par le candidat",
  "task": "La mission/tâche personnelle du candidat",
  "action": "Les actions concrètes menées (au 'je')",
  "result": "Les résultats obtenus (quantifiés si possible)",
  "skills_demonstrated": ["compétence1", "compétence2"],
  "is_complete": true/false
}

Règles :
- Utilise UNIQUEMENT les informations fournies par le candidat
- Si une composante n'a pas été mentionnée, laisse une chaîne vide ""
- is_complete = true seulement si les 4 composantes STAR ont du contenu substantiel
- Le titre doit être accrocheur et refléter le résultat principal

Conversation à analyser :
"""


async def extract_star_data(
    messages: list[dict],
    llm_config: LLMConfig | None = None,
) -> dict:
    """Extract STAR data from a conversation.

    Args:
        messages: The conversation messages.
        llm_config: Optional custom LLM configuration.

    Returns:
        Dictionary with extracted STAR components.
    """
    provider = get_llm_provider(llm_config)

    # Format conversation for analysis
    conversation_text = ""
    for msg in messages:
        role = "Candidat" if msg.get("role") == "user" else "Assistant"
        conversation_text += f"\n{role}: {msg.get('content', '')}"

    user_prompt = STAR_EXTRACTION_PROMPT + conversation_text

    system_prompt = "Tu es un expert en analyse de conversations. Tu extrais les informations structurées en JSON valide uniquement."

    try:
        response = provider.chat([{"role": "user", "content": user_prompt}], system_prompt)
        data = _parse_json_response(response)

        return {
            "title": data.get("title", ""),
            "situation": data.get("situation", ""),
            "task": data.get("task", ""),
            "action": data.get("action", ""),
            "result": data.get("result", ""),
            "skills_demonstrated": data.get("skills_demonstrated", []),
            "is_complete": data.get("is_complete", False),
        }

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse STAR extraction: {e}")
        return {
            "title": "",
            "situation": "",
            "task": "",
            "action": "",
            "result": "",
            "skills_demonstrated": [],
            "is_complete": False,
        }
    except Exception as e:
        logger.error(f"STAR extraction failed: {e}")
        raise


# Prompt for extracting pitch from conversation
PITCH_EXTRACTION_PROMPT = """Analyse la conversation ci-dessous et extrais les pitchs créés avec le candidat.

Retourne un JSON avec cette structure exacte :
{
  "pitch_30s": "Le pitch de 30 secondes complet (environ 75-80 mots)",
  "pitch_3min": "Le pitch de 3 minutes complet (environ 400-450 mots)",
  "key_strengths": ["force1", "force2", "force3"],
  "is_complete": true/false
}

Règles :
- Utilise UNIQUEMENT les informations présentes dans la conversation
- Si un pitch n'a pas été complètement formulé, reconstitue-le à partir des éléments discutés
- is_complete = true seulement si les deux pitchs sont substantiels
- Les key_strengths sont les 3-5 points forts principaux mis en avant dans les pitchs

Conversation à analyser :
"""


async def extract_pitch_data(
    messages: list[dict],
    llm_config: LLMConfig | None = None,
) -> dict:
    """Extract pitch data from a conversation.

    Args:
        messages: The conversation messages.
        llm_config: Optional custom LLM configuration.

    Returns:
        Dictionary with extracted pitch components.
    """
    provider = get_llm_provider(llm_config)

    # Format conversation for analysis
    conversation_text = ""
    for msg in messages:
        role = "Candidat" if msg.get("role") == "user" else "Assistant"
        conversation_text += f"\n{role}: {msg.get('content', '')}"

    user_prompt = PITCH_EXTRACTION_PROMPT + conversation_text

    system_prompt = "Tu es un expert en analyse de conversations. Tu extrais les informations structurées en JSON valide uniquement."

    try:
        response = provider.chat([{"role": "user", "content": user_prompt}], system_prompt)
        data = _parse_json_response(response)

        return {
            "pitch_30s": data.get("pitch_30s", ""),
            "pitch_3min": data.get("pitch_3min", ""),
            "key_strengths": data.get("key_strengths", []),
            "is_complete": data.get("is_complete", False),
        }

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse pitch extraction: {e}")
        return {
            "pitch_30s": "",
            "pitch_3min": "",
            "key_strengths": [],
            "is_complete": False,
        }
    except Exception as e:
        logger.error(f"Pitch extraction failed: {e}")
        raise
