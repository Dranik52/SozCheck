from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import LocalizationFile


@receiver(post_delete, sender=LocalizationFile)
def delete_original_file_after_record_removal(sender, instance: LocalizationFile, **kwargs):
    """Remove private uploaded data when its owning database record is deleted."""
    if instance.file:
        instance.file.delete(save=False)
