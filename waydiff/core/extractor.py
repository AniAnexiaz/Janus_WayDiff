import re
from bs4 import BeautifulSoup


# ==========================================================
# URL NORMALIZATION
# ==========================================================

def normalize_url(url: str) -> str:
    return url.strip().lower().rstrip("/")


# ==========================================================
# SECURITY HEADER EXTRACTION
# ==========================================================

def extract_security_headers(headers: dict | None):
    """
    Extract only security-relevant headers for drift analysis.
    """

    if not headers:
        return {}

    normalized = {k.lower(): v for k, v in headers.items()}

    relevant_headers = [
        "content-security-policy",
        "strict-transport-security",
        "x-frame-options",
        "x-content-type-options",
        "referrer-policy",
        "permissions-policy",
        "server",
        "set-cookie"
    ]

    extracted = {}

    for key in relevant_headers:
        if key in normalized:
            extracted[key] = normalized[key]

    return extracted


# ==========================================================
# HTML SECURITY SURFACE EXTRACTION
# ==========================================================

def extract_security_surface(html_lines, headers=None):
    """
    Extract attack surface elements from HTML.
    Optionally include extracted security headers.
    """

    html = "\n".join(html_lines)
    soup = BeautifulSoup(html, "lxml")

    surface = {
        "authentication_routes": set(),
        "admin_routes": set(),
        "api_routes": set(),
        "query_parameters": set(),
        "forms": [],
        "hidden_fields": set(),
        "sensitive_inputs": [],
        "file_inputs": [],
        "external_scripts": set(),
        "client_fetch_calls": set(),
        "business_logic_indicators": set(),
        "security_headers": {}
    }

    # --------------------------
    # ROUTES
    # --------------------------

    for tag in soup.find_all(["a", "form"]):
        raw_url = tag.get("href") or tag.get("action")
        if not raw_url:
            continue

        url = normalize_url(raw_url)
        lower = url

        # Query parameters
        if "?" in url:
            params = url.split("?", 1)[1]
            for p in params.split("&"):
                surface["query_parameters"].add(p.split("=")[0].lower())

        # Authentication routes
        if any(k in lower for k in ["login", "logout", "reset", "oauth", "callback", "token", "mfa", "sso"]):
            surface["authentication_routes"].add(url)

        # Admin routes
        if any(k in lower for k in ["admin", "dashboard", "internal", "debug"]):
            surface["admin_routes"].add(url)

        # API routes
        if "/api" in lower:
            surface["api_routes"].add(url)

    # --------------------------
    # FORMS
    # --------------------------

    for form in soup.find_all("form"):
        form_data = {
            "action": form.get("action"),
            "method": (form.get("method") or "GET").upper(),
            "input_names": []
        }

        for inp in form.find_all("input"):
            name = inp.get("name")
            itype = (inp.get("type") or "text").lower()

            if name:
                name_lower = name.lower()
                form_data["input_names"].append(name_lower)

                if itype == "hidden":
                    surface["hidden_fields"].add(name_lower)

                if any(k in name_lower for k in ["price", "amount", "role", "plan", "discount", "tier"]):
                    surface["business_logic_indicators"].add(name_lower)

            if itype == "password":
                surface["sensitive_inputs"].append({"type": "password", "name": name})

            if itype == "file":
                surface["file_inputs"].append({"name": name})

        surface["forms"].append(form_data)

    # --------------------------
    # SCRIPTS
    # --------------------------

    for script in soup.find_all("script"):
        if script.get("src"):
            surface["external_scripts"].add(script.get("src"))

        if script.string:
            js = script.string.lower()
            for match in re.findall(r"fetch\(['\"](.*?)['\"]", js):
                surface["client_fetch_calls"].add(match)

    # --------------------------
    # SECURITY HEADERS
    # --------------------------

    surface["security_headers"] = extract_security_headers(headers)

    # Convert sets to lists
    return {
        k: list(v) if isinstance(v, set) else v
        for k, v in surface.items()
    }