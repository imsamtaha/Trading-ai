from app.customer.service import CustomerService


class FakeRepository:
    def __init__(self):
        self.rows = {}
        self.upserts = []

    def upsert_account(self, row):
        self.upserts.append(dict(row))
        self.rows[(row["customer_id"], row["account_id"])] = dict(row)
        return dict(row)

    def get_account(self, customer_id, account_id):
        row = self.rows.get((customer_id, account_id))
        return dict(row) if row else None


def test_register_account_persists_ownership_mapping():
    repo = FakeRepository()
    service = CustomerService(repository=repo)
    service.register_account("c1", "a1", tier="PRO", auth_subject="subject-1")
    assert repo.upserts[-1]["auth_subject"] == "subject-1"
    assert repo.upserts[-1]["mode"] == "LIVE_DEMO"


def test_authorize_rehydrates_account_from_repository_after_restart():
    repo = FakeRepository()
    repo.rows[("c1", "a1")] = {
        "customer_id": "c1", "account_id": "a1", "tier": "ELITE",
        "mode": "LIVE_DEMO", "auth_subject": "subject-1",
    }
    service = CustomerService(repository=repo)
    account = service.authorize("c1", "a1", auth_subject="subject-1")
    assert account["tier"] == "ELITE"
    assert service.accounts[("c1", "a1")]["auth_subject"] == "subject-1"
