from decimal import Decimal


def calculate_progress(
    first_amount,
    latest_amount,
    first_target,
    latest_target,
):
    first_amount = Decimal(str(first_amount))
    latest_amount = Decimal(str(latest_amount))
    first_target = Decimal(str(first_target))
    latest_target = Decimal(str(latest_target))

    return {
        "amount_change": latest_amount - first_amount,
        "target_change": latest_target - first_target,
    }