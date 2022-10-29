import random
from .io import CSource

class Pipeline:
    
    def __init__(self, seed: int = None, *args):
        if seed is not None:
            random.seed(seed)
        self.buffer = list(args)
    
    def process(self, source: CSource):
        pass # TODO