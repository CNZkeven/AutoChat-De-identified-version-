from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_user
from ..models import User, UserAcademicReport, UserCourseReport
from ..schemas import (
    UserAcademicReportOut,
    UserCourseObjectiveOut,
    UserCourseOut,
    UserCourseReportOut,
    UserGraduationRequirementOut,
    UserProfileOut,
)
from ..services.academics import list_course_objectives, list_student_courses
from ..services.graduation_requirements import get_or_refresh_snapshot
from ..services.user_profiles import fetch_public_profile, generate_public_profile
from ..services.user_reports import build_training_plan, generate_academic_report, generate_course_report

router = APIRouter(prefix="/api/profile", tags=["profile"])


@router.get("/public", response_model=UserProfileOut)
def get_public_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserProfileOut:
    profile = fetch_public_profile(db, current_user.id)
    return UserProfileOut(content=profile.content if profile else None, updated_at=profile.updated_at if profile else None)


@router.post("/public", response_model=UserProfileOut)
def generate_public_profile_api(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserProfileOut:
    try:
        profile = generate_public_profile(db, current_user)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return UserProfileOut(content=profile.content, updated_at=profile.updated_at)


@router.get("/academics", response_model=list[UserCourseOut])
def list_my_courses(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    return list_student_courses(db, current_user.username, role="student")


@router.get("/courses/{offering_id}/objectives", response_model=list[UserCourseObjectiveOut])
def list_my_course_objectives(
    offering_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    return list_course_objectives(db, current_user.username, offering_id, role="student")


@router.get("/courses/{offering_id}/report", response_model=UserCourseReportOut)
def get_my_course_report(
    offering_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserCourseReportOut:
    report = (
        db.query(UserCourseReport)
        .filter(UserCourseReport.user_id == current_user.id, UserCourseReport.offering_id == offering_id)
        .first()
    )
    return UserCourseReportOut(
        content=report.content if report else None,
        updated_at=report.updated_at if report else None,
    )


@router.post("/courses/{offering_id}/report", response_model=UserCourseReportOut)
def generate_my_course_report(
    offering_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserCourseReportOut:
    try:
        report = generate_course_report(
            db,
            user_id=current_user.id,
            student_no=current_user.username,
            offering_id=offering_id,
            role="student",
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return UserCourseReportOut(content=report.content, updated_at=report.updated_at)


@router.get("/graduation-requirements", response_model=UserGraduationRequirementOut)
def get_graduation_requirements(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserGraduationRequirementOut:
    try:
        snapshot = get_or_refresh_snapshot(db, current_user, force_refresh=False)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    return UserGraduationRequirementOut(data=snapshot.data, updated_at=snapshot.updated_at)


@router.post("/graduation-requirements/refresh", response_model=UserGraduationRequirementOut)
def refresh_graduation_requirements(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserGraduationRequirementOut:
    try:
        snapshot = get_or_refresh_snapshot(db, current_user, force_refresh=True)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    return UserGraduationRequirementOut(data=snapshot.data, updated_at=snapshot.updated_at)


@router.get("/academic-report", response_model=UserAcademicReportOut)
def get_academic_report(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserAcademicReportOut:
    report = db.query(UserAcademicReport).filter(UserAcademicReport.user_id == current_user.id).first()
    return UserAcademicReportOut(content=report.content if report else None, updated_at=report.updated_at if report else None)


@router.post("/academic-report", response_model=UserAcademicReportOut)
def generate_academic_report_api(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserAcademicReportOut:
    try:
        snapshot = get_or_refresh_snapshot(db, current_user, force_refresh=True)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    training_plan = build_training_plan(db, snapshot.program_id)
    try:
        report = generate_academic_report(
            db,
            user_id=current_user.id,
            student_no=current_user.username,
            requirements_snapshot=snapshot.data,
            training_plan=training_plan,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return UserAcademicReportOut(content=report.content, updated_at=report.updated_at)
