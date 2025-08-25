"""
Model name utilities for handling progress markers via model suffix.

This module provides utilities for parsing model names to determine
whether progress markers should be shown based on the -progress suffix.
"""

from typing import Tuple
import logging

logger = logging.getLogger(__name__)


class ModelUtils:
    """Utilities for handling model names and progress markers."""
    
    @classmethod
    def extract_progress_flag(cls, model: str) -> Tuple[str, bool]:
        """Extract progress flag from model name.
        
        Args:
            model: Model name potentially ending with -progress
            
        Returns:
            Tuple of (base model name, has progress flag)
        """
        if model.endswith("-progress"):
            return model[:-9], True
        return model, False
