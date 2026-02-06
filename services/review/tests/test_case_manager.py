"""Tests for case management workflow."""

import pytest
from src.models import CaseStatus, CreateCaseRequest, Resolution, UpdateCaseRequest
from src.services.case_manager import CaseManager


@pytest.fixture
def manager():
    return CaseManager()


@pytest.fixture
def sample_case(manager):
    return manager.create_case(CreateCaseRequest(
        detection_id="det-001",
        user_id="user-alice",
        thread_id="thread-100",
        priority=5,
    ))


class TestCaseCreation:
    def test_create_case(self, manager):
        case = manager.create_case(CreateCaseRequest(
            detection_id="det-001",
            user_id="user-alice",
            thread_id="thread-100",
            priority=3,
        ))
        assert case.id is not None
        assert case.status == CaseStatus.OPEN
        assert case.user_id == "user-alice"
        assert case.priority == 3

    def test_create_case_default_priority(self, manager):
        case = manager.create_case(CreateCaseRequest(
            detection_id="det-002",
            user_id="user-bob",
            thread_id="thread-200",
        ))
        assert case.priority == 0


class TestCaseRetrieval:
    def test_get_case(self, manager, sample_case):
        retrieved = manager.get_case(sample_case.id)
        assert retrieved is not None
        assert retrieved.id == sample_case.id

    def test_get_nonexistent(self, manager):
        assert manager.get_case("nonexistent") is None

    def test_get_case_detail(self, manager, sample_case):
        detail = manager.get_case_detail(sample_case.id)
        assert detail is not None
        assert detail.actions == []

    def test_list_cases(self, manager):
        for i in range(5):
            manager.create_case(CreateCaseRequest(
                detection_id=f"det-{i}",
                user_id=f"user-{i}",
                thread_id=f"thread-{i}",
                priority=i,
            ))
        result = manager.list_cases()
        assert result.total == 5
        assert len(result.cases) == 5

    def test_list_cases_filter_status(self, manager, sample_case):
        result = manager.list_cases(status=CaseStatus.OPEN)
        assert result.total >= 1
        assert all(c.status == CaseStatus.OPEN for c in result.cases)

    def test_list_cases_pagination(self, manager):
        for i in range(10):
            manager.create_case(CreateCaseRequest(
                detection_id=f"det-{i}",
                user_id="user-1",
                thread_id=f"thread-{i}",
            ))
        page1 = manager.list_cases(limit=3, offset=0)
        page2 = manager.list_cases(limit=3, offset=3)
        assert page1.total == 10
        assert len(page1.cases) == 3
        assert len(page2.cases) == 3


class TestCaseUpdates:
    def test_assign_moderator(self, manager, sample_case):
        updated = manager.update_case(sample_case.id, UpdateCaseRequest(
            assigned_to="mod-dan",
        ))
        assert updated.assigned_to == "mod-dan"
        assert updated.status == CaseStatus.IN_REVIEW  # Auto-transition

    def test_resolve_case(self, manager, sample_case):
        # First move to in_review
        manager.update_case(sample_case.id, UpdateCaseRequest(
            status=CaseStatus.IN_REVIEW,
        ))
        # Then resolve
        updated = manager.update_case(sample_case.id, UpdateCaseRequest(
            status=CaseStatus.RESOLVED,
            resolution=Resolution.CONFIRMED,
            resolution_note="Verified phone number exchange",
        ))
        assert updated.status == CaseStatus.RESOLVED
        assert updated.resolution == Resolution.CONFIRMED

    def test_invalid_transition(self, manager, sample_case):
        with pytest.raises(ValueError, match="Invalid status transition"):
            manager.update_case(sample_case.id, UpdateCaseRequest(
                status=CaseStatus.OVERTURNED,
            ))

    def test_update_nonexistent(self, manager):
        result = manager.update_case("nonexistent", UpdateCaseRequest(
            status=CaseStatus.IN_REVIEW,
        ))
        assert result is None


class TestAppeals:
    def test_file_appeal(self, manager, sample_case):
        # Resolve first
        manager.update_case(sample_case.id, UpdateCaseRequest(
            status=CaseStatus.IN_REVIEW,
        ))
        manager.update_case(sample_case.id, UpdateCaseRequest(
            status=CaseStatus.RESOLVED,
        ))
        # Then appeal
        case = manager.file_appeal(sample_case.id, "I was discussing a different topic")
        assert case.status == CaseStatus.APPEALED

    def test_cannot_appeal_open_case(self, manager, sample_case):
        with pytest.raises(ValueError, match="Cannot appeal"):
            manager.file_appeal(sample_case.id, "reason")

    def test_appeal_nonexistent(self, manager):
        result = manager.file_appeal("nonexistent", "reason")
        assert result is None
