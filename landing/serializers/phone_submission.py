import re
from rest_framework import serializers


PHONE_REGEX = re.compile(r"^\+?[0-9]{10,15}$")


class SubmitPhoneSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=20)

    def validate_phone(self, value: str) -> str:
        value = value.strip()
        if not PHONE_REGEX.match(value):
            raise serializers.ValidationError("invalid_phone")
        return value
