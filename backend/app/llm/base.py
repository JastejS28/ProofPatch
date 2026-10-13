from abc import ABC, abstractmethod
from typing import TypeVar

from pydantic import BaseModel


T = TypeVar(
    "T",
    bound=BaseModel,
)


class LLMProvider(ABC):

    @abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        response_model: type[T],
    ) -> T:
        raise NotImplementedError