from typing import TypedDict

from langgraph.graph import (
    END,
    START,
    StateGraph,
)

from app.agents.scientist import (
    generate_hypotheses,
)
from app.llm.factory import (
    get_llm_provider,
)


class PlanningState(TypedDict):
    context: str
    hypotheses: list[dict]


async def scientist_node(
    state: PlanningState,
) -> dict:
    provider = get_llm_provider()

    result = await generate_hypotheses(
        provider=provider,
        context=state["context"],
    )

    return {
        "hypotheses": [
            hypothesis.model_dump()
            for hypothesis
            in result.hypotheses
        ]
    }


builder = StateGraph(
    PlanningState
)

builder.add_node(
    "scientist",
    scientist_node,
)

builder.add_edge(
    START,
    "scientist",
)

builder.add_edge(
    "scientist",
    END,
)

planning_graph = builder.compile()