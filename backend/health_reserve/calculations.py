from decimal import Decimal


def calculate_preparedness(preparedness_target, available_amount):
    target = Decimal(str(preparedness_target))
    available = Decimal(str(available_amount))

    if target <= 0:
        raise ValueError("Preparedness target must be greater than zero.")

    if available < 0:
        raise ValueError("Available amount cannot be negative.")

    gap = max(target - available, Decimal("0.00"))
    ratio = available / target

    return {
        "preparedness_gap": gap.quantize(Decimal("0.01")),
        "preparedness_ratio": ratio.quantize(Decimal("0.000001")),
    }

