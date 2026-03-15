# -------------------------
# Config
# -------------------------
SUSPICIOUS_PATHS = [
    "/vendor",
    "/phpunit",
    "/eval-stdin.php",
    "/hello.world",
    "/config.php",
    "/admin",
    "/login",
    "/.env"
]

SUSPICIOUS_PARAM_CHARS = ["%AD", "<?php", "../"]

# Aggressive scanning detection
AGGRESSIVE_THRESHOLD = 10        # Number of suspicious requests
AGGRESSIVE_WINDOW = 60           # seconds
