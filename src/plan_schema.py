from pydantic import BaseModel, Field
from typing import List

class FileSpec(BaseModel):
    path: str = Field(description="Relative path from project root")
    purpose: str = Field(description="What this file does")
    dependencies: List[str] = Field(default_factory=list)
    test_strategy: str = Field(default="unit", description="Testing strategy: unit, integration, e2e, or visual")

class TechStack(BaseModel):
    language: str
    framework: str
    testing: str
    styling: str
    build_tool: str

class Milestone(BaseModel):
    name: str
    description: str
    files_to_create: List[FileSpec]
    test_requirements: List[str]
    approval_required: bool = False

class ProjectPlan(BaseModel):
    project_name: str
    description: str
    tech_stack: TechStack
    milestones: List[Milestone]
    architecture_diagram: str = Field(description="Mermaid diagram as string")
    security_considerations: List[str]
    performance_budget: str = Field(description="e.g., 'Lighthouse score > 90, bundle < 200kb'")

    def validate_plan(self) -> List[str]:
        """Static validation before execution begins."""
        errors = []
        all_paths = []
        for m in self.milestones:
            for f in m.files_to_create:
                if f.path in all_paths:
                    errors.append(f"Duplicate file path: {f.path}")
                all_paths.append(f.path)
                if ".." in f.path or f.path.startswith('/'):
                    errors.append(f"Unsafe path detected: {f.path}")
        return errors