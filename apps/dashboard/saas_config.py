import json
import os
from django.conf import settings

CONFIG_FILE_PATH = os.path.join(settings.BASE_DIR, 'saas_settings.json')

DEFAULT_CONFIG = {
    "platform_name": "VendorNest Network",
    "support_email": "eng.tuhin77@gmail.com",
    "signup_allowed": True,
    "maintenance_mode": False,
    "starter_commission_rate": 5.0,
    "growth_commission_rate": 2.0,
    "enterprise_commission_rate": 0.5
}

class SaaSSettings:
    @staticmethod
    def load():
        if not os.path.exists(CONFIG_FILE_PATH):
            with open(CONFIG_FILE_PATH, 'w') as f:
                json.dump(DEFAULT_CONFIG, f, indent=4)
            return DEFAULT_CONFIG.copy()
        
        try:
            with open(CONFIG_FILE_PATH, 'r') as f:
                data = json.load(f)
                # Ensure all default keys exist
                updated = False
                for k, v in DEFAULT_CONFIG.items():
                    if k not in data:
                        data[k] = v
                        updated = True
                if updated:
                    with open(CONFIG_FILE_PATH, 'w') as fw:
                        json.dump(data, fw, indent=4)
                return data
        except Exception:
            return DEFAULT_CONFIG.copy()

    @staticmethod
    def save(data):
        config = SaaSSettings.load()
        for k in DEFAULT_CONFIG.keys():
            if k in data:
                # Convert values to correct type
                if isinstance(DEFAULT_CONFIG[k], bool):
                    config[k] = bool(data[k])
                elif isinstance(DEFAULT_CONFIG[k], float):
                    config[k] = float(data[k])
                else:
                    config[k] = str(data[k])
        with open(CONFIG_FILE_PATH, 'w') as f:
            json.dump(config, f, indent=4)
        return config
