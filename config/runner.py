from django.test.runner import DiscoverRunner
from django.test.utils import override_settings

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

    def setup_test_environment(self, **kwargs):
        super().setup_test_environment(**kwargs)
        self._settings_override = override_settings(
            CACHES={
                'default': {
                    'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
                    'LOCATION': 'test-runner-cache',
                }
            }
        )
        self._settings_override.enable()

    def teardown_test_environment(self, **kwargs):
        if hasattr(self, '_settings_override'):
            self._settings_override.disable()
        super().teardown_test_environment(**kwargs)

