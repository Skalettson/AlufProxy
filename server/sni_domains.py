"""
SNI Domains Database for XRay Reality
Актуально на 16.03.2026

Содержит 100+ доменов с приоритетами для отказоустойчивой конфигурации Reality.
Домены разделены по категориям для оптимального выбора.

Требования к домену для Reality:
- Поддержка TLS 1.3
- Поддержка X25519
- Поддержка HTTP/2 (H2)
- Доступность из России (опционально)
"""

# Приоритет 5⭐ - Максимальный приоритет (технологические гиганты, CDN)
PRIORITY_5 = [
    # Microsoft
    "www.microsoft.com",
    "microsoft.com",
    "cdn-dynmedia-1.microsoft.com",
    "software.download.prss.microsoft.com",
    
    # Apple
    "www.apple.com",
    "apple.com",
    "gateway.icloud.com",
    "itunes.apple.com",
    "swdist.apple.com",
    "swcdn.apple.com",
    "updates.cdn-apple.com",
    "mensura.cdn-apple.com",
    "osxapps.itunes.apple.com",
    "aod.itunes.apple.com",
    "www.icloud.com",
    
    # NVIDIA
    "www.nvidia.com",
    "nvidia.com",
    "academy.nvidia.com",
    
    # Cisco
    "www.cisco.com",
    "cisco.com",
    
    # AMD
    "www.amd.com",
    "amd.com",
    
    # Intel
    "www.intel.com",
    "intel.com",
    
    # IBM
    "www.ibm.com",
    "ibm.com",
    
    # Oracle
    "www.oracle.com",
    "oracle.com",
    
    # Adobe
    "www.adobe.com",
    "adobe.com",
    
    # Salesforce
    "www.salesforce.com",
    "salesforce.com",
    
    # SAP
    "www.sap.com",
    "sap.com",
]

# Приоритет 4⭐ - Высокий приоритет (европейские, азиатские, стриминговые)
PRIORITY_4 = [
    # Великобритания
    "www.bbc.co.uk",
    "bbc.co.uk",
    "www.theguardian.com",
    "theguardian.com",
    "www.telegraph.co.uk",
    "telegraph.co.uk",
    "www.sky.com",
    "sky.com",
    "www.gov.uk",
    "gov.uk",
    
    # Германия
    "www.spiegel.de",
    "spiegel.de",
    "www.bild.de",
    "bild.de",
    
    # Франция
    "www.lemonde.fr",
    "lemonde.fr",
    "www.lefigaro.fr",
    "lefigaro.fr",
    
    # Испания
    "www.elmundo.es",
    "elmundo.es",
    "www.elpais.com",
    "elpais.com",
    
    # Италия
    "www.corriere.it",
    "corriere.it",
    "www.repubblica.it",
    "repubblica.it",
    
    # Нидерланды
    "www.nos.nl",
    "nos.nl",
    "www.nu.nl",
    "nu.nl",
    
    # Швейцария
    "www.srf.ch",
    "srf.ch",
    
    # Швеция
    "www.svt.se",
    "svt.se",
    
    # Норвегия
    "www.nrk.no",
    "nrk.no",
    
    # Дания
    "www.dr.dk",
    "dr.dk",
    
    # Япония
    "www.nhk.or.jp",
    "nhk.or.jp",
    "www.asahi.com",
    "asahi.com",
    
    # Корея
    "www.kbs.co.kr",
    "kbs.co.kr",
    "www.sbs.co.kr",
    "sbs.co.kr",
    
    # Стриминговые
    "www.netflix.com",
    "netflix.com",
    "www.spotify.com",
    "spotify.com",
    "www.disneyplus.com",
    "disneyplus.com",
    "www.primevideo.com",
    "primevideo.com",
    "www.twitch.tv",
    "twitch.tv",
    
    # Социальные сети
    "www.linkedin.com",
    "linkedin.com",
    "www.pinterest.com",
    "pinterest.com",
    "www.reddit.com",
    "reddit.com",
    "www.tiktok.com",
    "tiktok.com",
    "www.telegram.org",
    "telegram.org",
    "www.whatsapp.com",
    "whatsapp.com",
]

