from seo_platform.config import get_settings
settings = get_settings()
print(f"TEMPORAL_NAMESPACE={settings.temporal.namespace}")
