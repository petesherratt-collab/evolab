# Generator `generated-0.3` audit

**Status:** passed for engineering use; not approved for exploratory evaluation
**Cases checked:** 3,000 (1,000 per task-class label)
**Unique fingerprints:** 3,000

## Balance

Each truth label occurred exactly 600 times, including `none_of_the_above`. Each displayed correct-answer position from zero through four also occurred exactly 600 times. This removes the label leak found in version `generated-0.2.1`.

## Mechanical checks

- exact evidence-role composition: 8 direct, 4 relational, 3 redundant, 3 misleading, 2 irrelevant;
- no individual clue formally isolates the true candidate;
- no ordinary pair of direct, relational, or redundant clues formally isolates truth;
- relational mappings are symmetric and each pair contains complementary phase markers;
- designated sufficient sets contain at least three clues, span multiple regions, and cost at most 60;
- designated solutions are neither cheap-only nor expensive-only;
- coordination traps have a multi-region verification set costing at most 20;
- deterministic regeneration and unique task fingerprints.

## Remaining limitations

The three task-class labels still share too much underlying template structure, and the difficulty label does not yet produce a sufficiently distinct mechanical difficulty manipulation. Wording diversity, formal hidden causal graphs, split derivation, and a rejection archive also remain to be implemented before any 30-task evaluation.
