from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class ProrationItem:
    description: str
    amount_minor: int  # positive = charge, negative = credit


@dataclass(frozen=True)
class ProrationCalculation:
    unused_credit_minor: int       # positive number representing credit owed to customer
    remaining_charge_minor: int    # positive number representing charge for new plan
    net_amount_due_minor: int      # net amount customer pays right now (can be 0 or credit)
    line_items: list[ProrationItem]


def calculate_proration(
    old_plan_name: str,
    old_plan_price_minor: int,
    new_plan_name: str,
    new_plan_price_minor: int,
    period_start: datetime,
    period_end: datetime,
    change_at: datetime,
) -> ProrationCalculation:
    """
    Calculate proration credit for unused time on old plan
    and charge for remaining time on new plan.
    All calculations are done in integer minor units (paise) with second-level precision.
    """
    # 1. Validate timezone-awareness
    if period_start.tzinfo is None or period_end.tzinfo is None or change_at.tzinfo is None:
        raise ValueError("All datetimes must be timezone-aware (UTC)")

    # 2. Total duration of the current billing cycle in seconds
    total_seconds = (period_end - period_start).total_seconds()
    if total_seconds <= 0:
        raise ValueError("period_end must be strictly after period_start")

    # 3. Clamp change_at within [period_start, period_end]
    effective_change = max(period_start, min(change_at, period_end))

    # 4. Seconds remaining in the billing period
    remaining_seconds = (period_end - effective_change).total_seconds()

    # Fraction of the billing cycle remaining (0.0 to 1.0)
    fraction_remaining = remaining_seconds / total_seconds

    # 5. Calculate integer minor amounts with round()
    unused_credit = round(old_plan_price_minor * fraction_remaining)
    remaining_charge = round(new_plan_price_minor * fraction_remaining)

    # 6. Net amount due (charge minus credit)
    net_amount = remaining_charge - unused_credit

    # 7. Generate itemized line items
    line_items: list[ProrationItem] = []

    if remaining_charge > 0:
        line_items.append(
            ProrationItem(
                description=f"Prorated charge for {new_plan_name} (remaining cycle)",
                amount_minor=remaining_charge,
            )
        )

    if unused_credit > 0:
        line_items.append(
            ProrationItem(
                description=f"Unused time credit for {old_plan_name}",
                amount_minor=-unused_credit,  # negative represents credit
            )
        )

    return ProrationCalculation(
        unused_credit_minor=unused_credit,
        remaining_charge_minor=remaining_charge,
        net_amount_due_minor=net_amount,
        line_items=line_items,
    )