# Приоритет 3⭐ - Средний приоритет (РФ домены, e-commerce, финансовые)
PRIORITY_3 = [
    # Российские государственные
    "www.gosuslugi.ru",
    "gosuslugi.ru",
    "www.gov.ru",
    "gov.ru",
    "www.kremlin.ru",
    "kremlin.ru",
    "www.government.ru",
    "government.ru",
    "www.mos.ru",
    "mos.ru",
    
    # Российские банки
    "www.sberbank.ru",
    "sberbank.ru",
    "www.vtb.ru",
    "vtb.ru",
    "www.tinkoff.ru",
    "tinkoff.ru",
    "www.alfabank.ru",
    "alfabank.ru",
    "www.gazprombank.ru",
    "gazprombank.ru",
    
    # Российские телекомы
    "www.mts.ru",
    "mts.ru",
    "www.beeline.ru",
    "beeline.ru",
    "www.megafon.ru",
    "megafon.ru",
    "www.tele2.ru",
    "tele2.ru",
    
    # Российские компании
    "www.gazprom.ru",
    "gazprom.ru",
    "www.rzd.ru",
    "rzd.ru",
    "www.pochta.ru",
    "pochta.ru",
    "www.aeroflot.ru",
    "aeroflot.ru",
    
    # Российские IT
    "www.yandex.ru",
    "yandex.ru",
    "www.mail.ru",
    "mail.ru",
    "www.vk.com",
    "vk.com",
    "www.ok.ru",
    "ok.ru",
    "www.rambler.ru",
    "rambler.ru",
    
    # Российские СМИ
    "www.lenta.ru",
    "lenta.ru",
    "www.kommersant.ru",
    "kommersant.ru",
    "www.rbc.ru",
    "rbc.ru",
    "www.tass.ru",
    "tass.ru",
    "www.ria.ru",
    "ria.ru",
    "www.interfax.ru",
    "interfax.ru",
    
    # Российские маркетплейсы
    "www.wildberries.ru",
    "wildberries.ru",
    "www.ozon.ru",
    "ozon.ru",
    
    # E-commerce международные
    "www.amazon.com",
    "amazon.com",
    "www.ebay.com",
    "ebay.com",
    "www.aliexpress.com",
    "aliexpress.com",
    "www.alibaba.com",
    "alibaba.com",
    "www.walmart.com",
    "walmart.com",
    "www.target.com",
    "target.com",
    "www.ikea.com",
    "ikea.com",
    "www.nike.com",
    "nike.com",
    "www.adidas.com",
    "adidas.com",
    
    # Финансовые
    "www.visa.com",
    "visa.com",
    "www.mastercard.com",
    "mastercard.com",
    "www.paypal.com",
    "paypal.com",
    "www.stripe.com",
    "stripe.com",
    "www.swift.com",
    "swift.com",
    "www.bloomberg.com",
    "bloomberg.com",
    "www.reuters.com",
    "reuters.com",
    "www.cnbc.com",
    "cnbc.com",
    "www.ft.com",
    "ft.com",
    "www.wsj.com",
    "wsj.com",
]

# Приоритет 2⭐ - CDN и облачные провайдеры
PRIORITY_2 = [
    # CDN
    "www.cloudflare.com",
    "cloudflare.com",
    "www.fastly.com",
    "fastly.com",
    "www.akamai.com",
    "akamai.com",
    
    # Cloud провайдеры
    "www.aws.amazon.com",
    "aws.amazon.com",
    "www.azure.microsoft.com",
    "azure.microsoft.com",
    "www.cloud.google.com",
    "cloud.google.com",
    "www.linode.com",
    "linode.com",
    "www.digitalocean.com",
    "digitalocean.com",
    "www.vultr.com",
    "vultr.com",
    "www.hetzner.com",
    "hetzner.com",
    "www.ovh.com",
    "ovh.com",
]

