"""Pydantic models for FreeCV cv.json v1.2 (https://freecv.org/schema/cv/v1.json)."""

from __future__ import annotations

import re
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

DATE_PATTERN = re.compile(r"^[0-9]{4}(-[0-9]{2}(-[0-9]{2})?)?$")
CV_SCHEMA_URI = "https://freecv.org/schema/cv/v1.json"


def _normalize_date(value: str | None) -> str | None:
    if value is None or not str(value).strip():
        return None
    raw = str(value).strip()
    if DATE_PATTERN.match(raw):
        return raw
    # MM/YYYY or MM/YYYY - MM/YYYY
    m = re.match(r"^(\d{1,2})/(\d{4})$", raw)
    if m:
        return f"{m.group(2)}-{int(m.group(1)):02d}"
    if re.match(r"^\d{4}$", raw):
        return raw
    # Dec 2022, Jun 2022
    months = {
        "jan": "01", "feb": "02", "mar": "03", "apr": "04",
        "may": "05", "jun": "06", "jul": "07", "aug": "08",
        "sep": "09", "oct": "10", "nov": "11", "dec": "12",
    }
    m = re.match(r"^([A-Za-z]{3,9})\s+(\d{4})$", raw)
    if m:
        month = months.get(m.group(1).lower()[:3])
        if month:
            return f"{m.group(2)}-{month}"
    return raw


class Profile(BaseModel):
    network: str
    username: str | None = None
    url: str


class Basics(BaseModel):
    name: str = Field(min_length=1)
    label: str | None = None
    email: str | None = None
    phone: str | None = None
    image: str | None = None
    summary: str | None = None
    location: str | None = None
    url: str | None = None
    profiles: list[Profile] = Field(default_factory=list)


class WorkEntry(BaseModel):
    company: str
    position: str
    location: str | None = None
    startDate: str | None = None
    endDate: str | None = None
    current: bool | None = None
    summary: str | None = None
    highlights: list[str] = Field(default_factory=list)

    @field_validator("startDate", "endDate", mode="before")
    @classmethod
    def normalize_dates(cls, v: str | None) -> str | None:
        return _normalize_date(v)


class EducationEntry(BaseModel):
    institution: str
    degree: str
    field: str | None = None
    startDate: str | None = None
    endDate: str | None = None
    score: str | None = None
    summary: str | None = None
    highlights: list[str] = Field(default_factory=list)

    @field_validator("startDate", "endDate", mode="before")
    @classmethod
    def normalize_dates(cls, v: str | None) -> str | None:
        return _normalize_date(v)


class LanguageEntry(BaseModel):
    language: str
    fluency: str | None = None


class ProjectEntry(BaseModel):
    name: str
    description: str | None = None
    role: str | None = None
    url: str | None = None
    keywords: list[str] = Field(default_factory=list)
    highlights: list[str] = Field(default_factory=list)
    current: bool | None = None
    startDate: str | None = None
    endDate: str | None = None

    @field_validator("startDate", "endDate", mode="before")
    @classmethod
    def normalize_dates(cls, v: str | None) -> str | None:
        return _normalize_date(v)


class CertificateEntry(BaseModel):
    name: str
    issuer: str | None = None
    date: str | None = None
    url: str | None = None

    @field_validator("date", mode="before")
    @classmethod
    def normalize_date(cls, v: str | None) -> str | None:
        return _normalize_date(v)


class ReferenceEntry(BaseModel):
    name: str
    title: str | None = None
    company: str | None = None
    relationship: str | None = None
    email: str | None = None
    phone: str | None = None


class PublicationEntry(BaseModel):
    name: str
    publisher: str | None = None
    releaseDate: str | None = None
    url: str | None = None
    summary: str | None = None

    @field_validator("releaseDate", mode="before")
    @classmethod
    def normalize_date(cls, v: str | None) -> str | None:
        return _normalize_date(v)


class AwardEntry(BaseModel):
    title: str
    date: str | None = None
    awarder: str | None = None
    summary: str | None = None

    @field_validator("date", mode="before")
    @classmethod
    def normalize_date(cls, v: str | None) -> str | None:
        return _normalize_date(v)


class VolunteerEntry(BaseModel):
    organization: str
    position: str | None = None
    url: str | None = None
    summary: str | None = None
    startDate: str | None = None
    endDate: str | None = None
    highlights: list[str] = Field(default_factory=list)

    @field_validator("startDate", "endDate", mode="before")
    @classmethod
    def normalize_dates(cls, v: str | None) -> str | None:
        return _normalize_date(v)


class Meta(BaseModel):
    version: str = "1.2"
    canonical: str
    lastModified: str
    generator: str = "cv_analyser"


class CvDocument(BaseModel):
    schema_uri: str = Field(default=CV_SCHEMA_URI, alias="$schema")
    basics: Basics
    work: list[WorkEntry] = Field(default_factory=list)
    education: list[EducationEntry] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    languages: list[LanguageEntry] = Field(default_factory=list)
    projects: list[ProjectEntry] = Field(default_factory=list)
    certificates: list[CertificateEntry] = Field(default_factory=list)
    references: list[ReferenceEntry] = Field(default_factory=list)
    referencesMode: Literal["show", "on-request", "hide"] | None = None
    publications: list[PublicationEntry] = Field(default_factory=list)
    awards: list[AwardEntry] = Field(default_factory=list)
    interests: list[str] = Field(default_factory=list)
    volunteer: list[VolunteerEntry] = Field(default_factory=list)
    meta: Meta

    model_config = ConfigDict(populate_by_name=True, ser_json_by_alias=True)

    @classmethod
    def build_meta(cls) -> Meta:
        return Meta(
            canonical="https://cv-analyser.local/extracted",
            lastModified=date.today().isoformat(),
            generator="cv_analyser",
        )
