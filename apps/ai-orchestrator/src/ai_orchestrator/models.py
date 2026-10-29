"""
AI Orchestrator Core Models
"""
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Literal, Callable, Awaitable, Union
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict, field_validator


class LLMProvider(str, Enum):
    """Supported LLM providers"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    LOCAL = "local"


class AgentStatus(str, Enum):
    """Agent execution status"""
    IDLE = "idle"
    RUNNING = "running"
    WAITING_TOOL = "waiting_tool"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SkillType(str, Enum):
    """Skill categories"""
    ANALYSIS = "analysis"
    GENERATION = "generation"
    TRANSFORMATION = "transformation"
    EXTRACTION = "extraction"
    CLASSIFICATION = "classification"
    SUMMARIZATION = "summarization"
    REASONING = "reasoning"
    PLANNING = "planning"
    EXECUTION = "execution"
    CUSTOM = "custom"


class ToolCategory(str, Enum):
    """Tool categories"""
    DATA_ACCESS = "data_access"
    API_CALL = "api_call"
    COMPUTATION = "computation"
    SEARCH = "search"
    COMMUNICATION = "communication"
    FILE_OPERATION = "file_operation"
    CODE_EXECUTION = "code_execution"
    VISUALIZATION = "visualization"
    CUSTOM = "custom"


class MemoryType(str, Enum):
    """Memory types"""
    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"
    WORKING = "working"


class ToolCallStatus(str, Enum):
    """Tool call execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class AgentRole(str, Enum):
    """Predefined agent roles"""
    ANALYST = "analyst"
    WRITER = "writer"
    CODER = "coder"
    RESEARCHER = "researcher"
    PLANNER = "planner"
    EXECUTOR = "executor"
    CRITIC = "critic"
    ORCHESTRATOR = "orchestrator"
    CUSTOM = "custom"


class LLMMessage(BaseModel):
    """LLM message"""
    role: Literal["system", "user", "assistant", "tool"]
    content: str
    name: Optional[str] = None
    tool_call_id: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None

    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat(),
        }
    )


class LLMResponse(BaseModel):
    """LLM response"""
    content: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
    finish_reason: Optional[str] = None
    usage: Optional[Dict[str, int]] = None
    model: Optional[str] = None
    provider: Optional[LLMProvider] = None
    latency_ms: int = 0


class ToolDefinition(BaseModel):
    """Tool definition for LLM function calling"""
    name: str
    description: str
    parameters: Dict[str, Any]  # JSON Schema
    category: ToolCategory = ToolCategory.CUSTOM
    required_permissions: List[str] = Field(default_factory=list)
    timeout_seconds: int = 30
    retryable: bool = True
    idempotent: bool = False


class ToolCall(BaseModel):
    """Tool call request/response"""
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    name: str
    arguments: Dict[str, Any]
    status: ToolCallStatus = ToolCallStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    latency_ms: int = 0
    retry_count: int = 0

    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat(),
        }
    )


class SkillParameter(BaseModel):
    """Skill parameter definition"""
    name: str
    type: Literal["string", "number", "boolean", "array", "object"]
    description: str
    required: bool = True
    default: Optional[Any] = None
    enum: Optional[List[Any]] = None


class SkillDefinition(BaseModel):
    """Skill definition"""
    skill_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    name: str
    description: str
    skill_type: SkillType = SkillType.CUSTOM
    version: str = "1.0.0"
    author: Optional[str] = None

    # Parameters
    parameters: List[SkillParameter] = Field(default_factory=list)
    required_params: List[str] = Field(default_factory=list)

    # Prompt template
    system_prompt: str
    user_prompt_template: str

    # Examples for few-shot
    examples: List[Dict[str, Any]] = Field(default_factory=list)

    # Constraints
    max_tokens: int = 2000
    temperature: float = 0.1
    allowed_tools: List[str] = Field(default_factory=list)
    required_context: List[str] = Field(default_factory=list)

    # Versioning
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    parent_skill_id: Optional[str] = None
    is_active: bool = True

    # Auto-training
    auto_training_enabled: bool = False
    training_data_path: Optional[str] = None
    min_training_samples: int = 100


class SkillExecution(BaseModel):
    """Skill execution record"""
    execution_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    skill_id: str
    agent_id: Optional[str] = None
    input_params: Dict[str, Any]
    output: Optional[Any] = None
    status: Literal["pending", "running", "completed", "failed"] = "pending"
    error: Optional[str] = None
    tokens_used: int = 0
    latency_ms: int = 0
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat(),
        }
    )


