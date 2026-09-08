from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class Specialist:
    name: str
    description: str
    skills: tuple[str, ...]
    tools: tuple[str, ...] = ()
    requires_approval_for_writes: bool = True


SPECIALISTS: dict[str, Specialist] = {
    "executive": Specialist(
        name="Executive Assistant",
        description="Priorities, planning, summaries, follow-ups, and project coordination.",
        skills=("executive-assistance", "planning", "summarization"),
        tools=("calendar", "email", "notes", "tasks"),
    ),
    "research": Specialist(
        name="Research Intelligence",
        description="Research, comparisons, source synthesis, and decision briefs.",
        skills=("research", "analysis", "reporting"),
        tools=("web", "files"),
        requires_approval_for_writes=False,
    ),
    "coding": Specialist(
        name="Tech Copilot",
        description="Coding, debugging, architecture, tests, and repository work.",
        skills=("coding", "debugging", "architecture"),
        tools=("github", "files"),
    ),
    "automation": Specialist(
        name="Automation Specialist",
        description="Workflow design, integrations, APIs, and agent automation.",
        skills=("automation", "integrations", "apis"),
        tools=("workflows", "connectors"),
    ),
    "business": Specialist(
        name="Business Assistant",
        description="Strategy, marketing, sales, positioning, and business analysis.",
        skills=("business-strategy", "marketing", "sales"),
        tools=("research", "files"),
    ),
    "market": Specialist(
        name="ATLAS Market Intelligence",
        description="Paper-only market analysis, scalping context, multi-timeframe analysis, news context, and risk review.",
        skills=("market-analysis", "technical-analysis", "market-structure", "risk-management"),
        tools=("market.analyze", "risk.evaluate", "paper.positions"),
        requires_approval_for_writes=True,
    ),
}


ROUTING_HINTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("market", ("market", "trade", "trading", "scalp", "scalping", "gold", "xau", "eurusd", "silver", "gas", "crypto")),
    ("coding", ("code", "coding", "bug", "debug", "github", "repo", "python", "fastapi", "react", "api error")),
    ("automation", ("automate", "automation", "workflow", "integration", "webhook", "n8n", "zapier", "make.com")),
    ("research", ("research", "compare", "study", "investigate", "sources", "report")),
    ("business", ("business", "marketing", "sales", "pricing", "campaign", "brand", "strategy")),
    ("executive", ("priority", "priorities", "plan", "schedule", "meeting", "summary", "follow up", "follow-up", "task", "remind")),
)


@dataclass
class RightHandPlan:
    request: str
    primary_specialist: str
    specialist_name: str
    selected_skills: list[str]
    suggested_tools: list[str]
    execution_mode: str
    approval_required: bool
    steps: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def route_request(text: str) -> str:
    normalized = " ".join(text.lower().split())
    for specialist, hints in ROUTING_HINTS:
        if any(hint in normalized for hint in hints):
            return specialist
    return "executive"


def build_right_hand_plan(text: str) -> RightHandPlan:
    request = text.strip()
    if not request:
        raise ValueError("Request must not be empty.")

    specialist_key = route_request(request)
    specialist = SPECIALISTS[specialist_key]
    approval_required = specialist.requires_approval_for_writes

    steps = [
        f"Route the request to {specialist.name}.",
        "Gather the minimum context required for the task.",
        "Use read-only tools first and produce a concrete result or proposed action.",
    ]
    if approval_required:
        steps.append("Require explicit approval before any consequential external write or mutation.")

    constraints = [
        "Do not invent tool results or claim actions were completed without verification.",
        "Keep external writes approval-gated.",
    ]
    execution_mode = "assist"
    if specialist_key == "market":
        execution_mode = "paper_only"
        constraints.extend([
            "Market intelligence remains paper/demo only.",
            "Do not route live orders to MT5 from the right-hand assistant.",
        ])

    return RightHandPlan(
        request=request,
        primary_specialist=specialist_key,
        specialist_name=specialist.name,
        selected_skills=list(specialist.skills),
        suggested_tools=list(specialist.tools),
        execution_mode=execution_mode,
        approval_required=approval_required,
        steps=steps,
        constraints=constraints,
        metadata={"version": "right-hand-v2"},
    )


def capabilities() -> dict[str, Any]:
    return {
        "name": "ATLAS Right Hand Agent",
        "version": "v2",
        "specialists": {
            key: {
                "name": value.name,
                "description": value.description,
                "skills": list(value.skills),
                "tools": list(value.tools),
                "requires_approval_for_writes": value.requires_approval_for_writes,
            }
            for key, value in SPECIALISTS.items()
        },
        "safety": {
            "external_writes": "approval_gated",
            "market_execution": "paper_only",
            "live_mt5_from_right_hand": False,
        },
    }
