import re
from rest_framework import serializers


PHONE_REGEX = re.compile(r"^\+989\d{9}$")


class SubmitPhoneSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=13)

    def validate_phone(self, value: str) -> str:
        value = value.strip()
        if not PHONE_REGEX.match(value):
            raise serializers.ValidationError("invalid_phone")
        return value
