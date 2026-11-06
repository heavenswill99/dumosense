"""Temporary settings for isolated backend regression tests."""

from .settings import *

DATABASES["default"]["TEST"]["NAME"] = "test_dumosense_integration"