# Приоритет 1⭐ - Образовательные (редко блокируются)
PRIORITY_1 = [
    # Википедия
    "www.wikipedia.org",
    "wikipedia.org",
    
    # Образовательные платформы
    "www.khanacademy.org",
    "khanacademy.org",
    "www.coursera.org",
    "coursera.org",
    "www.edx.org",
    "edx.org",
    "www.udemy.com",
    "udemy.com",
    
    # Университеты
    "www.mit.edu",
    "mit.edu",
    "www.harvard.edu",
    "harvard.edu",
    "www.stanford.edu",
    "stanford.edu",
    "www.ox.ac.uk",
    "ox.ac.uk",
    "www.cam.ac.uk",
    "cam.ac.uk",
    "www.yale.edu",
    "yale.edu",
    "www.princeton.edu",
    "princeton.edu",
    "www.columbia.edu",
    "columbia.edu",
    "www.berkeley.edu",
    "berkeley.edu",
    "www.caltech.edu",
    "caltech.edu",
]

# Все домены в одном словаре
ALL_DOMAINS = {
    "priority_5": PRIORITY_5,
    "priority_4": PRIORITY_4,
    "priority_3": PRIORITY_3,
    "priority_2": PRIORITY_2,
    "priority_1": PRIORITY_1,
}

# РФ домены (отдельно для локального использования)
RF_DOMAINS = PRIORITY_3[:50]  # Первые 50 - это в основном РФ

# Международные домены
INTERNATIONAL_DOMAINS = PRIORITY_5 + PRIORITY_4 + PRIORITY_2 + PRIORITY_1

# Домены для быстрой проверки (топ-20)
QUICK_CHECK_DOMAINS = [
    "www.microsoft.com",
    "www.apple.com",
    "gateway.icloud.com",
    "www.nvidia.com",
    "www.netflix.com",
    "www.gosuslugi.ru",
    "www.sberbank.ru",
    "www.yandex.ru",
    "www.wikipedia.org",
    "www.cloudflare.com",
    "www.bbc.co.uk",
    "www.spiegel.de",
    "www.nhk.or.jp",
    "www.amazon.com",
    "www.visa.com",
    "www.mit.edu",
    "www.cisco.com",
    "www.adobe.com",
    "www.telegram.org",
    "www.spotify.com",
]


def get_domains_by_priority(priority: int = 5) -> list:
    """
    Получить список доменов по приоритету.
    
    Args:
        priority: Приоритет от 1 до 5
        
    Returns:
        Список доменов
    """
    return ALL_DOMAINS.get(f"priority_{priority}", [])


def get_all_domains() -> list:
    """
    Получить все домены плоским списком.
    
    Returns:
        Список всех доменов
    """
    domains = []
    for domain_list in ALL_DOMAINS.values():
        domains.extend(domain_list)
    return domains


def get_unique_domains() -> list:
    """
    Получить уникальные домены (без дубликатов).
    
    Returns:
        Список уникальных доменов
    """
    return list(set(get_all_domains()))


def get_domain_count() -> dict:
    """
    Получить количество доменов по приоритетам.
    
    Returns:
        Словарь с количеством доменов
    """
    return {
        priority: len(domains)
        for priority, domains in ALL_DOMAINS.items()
    }


if __name__ == "__main__":
    print("=" * 60)
    print("  SNI Domains Database for XRay Reality")
    print("  Актуально на 16.03.2026")
    print("=" * 60)
    print()
    
    counts = get_domain_count()
    total = sum(counts.values())
    
    print(f"Всего доменов: {total}")
    print()
    print("По приоритетам:")
    for priority, count in counts.items():
        print(f"  {priority}: {count} доменов")
    print()
    print(f"Уникальных доменов: {len(get_unique_domains())}")
    print()
    print(f"РФ доменов: {len(RF_DOMAINS)}")
    print(f"Международных доменов: {len(INTERNATIONAL_DOMAINS)}")
    print()
    print(f"Доменов для быстрой проверки: {len(QUICK_CHECK_DOMAINS)}")
