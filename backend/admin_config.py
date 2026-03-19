import os


DEFAULT_ADMIN_EMAILS = {"vy2153166@gmail.com"}


def get_admin_emails() -> set[str]:
    """Danh sách email luôn có quyền admin."""
    raw_emails = os.getenv("ADMIN_EMAILS", "")
    emails = set(DEFAULT_ADMIN_EMAILS)

    for email in raw_emails.split(","):
        normalized = email.strip().lower()
        if normalized:
            emails.add(normalized)

    return emails


def is_bootstrap_admin_email(email: str | None) -> bool:
    """Kiểm tra email có nằm trong danh sách admin mặc định không."""
    if not email:
        return False
    return email.strip().lower() in get_admin_emails()
