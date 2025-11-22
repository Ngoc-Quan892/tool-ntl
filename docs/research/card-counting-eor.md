# Card Counting EOR (Effect of Removal)

## Overview

EOR values represent how removing a specific card affects the probability of Banker winning.

## Calculation Method

EOR is calculated using combinatorial analysis of all possible card combinations.

## Values

See `baccarat-mathematics.md` for complete EOR table.

## Implementation

- Track cards as they're drawn
- Update running count
- Calculate true count based on remaining decks
- Convert to edge percentage

## Edge Calculation

```
Edge = True Count × 0.005
```

This gives the approximate percentage advantage.

