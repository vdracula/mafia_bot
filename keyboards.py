class StatsManager:
    def __init__(self):
        self.total_games = 0
        self.wins = {"mafia": 0, "civilians": 0}

    def record_win(self, winner: str):
        self.total_games += 1
        if winner in self.wins:
            self.wins[winner] += 1
