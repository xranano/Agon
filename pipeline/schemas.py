from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


AgentId = Literal["agent_1", "agent_2", "agent_3", "agent_4", "agent_5"]
SolverRole = Literal["solver_1", "solver_2", "solver_3", "solver_4"]
DebateRole = Literal["Solver", "Judge"]
Severity = Literal["minor", "major", "critical"]
AssessmentLabel = Literal["correct", "mostly_correct", "promising_but_flawed", "incorrect"]
SelectionMode = Literal["auto", "selector"]


class ConfidenceScores(BaseModel):
    Solver: float = Field(ge=0.0, le=1.0)
    Judge: float = Field(ge=0.0, le=1.0)


class RoleAssessment(BaseModel):
    agent: AgentId
    agent_name: str
    confidence: ConfidenceScores
    preferred_role: DebateRole
    reasoning: str


class AssignedRoles(BaseModel):
    judge: AgentId
    solvers: List[AgentId] = Field(min_length=2, max_length=4)
    solver_roles: Dict[SolverRole, AgentId]
    assignment_rule: str
    selection_mode: SelectionMode = "auto"
    selector_reasoning: Optional[str] = None


class SelectorDecision(BaseModel):
    judge: AgentId
    solver_1: AgentId
    solver_2: AgentId
    solver_3: Optional[AgentId] = None
    solver_4: Optional[AgentId] = None
    reasoning: str


class SolverSolution(BaseModel):
    solver_role: SolverRole
    agent_id: AgentId
    agent_name: str
    solution: str
    answer: str
    confidence: float = Field(ge=0.0, le=1.0)


class ReviewError(BaseModel):
    location: str
    error_type: str
    description: str
    severity: Severity


class PeerReview(BaseModel):
    reviewer_role: SolverRole
    target_role: SolverRole
    strengths: List[str]
    weaknesses: List[str]
    errors: List[ReviewError]
    suggested_changes: List[str]
    overall_assessment: AssessmentLabel


class CritiqueResponse(BaseModel):
    critique: str
    response: str
    accepted: bool


class RefinedSolution(BaseModel):
    solver_role: SolverRole
    agent_id: AgentId
    agent_name: str
    changes_made: List[CritiqueResponse]
    refined_solution: str
    refined_answer: str
    confidence: float = Field(ge=0.0, le=1.0)


class JudgeDecision(BaseModel):
    judge_agent_id: AgentId
    judge_agent_name: str
    winner: SolverRole
    final_answer: str
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