class MemoryEntry(BaseModel):
    """Memory entry"""
    memory_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    agent_id: str
    memory_type: MemoryType
    content: str
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    importance: float = 1.0
    access_count: int = 0
    last_accessed: datetime = Field(default_factory=datetime.utcnow)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    tags: List[str] = Field(default_factory=list)

    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat(),
        }
    )


class AgentConfig(BaseModel):
    """Agent configuration"""
    agent_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    name: str
    role: AgentRole = AgentRole.CUSTOM
    description: str = ""

    # LLM Configuration
    llm_provider: LLMProvider = LLMProvider.OPENAI
    model: Optional[str] = None
    temperature: float = 0.1
    max_tokens: int = 4096
    system_prompt: str = ""

    # Capabilities
    skills: List[str] = Field(default_factory=list)  # skill_ids
    allowed_tools: List[str] = Field(default_factory=list)
    max_iterations: int = 10
    max_tool_calls_per_iteration: int = 5

    # Memory
    memory_enabled: bool = True
    memory_config: Dict[str, Any] = Field(default_factory=dict)

    # Behavior
    verbose: bool = False
    stop_on_error: bool = True
    max_retries: int = 3

    # Timeouts
    execution_timeout_seconds: int = 300
    tool_timeout_seconds: int = 30

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None
    tags: List[str] = Field(default_factory=list)

    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat(),
        }
    )


class AgentState(BaseModel):
    """Agent runtime state"""
    agent_id: str
    status: AgentStatus = AgentStatus.IDLE
    current_iteration: int = 0
    current_task: Optional[str] = None
    context: Dict[str, Any] = Field(default_factory=dict)
    conversation_history: List[LLMMessage] = Field(default_factory=list)
    tool_calls: List[ToolCall] = Field(default_factory=list)
    skill_executions: List[SkillExecution] = Field(default_factory=list)
    memory_retrieved: List[MemoryEntry] = Field(default_factory=list)
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    tokens_used: int = 0
    total_latency_ms: int = 0

    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat(),
        }
    )


class AgentTask(BaseModel):
    """Task for agent execution"""
    task_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    agent_id: Optional[str] = None
    task_type: str
    description: str
    input_data: Dict[str, Any] = Field(default_factory=dict)
    context: Dict[str, Any] = Field(default_factory=dict)
    required_skills: List[str] = Field(default_factory=list)
    required_tools: List[str] = Field(default_factory=list)
    priority: int = 0
    timeout_seconds: Optional[int] = None
    callback_url: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    scheduled_at: Optional[datetime] = None

    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat(),
        }
    )


class AgentResult(BaseModel):
    """Agent execution result"""
    task_id: str
    agent_id: str
    status: AgentStatus
    output: Optional[Any] = None
    error: Optional[str] = None
    iterations: int = 0
    tokens_used: int = 0
    latency_ms: int = 0
    tool_calls: List[ToolCall] = Field(default_factory=list)
    skill_executions: List[SkillExecution] = Field(default_factory=list)
    started_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat(),
        }
    )


class TraceEvent(BaseModel):
    """Execution trace event"""
    trace_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    agent_id: str
    event_type: Literal["llm_call", "tool_call", "skill_execution", "memory_retrieval", "error", "state_change"]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    duration_ms: int = 0
    input_data: Optional[Dict[str, Any]] = None
    output_data: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None

    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat(),
        }
    )


class ExecutionTrace(BaseModel):
    """Complete execution trace"""
    trace_id: str
    agent_id: str
    task_id: Optional[str] = None
    events: List[TraceEvent] = Field(default_factory=list)
    started_at: datetime
    completed_at: Optional[datetime] = None
    total_duration_ms: int = 0
    total_tokens: int = 0
    final_status: AgentStatus

    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat(),
        }
    )


class SkillTrainingData(BaseModel):
    """Training data for skill auto-training"""
    skill_id: str
    input_params: Dict[str, Any]
    expected_output: Any
    quality_score: float = 1.0
    source: Literal["human", "agent", "synthetic"] = "agent"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    tags: List[str] = Field(default_factory=list)

    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat(),
        }
    )


class ToolResult(BaseModel):
    """Tool execution result"""
    tool_call_id: str
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    latency_ms: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class LLMProviderConfig(BaseModel):
    """LLM provider configuration"""
    provider: LLMProvider
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    organization: Optional[str] = None
    default_model: str
    max_tokens: int = 4096
    temperature: float = 0.1
    timeout_seconds: int = 60
    max_retries: int = 3
    extra_headers: Dict[str, str] = Field(default_factory=dict)