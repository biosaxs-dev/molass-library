"""
    Mapping.Mapping.py
"""
class Mapping:
    def __init__(self, a, b):
        self.a = a
        self.b = b
    
    def __call__(self, x):
        return self.a * x + self.b
    
    def inv(self, y):
        return (y - self.b) / self.a
