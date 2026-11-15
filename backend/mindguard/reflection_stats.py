"""Summarize comparable self-reported ratings for one form version."""

from statistics import median


MIN_PRIOR_ANSWERS = 3
MAX_PRIOR_ANSWERS = 5


def summarize_ratings(questions, records):
    """Consume records newest first, with ties ordered by the caller."""
    history = {question: [] for question in questions}
    for recorded_at, answers in records:
        for answer in answers:
            question, value = answer["question"], answer["value"]
            if question not in history or type(value) is not int or not 1 <= value <= 5:
                continue
            samples = history[question]
            if len(samples) < 1 + MAX_PRIOR_ANSWERS and (
                not samples or recorded_at < samples[-1][0]
            ):
                samples.append((recorded_at, value))

        if all(len(samples) == 1 + MAX_PRIOR_ANSWERS for samples in history.values()):
            break

    items = []
    for question, samples in history.items():
        latest_at, latest_value = samples[0] if samples else (None, None)
        prior = samples[1:]
        baseline = median(value for _, value in prior) if len(prior) >= MIN_PRIOR_ANSWERS else None
        if baseline is not None:
            status = "comparison_available"
        elif samples:
            status = "insufficient_history"
        else:
            status = "missing_rating"
        items.append({
            "question": question,
            "latest_rating": latest_value,
            "latest_recorded_at": latest_at,
            "prior_count": len(prior),
            "prior_median": baseline,
            "difference_from_prior_median": latest_value - baseline if baseline is not None else None,
            "status": status,
        })
    return items
