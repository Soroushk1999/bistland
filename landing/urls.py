from django.urls import path
from .apis import SubmitPhoneView


urlpatterns = [
    path("submit", SubmitPhoneView.as_view(), name="submit_phone"),
]



