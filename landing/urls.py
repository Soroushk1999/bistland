from django.urls import path

from landing.apis import LandingPageView, SubmitPhoneView


urlpatterns = [
    path("", LandingPageView.as_view(), name="landing-page"),
    path("submit", SubmitPhoneView.as_view(), name="submit_phone"),
]



