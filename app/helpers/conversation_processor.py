import asyncio
import itertools
import logging
from collections import deque

from app.config import MEMORY_MAX_ENTRIES, RECENT_MESSAGE_LIMIT
from app.services.memory import MemoryCurator

logger = logging.getLogger(__name__)


class ConversationProcessor:
    """Recent-window history + LLM-curated long-term memory, all in RAM.

    The last RECENT_MESSAGE_LIMIT individual messages (10 user/ai
    exchanges) are the main context. When older messages fall out of that
    window they are handed to the MemoryCurator (OpenRouter) as a
    fire-and-forget task that distills them into fact entries; when the
    store fills, the curator picks the least-important entries to delete.

    add_conversation() is synchronous and never blocks the event loop —
    all curator LLM work happens in background tasks after the turn ends.
    """

    def __init__(self):
        self.recent = deque(maxlen=RECENT_MESSAGE_LIMIT)
        self.memory: dict[int, dict] = {}  # id -> {"fact", "importance"}
        self._next_id = itertools.count(1)
        self.curator = MemoryCurator()
        self._curate_lock = asyncio.Lock()
        self._curate_tasks: set[asyncio.Task] = set()

    def add_conversation(self, context):
        user = context['user']
        ai = context['ai']

        # make room for both messages up front, capturing what falls out
        overflow = max(len(self.recent) + 2 - self.recent.maxlen, 0)
        evicted = [self.recent.popleft() for _ in range(overflow)]

        self.recent.append({'user': user})
        self.recent.append({'ai': ai})

        if evicted:
            self._spawn_curate(evicted)

    def _spawn_curate(self, evicted: list[dict]):
        # evicted messages come in user/ai pairs; be defensive about strays
        exchange = {}
        for msg in evicted:
            if 'user' in msg and 'user' not in exchange:
                exchange['user'] = msg['user']
            elif 'ai' in msg and 'ai' not in exchange:
                exchange['ai'] = msg['ai']
        if 'user' not in exchange or 'ai' not in exchange:
            return
        task = asyncio.create_task(self._curate(exchange))
        self._curate_tasks.add(task)
        task.add_done_callback(self._curate_tasks.discard)

    async def _curate(self, exchange: dict):
        # serialize: two overlapping responses must not double-evict
        async with self._curate_lock:
            facts = await self.curator.distill(exchange)
            for fact in facts:
                self.memory[next(self._next_id)] = fact
            if facts:
                logger.info("Memory: +%d facts (%d entries)", len(facts), len(self.memory))

            if len(self.memory) > MEMORY_MAX_ENTRIES:
                slots = len(self.memory) - MEMORY_MAX_ENTRIES
                entries = sorted(self.memory.items())  # oldest first on ties
                ids = await self.curator.evict(entries, slots)
                for eid in ids:
                    self.memory.pop(eid, None)
                if ids:
                    logger.info("Memory: evicted ids %s (%d entries remain)", ids, len(self.memory))

    def get_conversation(self):
        return list(self.recent)

    def get_memory_digest(self) -> str:
        if not self.memory:
            return ""
        return "\n".join(
            f"- [importance {e['importance']}] {e['fact']}"
            for e in self.memory.values()
        )

    def get_whole_conversation(self):
        return list(self.recent)
