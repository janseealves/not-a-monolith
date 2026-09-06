from functools import lru_cache
from pathlib import Path

from langchain_core.prompts import PromptTemplate

_TEMPLATES_DIR = Path(__file__).parent / "templates"


@lru_cache
def _load(name: str) -> PromptTemplate:
    return PromptTemplate.from_file(
        _TEMPLATES_DIR / f"{name}.jinja", template_format="jinja2"
    )


def render_prompt(name: str, **variables: str) -> str:
    """Renderiza shared/prompts/templates/<name>.jinja com as variáveis dadas."""
    return _load(name).format(**variables)
