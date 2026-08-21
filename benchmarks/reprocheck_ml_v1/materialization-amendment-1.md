# Materialization amendment 1

The first execution stopped on the first selected GitHub blob, before any corpus was
written. GitHub's documented Base64 response wraps the encoded content with newline
characters. The preregistered transport adapter incorrectly used strict Base64 validation
without first removing JSON-string whitespace.

This amendment removes ASCII whitespace from the encoded transport string before strict
decoding. It does not change repository inclusion, artifact selection, ordering, size
limits, content eligibility, or any analysis rule. A new registration must be committed
and published before execution resumes.
