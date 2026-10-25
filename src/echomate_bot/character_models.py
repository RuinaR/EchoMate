"""Versioned pretrained-character catalog. Metadata is not execution approval.

No model download, license acceptance, operating-settings migration or GPU work
occurs on import. Paths and user names never determine model identity.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
import json
import unicodedata

from .settings import atomic_private_json

CATALOG_VERSION = 1
BACKEND_API_VERSION = 1
PRODUCT_SCOPE_VERSION = 1
DEFAULT_CHARACTER_ID = 'lime'
# Release scope is distinct from technical readiness/license validation. Adding
# catalog metadata must never silently add a launch requirement or UI choice.
RELEASE_CHARACTER_IDS = ('lime',)


@dataclass(frozen=True)
class CharacterModel:
    character_id: str
    default_name: str
    description: str
    repository: str
    revision: str
    model_file: str | None
    sha256: str | None
    size_bytes: int | None
    backend: str
    model_format: str
    quantization: str | None
    base_dependency: str
    license: str
    license_url: str
    chat_template: str
    blocker: str | None = None
    # Unmeasured profiles must not silently inherit the QLoRA training budget.
    resource_profile: str = 'NOT VERIFIED'
    tokenizer: str = 'provider GGUF metadata; exact upstream revision NOT VERIFIED'
    context_limit: int | None = None
    adapter_dependency: str | None = None

    def verify_file(self, path: Path) -> bool:
        if not self.sha256 or not self.size_bytes:
            return False
        if path.is_symlink() or not path.is_file() or path.stat().st_size != self.size_bytes:
            return False
        digest = hashlib.sha256()
        with path.open('rb') as handle:
            for block in iter(lambda: handle.read(4 * 1024**2), b''):
                digest.update(block)
        return digest.hexdigest() == self.sha256


CHARACTERS = (
    CharacterModel('yaho', '야호', '활발하고 장난스러운 한국어 갸루 캐릭터',
        'ChanLumerico/EXAONE-3.5-7.8B-Instruct-Yaho',
        '24a501c8107a07ea18c9657e84525a081741be02',
        'gguf/EXAONE-3.5-7.8B-Instruct-Yaho-Q4_K_M.gguf',
        'a52795a05e9cd2a62aef491a2040a3b6ada658cf1c7ac598a480678eafd9bd96',
        4770651872, 'llama.cpp', 'GGUF', 'Q4_K_M',
        'LGAI-EXAONE/EXAONE-3.5-7.8B-Instruct', 'EXAONE AI Model License 1.1-NC',
        'https://huggingface.co/ChanLumerico/EXAONE-3.5-7.8B-Instruct-Yaho/blob/24a501c8107a07ea18c9657e84525a081741be02/LICENSE',
        'provider GGUF embedded template; identity override NOT VERIFIED',
        'research_only_license_product_use_review_required'),
    CharacterModel('lime', '라임', '차분하고 간결한 한국어 여성 AI',
        'naksyu/lime_Q6_K', '99280194d4593f0efe2d6a9ac79a697b0ec5e880',
        'gemma4_e4b_lime_persona500_Q6_K_limechat.gguf',
        'bafcfe3f624f0e1f84014c9b9136788992629955f7ce9146941226cd280d618e',
        6217263584, 'llama.cpp', 'GGUF', 'Q6_K', 'google/gemma-4-E4B',
        'Apache-2.0',
        'https://huggingface.co/naksyu/lime_Q6_K/blob/99280194d4593f0efe2d6a9ac79a697b0ec5e880/LICENSE',
        'provider limechat GGUF embedded template; tokenizer provenance NOT VERIFIED'),
    CharacterModel('it-planner', '기획자', '논리적이고 직설적인 여성 IT 기획자',
        '92doolgi/Persona-Driven_Korean_Debate_Bot',
        '3001bbc98605fbdb8754e16c17513cdc1724656f', None, None, None,
        'peft', 'PEFT', None, 'google/gemma-4-E2B', 'UNRESOLVED (card: gemma)',
        'https://huggingface.co/92doolgi/Persona-Driven_Korean_Debate_Bot',
        'NOT VERIFIED', 'missing_adapter_weights_and_exact_base_revision'),
)


def discover() -> tuple[CharacterModel, ...]:
    """Immutable catalog; installation, validation and runtime are separate states."""
    return CHARACTERS


def character(character_id: str) -> CharacterModel:
    for entry in CHARACTERS:
        if entry.character_id == character_id:
            return entry
    raise ValueError('Unknown character ID')


def default_character() -> CharacterModel:
    """Product default only; never changes existing settings or loads a model."""
    return character(DEFAULT_CHARACTER_ID)


def product_characters(*, include_future: bool = False) -> tuple[CharacterModel, ...]:
    """Default installer/selector entries; membership does not imply READY.

    Full discovery remains available for diagnostics and future catalog work.
    Future entries keep their actual blockers and cannot be offered as usable.
    """
    return discover() if include_future else tuple(character(cid) for cid in RELEASE_CHARACTER_IDS)


def valid_name(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError('Name must be text')
    value = value.strip()
    if not 1 <= len(value) <= 32 or any(unicodedata.category(c).startswith('C') for c in value):
        raise ValueError('Name must contain 1–32 visible characters')
    if any(c in value for c in '<>\n\r'):
        raise ValueError('Name contains a role or mention delimiter')
    return value


class CharacterNames:
    """Explicit separate local file, never migrates Settings/CompanionStore.

    The manager performs live renames; this object only persists per-ID choices.
    No Discord profile or nickname API is involved.
    """
    def __init__(self, path: Path):
        self.path = Path(path)
        self.names = {}
        if self.path.exists():
            data = json.loads(self.path.read_text('utf-8'))
            if not isinstance(data, dict) or set(data) != {'schema', 'names'} or data['schema'] != 1 or not isinstance(data['names'], dict):
                raise ValueError('Unsupported character-name document')
            for key, name in data['names'].items():
                character(key)
                self.names[key] = valid_name(name)

    def effective(self, character_id: str) -> str:
        return self.names.get(character_id, character(character_id).default_name)

    def save(self, character_id: str, name: str):
        character(character_id)
        updated = dict(self.names, **{character_id: valid_name(name)})
        atomic_private_json(self.path, {'schema': 1, 'names': updated})
        self.names = updated


def identity_message(entry: CharacterModel, name: str) -> dict:
    # JSON quoting preserves the name as data; no string replacement in provider
    # templates or old memories. Actual model adherence still requires GPU QA.
    return {'role': 'system', 'content':
        '현재 대화에서 사용하는 자기 이름은 ' + json.dumps(valid_name(name), ensure_ascii=False) +
        '이다. 기존 캐릭터의 말투와 성향은 유지한다. 이 이름 설정은 실제 기억, '
        '기능 실행 영수증 또는 개인정보 접근 권한이 아니다.'}


def with_identity(entry: CharacterModel, name: str, messages: list[dict]) -> list[dict]:
    """One trusted leading header for templates with a first-system contract.

    Keep existing policy/facts before the minimal identity override. Never move
    a user/tool message into the trusted header or rewrite provider templates.
    """
    prefix = []
    index = 0
    while index < len(messages) and messages[index].get('role') in ('system', 'developer'):
        content = messages[index].get('content')
        if not isinstance(content, str):
            raise ValueError('Trusted character header must be text')
        prefix.append(content)
        index += 1
    if any(message.get('role') in ('system', 'developer') for message in messages[index:]):
        raise ValueError('Late policy message requires explicit context reconstruction')
    prefix.append(identity_message(entry, name)['content'])
    return [{'role': 'system', 'content': '\n\n'.join(prefix)}, *[dict(message) for message in messages[index:]]]
