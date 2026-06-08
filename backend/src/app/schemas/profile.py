from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class ProficiencyLevel(str, Enum):
    NOVICE = "NOVICE"
    INTERMEDIATE = "INTERMEDIATE"
    ADVANCED = "ADVANCED"
    EXPERT = "EXPERT"


class SkillSchema(BaseModel):
    id: UUID | None = None
    skill_name: str
    years_experience: Decimal = Field(..., max_digits=3, decimal_places=1)
    proficiency: ProficiencyLevel

    class Config:
        from_attributes = True


class ExperienceSchema(BaseModel):
    id: UUID | None = None
    company_name: str
    job_title: str
    start_date: date
    end_date: date | None = None
    description: str
    is_current: bool

    @model_validator(mode="after")
    def validate_dates(self) -> ExperienceSchema:
        if not self.is_current and self.end_date and self.start_date > self.end_date:
            raise ValueError("start_date cannot be later than end_date")
        return self

    class Config:
        from_attributes = True


class EducationSchema(BaseModel):
    id: UUID | None = None
    institution: str
    degree: str | None = None
    field_of_study: str | None = None
    start_date: date
    end_date: date | None = None

    @model_validator(mode="after")
    def validate_dates(self) -> EducationSchema:
        if self.end_date and self.start_date > self.end_date:
            raise ValueError("start_date cannot be later than end_date")
        return self

    class Config:
        from_attributes = True


class ProjectSchema(BaseModel):
    id: UUID | None = None
    project_name: str
    description: str
    role_description: str | None = None
    url: str | None = None

    class Config:
        from_attributes = True


class ProfileUpdate(BaseModel):
    headline: str | None = None
    summary: str | None = None
    location: str | None = None
    current_salary: Decimal | None = None
    skills: list[SkillSchema] = []
    experiences: list[ExperienceSchema] = []
    education: list[EducationSchema] = []
    projects: list[ProjectSchema] = []

    @model_validator(mode="after")
    def validate_current_experiences(self) -> ProfileUpdate:
        current_jobs = [exp for exp in self.experiences if exp.is_current]
        if len(current_jobs) > 2:
            raise ValueError("At most two experiences can be active concurrently")
        return self


class ProfileResponse(BaseModel):
    id: UUID
    user_id: UUID
    headline: str | None = None
    summary: str | None = None
    location: str | None = None
    current_salary: Decimal | None = None
    skills: list[SkillSchema] = []
    experiences: list[ExperienceSchema] = []
    education: list[EducationSchema] = []
    projects: list[ProjectSchema] = []

    class Config:
        from_attributes = True


class ResumeUploadResponse(BaseModel):
    resume_id: UUID
    confidence_score: Decimal = Field(..., max_digits=3, decimal_places=2)
    parsed_data: ProfileUpdate


class ResumeSyncRequest(BaseModel):
    resume_id: UUID
    override_data: ProfileUpdate


class ProfileVersionResponse(BaseModel):
    id: UUID
    profile_id: UUID
    version_number: int
    snapshot_payload: dict
    created_at: datetime

    class Config:
        from_attributes = True

