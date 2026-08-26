You are evaluating a review comment classifier.

For each review comment in the LLM output, classify the verdict as:
- valid: the comment is clearly supported by the ticket content.
- borderline: the comment is interpretable but somewhat over-extended.
- invalid: the comment is not supported by the ticket content.

Also list categories that the LLM missed.
Return JSON with `judgments`, `missed_categories`, and `overall_verdict`.
