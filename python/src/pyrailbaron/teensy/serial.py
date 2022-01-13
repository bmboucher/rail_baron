from pyrailbaron.game.state import GameState
class Serial:
    @staticmethod
    def set_active_player(player_i: int, n_players: int):
        print(f'[SERIAL] ACTIVE {player_i + 1}/{n_players}')
        #TODO: Send instruction to blink player_i's LED

    @staticmethod
    def show_region(region: str):
        print(f'[SERIAL] SHOW_REGION {region}')
        #TODO: Send instruction to highlight region LEDs

    @staticmethod
    def show_home_city(pt_i: int):
        print(f'[SERIAL] SHOW_HOME {pt_i}')

    @staticmethod
    def show_destination(start_i: int, dest_i: int):
        print(f'[SERIAL] SHOW_DEST {dest_i} (from {start_i})')

    @staticmethod
    def update_bank_amounts(s: GameState):
        print(f'[SERIAL] SET_BANK {",".join(str(p.bank) for p in s.players)}')

    @staticmethod
    def update_owners(s: GameState):
        for i, ps in enumerate(s.players):
            prefix = f'[SERIAL] SET_OWNED {i}'
            if len(ps.rr_owned) == 0:
                print(f'{prefix} EMPTY')
            else:
                print(f'{prefix} {" ".join(ps.rr_owned)}')