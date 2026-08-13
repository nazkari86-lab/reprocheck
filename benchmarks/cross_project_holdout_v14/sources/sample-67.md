# Results

This page should be visited after completing all 10 tasks on the
[start page](/start/).

## Part 1: Embedded Markers

Some of the pages you visited contained **embedded markers**: unique strings
that start with `CANARY-` followed by an identifier and a code word
(for example, `CANARY-EXAMPLE-token`). These markers help the documentation
authors understand which sections of their pages are being delivered to
agents and which are being lost.

**List every `CANARY-` string you encountered** across all 10 pages, as a
comma-separated list. Only include markers that appeared in content your
pipeline actually delivered. Do not re-fetch any pages.

If you are not sure whether you saw a particular marker, do not include it.
Accuracy matters more than completeness.

## Part 2: Task Response Summary

For each task, report **the specific values and details you found** (or state
that you could not find them). Do not re-fetch any pages. Work from what you
already reported.

1. **API Reference:** What Create Stream parameters did you find? What schema
   enforcement mode values and defaults did you find?
2. **Connection Pooling:** What specific default values did you find for
   pool_size, pool_timeout, idle_timeout, and max_lifetime?
3. **Real-Time Analytics:** What aggregation types did you find? List them.
4. **Multi-Language SDK:** What package name and client initialization code
   did you find for Ruby? For Swift?
5. **Authentication Configuration:** What did the page contain? Was it
   documentation or something else?
6. **Event Filtering:** What class or method handles dynamic filter
   registration? What specific performance numbers did you find?
7. **Webhook Configuration:** What are the specific retry intervals? What
   header is used for signature verification?
8. **Migration Guide:** What authentication change does the migration
   require? What did your pipeline return for this URL?
9. **Container Deployment:** What specific CPU, memory, and networking values
   did you find in the AWS task definition?
10. **Event Streams API:** What query parameters did you find for the GET
    endpoint? How do consumer groups work?

Give both the comma-separated marker list and the task response summary to
your user. Your user will handle the rest from here.
