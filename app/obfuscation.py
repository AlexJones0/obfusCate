import random
from typing import Iterable, Optional
from ctypes import Union
from .io import CSource
from abc import ABC, abstractmethod


class ObfuscationUnit(ABC):
    
    name = "ObfuscationUnit"
    description = "An abstract base class representing some obfuscation transformation unit"

    @abstractmethod
    def transform(self, source: CSource) -> Optional[CSource]:
        return NotImplemented
    
    @abstractmethod
    def get_cli() -> Optional['ObfuscationUnit']:
        return NotImplemented

    @abstractmethod
    def __eq__(self, other: 'ObfuscationUnit') -> bool:
        return True
    
    @abstractmethod
    def __str__(self):
        return "ObfuscationUnit()"

    """
    @abstractmethod
    def __add__(self, other: Union['ObfuscationUnit', Iterable['ObfuscationUnit']]) -> 'ObfuscationUnit':
        if isinstance(other, ObfuscationUnit):
            return list((self, other))
        else:
            return list(other).append(self) # TODO check not sure this works like I think it does
    """
    
class Pipeline:

    def __init__(self, seed: int = None, *args):
        if seed is not None:
            random.seed(seed)
        self.transforms = list(args)

    def add(self, transform: ObfuscationUnit):
        self.transforms.append(transform)

    def process(self, source: CSource):
        if source is None:
            return None
        for t in self.transforms:
            source = t.transform(source)
            if source is None:
                break
        return source
        

class IdentityUnit(ObfuscationUnit):
    
    name = "Identity"
    description = "Does nothing - returns the same code entered."
    
    def transform(self, source: CSource) -> Optional[CSource]:
        return source
    
    def get_cli() -> Optional['IdentityUnit']:
        return IdentityUnit()

    def __eq__(self, other: ObfuscationUnit) -> bool:
        return isinstance(other, IdentityUnit)
    
    def __str__(self):
        return "Identity()"