# hyperloglog-sketch

HyperLogLog++ cardinality estimator.
Estimates the number of distinct elements in a stream using O(m) space
where m = 2^precision registers. Typical error: ~1.04/sqrt(m).
Supports merge for distributed cardinality counting.

## License
MIT
