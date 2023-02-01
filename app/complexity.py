""" File: complexity.py
Implements classes and functions for handling input and output. """
from app import settings as config
from .interaction import CSource
from abc import ABC, abstractmethod
from typing import Iterable, Any


class CodeMetricUnit(ABC):
    """An abstract base class representing some code complexity metric unit, such that
    any implemented code metrics will be subclasses of this class. Implements methods
    for calculating and formatting these complexity metrics given some code. """
    
    @abstractmethod
    def calculate_metric(self, source: CSource) -> None:
        return NotImplemented 
    
    @abstractmethod
    def calculate_metric(self, old_source: CSource, new_source: CSource) -> None:
        return NotImplemented
    
    @abstractmethod
    def get_metrics(self) -> Iterable[Any]:
        return NotImplemented