class MultiValue:
    def __init__(self, *values):
        self.values = set(values)

    def __eq__(self, other):
        if isinstance(other, str):
            return other in self.values
        return False


LPS = MultiValue("LPS", "left-posterior-superior")
