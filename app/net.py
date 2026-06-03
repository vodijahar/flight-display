import json
from time import sleep
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def get_json(url, params=None, timeout=15, attempts=3, headers=None):
    if params:
        url = f"{url}?{urlencode(params)}"

    last_error = None
    for attempt in range(1, attempts + 1):
        try:
            request = Request(url, headers=headers or {})
            with urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            last_error = exc
            if exc.code < 500 or attempt == attempts:
                raise
        except URLError as exc:
            last_error = exc
            if attempt == attempts:
                raise

        sleep(attempt * 2)

    raise last_error
