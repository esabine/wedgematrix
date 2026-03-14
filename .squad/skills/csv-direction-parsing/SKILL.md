# CSV Direction Parsing

## Pattern
Golf launch monitor CSVs use R/L prefixes for directional values: `R8.5` = 8.5° right, `L3.2` = -3.2° left.

## Implementation
```python
def parse_direction(value):
    value = str(value).strip()
    if not value or value.lower() == 'nan':
        return None
    if value.startswith('R'):
        return float(value[1:])
    elif value.startswith('L'):
        return -float(value[1:])
    else:
        return float(value)
```

## Edge Cases
- `0.0` with no prefix → 0.0
- `NaN` string → None
- `L0.0` → -0.0 (treated as 0)
- Empty string → None

## Applies To
`launch_direction`, `spin_axis`, `club_path`, `face_angle`, `offline`, `back_spin`, `side_spin`
