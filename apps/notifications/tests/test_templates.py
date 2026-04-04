from apps.notifications.templates import get_notification_content


class TestNotificationTemplates:
    """Tests for notification message templates."""
    def test_ride_accepted_template(self):
        """Test that ride_accepted template correctly substitutes context variables."""
        content = get_notification_content('ride_accepted', {
            'driver_name': 'John', 'eta_minutes': 5
        })
        assert 'John' in content['message']
        assert '5' in content['message']

    def test_unknown_type_fallback(self):
        """Test that unknown notification type returns default content."""
        content = get_notification_content('unknown_type')
        assert content['title'] == 'Notification'

    def test_template_without_context(self):
        """Test that templates without context variables work."""
        content = get_notification_content('ride_created')
        assert content['title']
        assert content['message']

    def test_all_templates_valid(self):
        """Test that all templates can be rendered without errors."""
        from apps.notifications.templates import NOTIFICATION_TEMPLATES
        for ntype in NOTIFICATION_TEMPLATES:
            content = get_notification_content(ntype)
            assert content['title']
            assert content['message']
