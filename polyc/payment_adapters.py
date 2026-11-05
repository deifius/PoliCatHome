"""Provider-neutral settlement interfaces. All real-money integrations are DISABLED.

No provider SDK is imported, no credentials collected, no transfers attempted.
Source (receiving revenue), destination (paying contributors), and evidence
(reconciling statements) are different capabilities; do not infer one from another.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Literal, Protocol, Any


@dataclass(frozen=True)
class ProviderDeclaration:
    provider_id: str
    role: tuple[Literal['revenue_source','payout_destination','manual_evidence'],...]
    automated_money_movement_available_here: Literal[False] = False
    implementation_state: Literal['declaration_only'] = 'declaration_only'
    note: str = ''


# Descriptive capabilities, not a claim of current provider eligibility or API access.
PROVIDERS = (
    ProviderDeclaration('paypal',('revenue_source','payout_destination'),
                        note='Separate receipts and payout integrations; approvals and countries vary'),
    ProviderDeclaration('patreon',('revenue_source',),
                        note='Patronage statements; NOT assumed to pay distributed compute owners'),
    ProviderDeclaration('zelle_manual',('manual_evidence','payout_destination'),
                        note='Manual, bank-mediated settlement. No public bulk-payout API assumed'),
    ProviderDeclaration('bank_transfer_manual',('manual_evidence','payout_destination'),
                        note='Operator-entered confirmation, requires independent reconciliation'),
    ProviderDeclaration('stripe_connect',('revenue_source','payout_destination'),
                        note='Future connected-account integration, requires compliance review'),
    ProviderDeclaration('other',('manual_evidence',),
                        note='Custom registered adapter; no automatic money movement'),
)


class PaymentEvidenceAdapter(Protocol):
    """Future plugin contract; verification requires authentic provider data."""
    adapter_id: str

    def verify_revenue_event(self, provider_event: dict[str, Any]) -> dict[str, Any]: ...
    def reconcile_statement(self, statement_id: str) -> dict[str, Any]: ...


class PayoutAdapter(Protocol):
    """Future plugin contract. Never implement using unregulated custody by default."""
    adapter_id: str

    def quote_payout(self, recipient_ref: str, amount_minor: int, currency: str) -> dict[str, Any]: ...
    def request_payout(self, idempotency_key: str, recipient_ref: str,
                       amount_minor: int, currency: str) -> dict[str, Any]: ...
    def reconcile_payout(self, provider_payment_id: str) -> dict[str, Any]: ...


def catalogue():
    return {'schema':'polyc.payment-adapters/v0.3',
            'automatic_money_movement':False,
            'incoming_revenue_verification':False,
            'actual_payouts':False,
            'providers':[asdict(provider) for provider in PROVIDERS],
            'integration_notice':'Declaration capability only, NOT live PayPal/Zelle/Patreon connectivity.'}
