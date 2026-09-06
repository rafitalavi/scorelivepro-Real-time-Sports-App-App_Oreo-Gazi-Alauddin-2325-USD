from django.test.runner import DiscoverRunner

class CustomDiscoverRunner(DiscoverRunner):
    """
    Custom test runner that defaults to installed application labels
    (users, sports, notifications, monitoring) when no test labels are provided,
    preventing submodule path mismatches with the apps/ directory.
    """
    def build_suite(self, test_labels=None, extra_tests=None, **kwargs):
        if not test_labels:
            test_labels = ['users', 'sports', 'notifications', 'monitoring']
        return super().build_suite(test_labels, extra_tests=extra_tests, **kwargs)
