# levels.py

TEAM_LEVELS = [
    ("Oddiy", 0, 5), ("Bronza",6,20), ("Silver",21,80),
    ("Gold",81,200), ("Platina 1",201,350), ("Platina 2",351,600),
    ("Platina 3",601,1000), ("Platina 4",1001,1500), ("Platina 5",1501,2200),
    ("Platina 6",2201,4000), ("Diamond 1",4001,6500), ("Diamond 2",6501,10000),
    ("Diamond 3",10001,15000), ("Diamond 4",15001,25000), ("Diamond 5",25001,40000),
    ("Diamond 6",40001,float('inf'))
]

def get_team_level(member_count: int):
    for name, start, end in TEAM_LEVELS:
        if start <= member_count <= end:
            return name
    return TEAM_LEVELS[-1][0]


level = [
    ("Oddiy", 3, 1500),
    ("Bronza", 10, 1750),
    ("Silver", 50, 2250),
    ("Gold", 200, 2500),
    ("Platina 1", 350, 2000),
    ("Platina 2", 550, 2000),
    ("Platina 3", 800, 2000),
    ("Platina 4", 1100, 2000),
    ("Platina 5", 1500, 2000),
    ("Platina 6", 4000, 2000),
    ("Diamond 1", 10000, 2000),
    ("Diamond 2", 18000, 4000),
    ("Diamond 3", 28000, 4000),
    ("Diamond 4", 40000, 4000),
    ("Diamond 5", 60000, 4000),
    ("Diamond 6", float('inf'), 4000),
]


def get_level_by_refs(refs: int):
    for name, upper, per_ref in level:
        if refs < upper:
            return name, per_ref
    return level[-1][0], level[-1][2]


def get_total_earned_until_refs(refs: int):
    total, prev = 0, 0
    for name, upper, per_ref in level:
        if upper == float('inf'):
            total += max(0, refs - prev) * per_ref
            break
        else:
            total += max(0, min(refs, upper) - prev) * per_ref
            prev = upper
    return total
