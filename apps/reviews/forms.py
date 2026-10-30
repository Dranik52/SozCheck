from django import forms

from .models import Review


class ReviewForm(forms.ModelForm):
    decision = forms.ChoiceField(choices=(
        (Review.Status.APPROVED, "Approve suggestion"),
        (Review.Status.REJECTED, "Reject suggestion"),
        (Review.Status.EDITED, "Save edit and approve"),
    ))

    class Meta:
        model = Review
        fields = ("final_translation", "reviewer_comment")
        widgets = {
            "final_translation": forms.Textarea(attrs={"rows": 3}),
            "reviewer_comment": forms.Textarea(attrs={"rows": 2}),
        }
