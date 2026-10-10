from decimal import Decimal

from django import forms

from catalog.models import Exam

from .models import UserProfile

SCORE_RANGES = {
    Exam.Kind.PTE: (Decimal("10"), Decimal("90"), Decimal("1")),
    Exam.Kind.IELTS: (Decimal("0"), Decimal("9"), Decimal("0.5")),
}


class OnboardingForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ["display_name", "primary_exam", "target_score"]
        labels = {"primary_exam": "Exam you are preparing for"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["primary_exam"].queryset = Exam.objects.filter(is_active=True)
        self.fields["primary_exam"].required = True
        self.fields["primary_exam"].empty_label = None
        self.fields["target_score"].required = True

    def clean(self):
        cleaned = super().clean()
        exam, score = cleaned.get("primary_exam"), cleaned.get("target_score")
        if exam and score is not None and exam.kind in SCORE_RANGES:
            low, high, step = SCORE_RANGES[exam.kind]
            if not (low <= score <= high) or (score - low) % step:
                self.add_error(
                    "target_score",
                    f"{exam.name} targets go from {low} to {high} in steps of {step}.",
                )
        return cleaned
