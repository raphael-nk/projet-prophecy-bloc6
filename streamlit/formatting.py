"""Formatage affichage (devise MGA, nombres FR)."""


def fmt_money_mga(n) -> str:
    """Montant en ariary malgache (MGA)."""
    try:
        x = float(n)
    except (TypeError, ValueError):
        return str(n)
    ax = abs(x)
    if ax >= 1_000_000_000:
        value = f"{x / 1_000_000_000:.1f}".rstrip("0").rstrip(".")
        return f"{value.replace('.', ',')} Md MGA"
    if ax >= 1_000_000:
        value = f"{x / 1_000_000:.1f}".rstrip("0").rstrip(".")
        return f"{value.replace('.', ',')} M MGA"
    if ax >= 1_000:
        value = f"{x / 1_000:.1f}".rstrip("0").rstrip(".")
        return f"{value.replace('.', ',')} k MGA"
    if x == int(x):
        return f"{int(x):,}".replace(",", " ") + " MGA"
    amount = f"{x:,.2f}".replace(",", " ").replace(".", ",")
    return f"{amount} MGA"
