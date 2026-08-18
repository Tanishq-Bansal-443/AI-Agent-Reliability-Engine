"""
conftest.py — shared pytest fixtures for all tests.
"""

import sys
import os
import pytest

# Add the project root to sys.path so tests can import packages
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
