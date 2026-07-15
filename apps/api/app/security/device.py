"""Device/browser/OS extraction for session records, and client IP resolution."""

from fastapi import Request
from user_agents import parse as parse_user_agent


def build_device_info(user_agent: str | None) -> dict[str, str | bool]:
    if not user_agent:
        return {}
    ua = parse_user_agent(user_agent)
    return {
        "browser": ua.browser.family,
        "browser_version": ua.browser.version_string,
        "os": ua.os.family,
        "os_version": ua.os.version_string,
        "device": ua.device.family,
        "is_mobile": ua.is_mobile,
        "is_tablet": ua.is_tablet,
        "is_pc": ua.is_pc,
        "is_bot": ua.is_bot,
    }


def get_client_ip(request: Request) -> str | None:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None
