from django.db import models
from django.utils.translation import gettext_lazy as _

# Create your models here.
class SiteSettings(models.Model):
    """
    A singleton model to store site-wide settings.
    Ensures there are only one row of settings in the database.
    """
    coming_soon_mode = models.BooleanField(
        default=False,
        verbose_name=_("Activate 'Coming Soon' Mode"),
        help_text=_("If checked, visitors will see the 'Coming Soon' overlay instead of the main site content.")
    )

    class Meta:
        verbose_name = _("Site Setting")
        verbose_name_plural = _("Site Settings")

    def __str__(self):
        return str(_("Site Settings"))

    @classmethod
    def load(cls):
        """
        Load the single SiteSettings instance, creating it if it doesn't exist.
        """
        obj, created = cls.objects.get_or_create(pk=1)
        return obj
