import pytest
from apps.rides.models import Ride, validate_status_transition


class TestStatusTransitions:

    def test_pending_to_accepted(self):
        assert validate_status_transition('pending', 'accepted') is True

    def test_pending_to_cancelled(self):
        assert validate_status_transition('pending', 'cancelled') is True

    def test_pending_to_completed_invalid(self):
        assert validate_status_transition('pending', 'completed') is False

    def test_accepted_to_in_progress(self):
        assert validate_status_transition('accepted', 'in_progress') is True

    def test_completed_cannot_transition(self):
        assert validate_status_transition('completed', 'cancelled') is False

    def test_in_progress_to_completed(self):
        assert validate_status_transition('in_progress', 'completed') is True