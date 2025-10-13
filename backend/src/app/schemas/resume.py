from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, EmailStr, Field, HttpUrl

SchemaVersion = Literal["1.0.0"]


class Socials(BaseModel):
    github: HttpUrl | None = None
    linkedin: HttpUrl | None = None
    website: HttpUrl | None = None
    x: HttpUrl | None = None


class EducationItem(BaseModel):
    college: str
    degree: str | None = None
    gpa: str | None = None
    years: str | None = None


class ExperienceItem(BaseModel):
    role: str
    company: str | None = None
    period: str | None = None
    details: list[str] = Field(default_factory=list)


class ProjectItem(BaseModel):
    name: str
    tech_stack: str | None = None
    details: list[str] = Field(default_factory=list)


class Skills(BaseModel):
    languages: list[str] = Field(default_factory=list)
    frameworks: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)


class AchievementItem(BaseModel):
    title: str
    description: str | None = None


class Resume(BaseModel):
    schemaVersion: SchemaVersion = "1.0.0"
    source_file: str | None = None

    name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    location: str | None = None

    socials: Socials | None = Field(default_factory=Socials)

    education: list[EducationItem] | None = Field(default_factory=list)
    experience: list[ExperienceItem] | None = Field(default_factory=list)
    projects: list[ProjectItem] | None = Field(default_factory=list)
    skills: Skills | None = Field(default_factory=Skills)
    certifications: list[str] | None = Field(default_factory=list)
    achievements: list[AchievementItem] | None = Field(default_factory=list)
    summary: str | None = None
