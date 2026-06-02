# count-min-sketch

Count-Min Sketch probabilistic frequency estimator.
Answers "how many times did item X appear?" in O(1) with sub-linear space.
Guarantees: estimate >= true count, expected error <= ε·N with probability >= 1-δ.
Configurable via width (w = ⌈e/ε⌉) and depth (d = ⌈ln(1/δ)⌉).

## License
MIT
