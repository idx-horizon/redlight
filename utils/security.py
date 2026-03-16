from flask import request
from urllib.parse import urlparse, urljoin
import logging
from colorama import Fore, Style, init

def is_safe_url(target):
    host_url = urlparse(request.host_url)
    redirect_url = urlparse(urljoin(request.host_url, target))
    return redirect_url.scheme in ("http", "https") and host_url.netloc == redirect_url.netloc

init(autoreset=True)

WHITELIST_IPS = {
    "127.0.0.1",
    "81.103.65.22",
    "::1"
}

SUSPICIOUS_PATHS = [
    "/.env",
    "/vendor",
    "/phpunit",
    "/wp-config",
    "/config.php",
    "/.git"
]


class SecurityFormatter(logging.Formatter):

    def format(self, record):

        message = super().format(record)

        # highlight suspicious paths
        if any(path in message for path in SUSPICIOUS_PATHS):
            return Fore.RED + message + Style.RESET_ALL

        # highlight non-whitelisted IPs
        if "IP=" in message:
            ip = message.split("IP=")[1].split(",")[0]

            if ip not in WHITELIST_IPS:
                return Fore.YELLOW + message + Style.RESET_ALL

        return message
