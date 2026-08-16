from __future__ import annotations

EXPECTED = (1, 1, 2, 6, 4, 6, 3, 4)
LENGTHS = (5, 5, 5, 5, 4, 4, 3, 2)
TOTAL = 27


def validate_prize_groups(groups: dict[str, list[str]]) -> tuple[str, ...]:
    names = ('DB', 'G1', 'G2', 'G3', 'G4', 'G5', 'G6', 'G7')
    if tuple(groups) != names:
        raise ValueError('prize group names/order mismatch')
    flat: list[str] = []
    for name, count, width in zip(names, EXPECTED, LENGTHS):
        values = [str(v).strip() for v in groups[name]]
        if len(values) != count:
            raise ValueError(f'{name}: expected {count}, got {len(values)}')
        for value in values:
            if len(value) != width or not value.isdigit():
                raise ValueError(f'{name}: invalid {width}-digit prize {value!r}')
        flat.extend(values)
    if len(flat) != TOTAL:
        raise ValueError(f'expected {TOTAL} prizes, got {len(flat)}')
    return tuple(flat)


def tails27(full27: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    if len(full27) != TOTAL:
        raise ValueError('FULL_27 must contain exactly 27 prizes')
    return tuple(str(v)[-2:] for v in full27)
