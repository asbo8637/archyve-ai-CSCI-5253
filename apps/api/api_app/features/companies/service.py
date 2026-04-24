from sqlalchemy.orm import Session

from archyve_common.models import Company


def create_company(session: Session, *, name: str) -> Company:
    normalized_name = name.strip()
    if not normalized_name:
        raise ValueError("A company name is required.")

    company = Company(name=normalized_name)
    session.add(company)
    session.flush()
    return company
