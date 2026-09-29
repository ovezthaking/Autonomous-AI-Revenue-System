from revenue_swarm.llm import structured

from research_agent.models import ProgramFacts, SearchHit

EXTRACT_PROMPT = (
    "Extract affiliate program terms from the page text below. "
    "Use null for anything the page does not state explicitly. "
    "Never guess numbers. Set confidence below 0.3 if the page does not "
    "clearly describe an affiliate or partner program.\n\n"
    "PAGE TEXT:\n{text}"
)

MAX_CHARS = 12_000


def extract_facts(hit: SearchHit, text: str) -> ProgramFacts | None:
    prompt = EXTRACT_PROMPT.format(text=text[:MAX_CHARS])
    return structured(prompt, ProgramFacts)
