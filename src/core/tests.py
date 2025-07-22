# src/core/tests.py

from django.test import TestCase, Client
from django.urls import reverse
from django.db import connection, OperationalError
from .models import SiteSettings

class CoreFunctionalityTests(TestCase):
    """
    Test suite for the core application functionality.
    Each test is designed to be verbose, explaining what it does and why,
    to make the output of the test runner more informative.
    """

    def setUp(self):
        """
        Set up the test environment before each test method is run.
        This includes creating a Django test client and any necessary initial data.
        """
        self.client = Client()
        print("\n- Setting up for a new test...")

    def test_main_page_loads_successfully(self):
        """
        [Test 1/3] Checks if the main page (homepage) is accessible.

        Purpose:
        - This test verifies that the primary URL ('/') is correctly routed to its view.
        - It confirms that the view can be rendered without errors.
        - A successful test (status code 200) is a fundamental check for any web application.
        """
        print("  - Running test: Accessing the main page...")
        url = reverse('core:index')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        print(f"  - OK: Main page at '{url}' returned status code 200.")

    def test_singleton_site_settings_model(self):
        """
        [Test 2/3] Validates the behavior of the singleton SiteSettings model.

        Purpose:
        - To ensure that the custom .load() method correctly fetches or creates the settings object.
        - To confirm that the model's default values are set as expected upon creation.
        - This also serves as an indirect test of the database connection from the model level.
        """
        print("  - Running test: Loading the SiteSettings model...")
        settings = SiteSettings.load()

        self.assertIsInstance(settings, SiteSettings)
        print(f"  - OK: Loaded object is an instance of SiteSettings.")

        self.assertFalse(settings.coming_soon_mode)
        print(f"  - OK: Default 'coming_soon_mode' is correctly set to False.")

        settings_again = SiteSettings.load()
        self.assertEqual(settings.pk, settings_again.pk)
        print(f"  - OK: Singleton pattern confirmed; loading again returns the same object (pk={settings.pk}).")


    def test_direct_database_connection(self):
        """
        [Test 3/3] Performs a direct check of the database connection.

        Purpose:
        - To isolate and confirm that the Django application can communicate with the database.
        - This test bypasses the ORM to execute a raw SQL query, providing a definitive
          check of the underlying database connection settings.
        """
        print("  - Running test: Executing a direct database query...")
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()

            self.assertEqual(result[0], 1)
            print("  - OK: Direct database query was successful.")

        except OperationalError as e:
            self.fail(f"  - FAIL: Database connection test failed with an error: {e}")

    def tearDown(self):
        """
        Clean up after each test has run.
        """
        print("- Test finished.")