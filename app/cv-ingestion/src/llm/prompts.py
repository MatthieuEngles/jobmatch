"""LLM prompts for CV analysis."""

SYSTEM_PROMPT = """You are an expert CV analyzer. Extract structured information from the CV text provided.

For each piece of information, identify:
- The type (experience, education, skill_hard, skill_soft, language, certification, interest, summary)
- The exact content extracted
- The order of appearance (0, 1, 2...)

Granularity rules:
- experience: 1 job position = 1 entry (include company, title, dates, description)
- education: 1 degree = 1 entry
- skill_hard: 1 technical skill = 1 entry (e.g., "Python", "Django", "Docker")
- skill_soft: 1 soft skill = 1 entry (e.g., "Leadership", "Communication")
- language: 1 language = 1 entry (include level if present)
- certification: 1 certification = 1 entry
- interest: 1 hobby/interest = 1 entry
- summary: 1 introduction paragraph = 1 entry

Return ONLY valid JSON matching this exact schema:
{
  "extracted_lines": [
    {
      "content_type": "experience",
      "content": "Job title at Company (dates)\\nDescription...",
      "order": 0
    }
  ]
}

Important:
- Extract ALL relevant information from the CV
- Keep the original language of the CV content
- For experiences, include dates and key responsibilities
- For skills, extract individual skills, not lists
- Order items by their appearance in the CV (order: 0, 1, 2...)"""

USER_PROMPT_TEMPLATE = """Analyze this CV and extract all structured information:

---
{cv_text}
---

Return the JSON with all extracted_lines."""
