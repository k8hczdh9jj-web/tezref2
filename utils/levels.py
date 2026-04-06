# levels.py

LEVEL_NAMES = [
    "Oddiy",
    "Bronza",
    "Silver",
    "Gold",
    "Platina 1",
    "Platina 2",
    "Platina 3",
    "Platina 4",
    "Platina 5",
    "Platina 6",
    "Diamond 1",
    "Diamond 2",
    "Diamond 3",
    "Diamond 4",
    "Diamond 5",
    "Diamond 6",
]

# Referral oralig'i o'zgarmaydi (oldingi mantiq saqlandi)
REFERRAL_UPPER_BOUNDS = [
    3,
    10,
    50,
    200,
    350,
    550,
    800,
    1100,
    1500,
    4000,
    10000,
    18000,
    28000,
    40000,
    60000,
    float("inf"),
]

# Guruhga odam qo'shish oralig'i (siz bergan qoidaga mos)
GROUP_UPPER_BOUNDS = [
    10,
    30,
    60,
    120,
    240,
    480,
    960,
    1920,
    3840,
    7680,
    15360,
    30720,
    61440,
    122880,
    245760,
    float("inf"),
]


def _bonus_by_level_index(index: int) -> int:
    # 1-daraja 800, Goldgacha +50, Platina va Diamond bosqichlarida +100
    if index <= 3:
        return 800 + (index * 50)
    return 1050 + ((index - 4) * 100)


LEVEL_BONUSES = [_bonus_by_level_index(i) for i in range(len(LEVEL_NAMES))]


def _level_index_by_value(value: int, upper_bounds: list) -> int:
    for i, upper in enumerate(upper_bounds):
        if value < upper:
            return i
    return len(upper_bounds) - 1


def get_level_by_refs(refs: int):
    idx = _level_index_by_value(refs, REFERRAL_UPPER_BOUNDS)
    return LEVEL_NAMES[idx], LEVEL_BONUSES[idx]


def get_level_by_group_adds(group_adds: int):
    idx = _level_index_by_value(group_adds, GROUP_UPPER_BOUNDS)
    return LEVEL_NAMES[idx], LEVEL_BONUSES[idx]


def get_combined_level(refs: int, group_adds: int) -> str:
    ref_idx = _level_index_by_value(refs, REFERRAL_UPPER_BOUNDS)
    group_idx = _level_index_by_value(group_adds, GROUP_UPPER_BOUNDS)
    return LEVEL_NAMES[max(ref_idx, group_idx)]


def get_total_earned_until_refs(refs: int):
    total = 0
    prev = 0
    for i, upper in enumerate(REFERRAL_UPPER_BOUNDS):
        per_ref = LEVEL_BONUSES[i]
        if upper == float("inf"):
            total += max(0, refs - prev) * per_ref
            break

        total += max(0, min(refs, upper) - prev) * per_ref
        prev = upper
    return total
