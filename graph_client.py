import requests
from msal import ConfidentialClientApplication, PublicClientApplication

from config import Settings


class HttpClientWithTimeout(requests.Session):
    """MSAL-compatible HTTP client that enforces a default timeout for token calls."""

    def __init__(self, timeout: float):
        super().__init__()
        self._default_timeout = timeout

    def send(self, request, **kwargs):
        if kwargs.get("timeout") is None:
            kwargs["timeout"] = self._default_timeout
        return super().send(request, **kwargs)


class GraphClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.base_url = "https://graph.microsoft.com/v1.0/"
        self.auth_mode = settings.auth_mode
        self.http_client = HttpClientWithTimeout(settings.request_timeout)
        if self.auth_mode == "delegated":
            self.app = PublicClientApplication(
                self.settings.client_id,
                authority=self.settings.authority,
                http_client=self.http_client,
            )
            self._delegated_result = None
        else:
            self.app = ConfidentialClientApplication(
                self.settings.client_id,
                authority=self.settings.authority,
                client_credential=self.settings.client_secret,
                http_client=self.http_client,
            )

    def _acquire_token(self) -> str:
        if self.auth_mode == "delegated":
            if self._delegated_result and "access_token" in self._delegated_result:
                return self._delegated_result["access_token"]
            flow = self.app.initiate_device_flow(scopes=self.settings.delegated_scopes)
            if "user_code" not in flow:
                raise RuntimeError(f"Failed to create device flow: {flow}")
            print(
                f"请在浏览器打开 {flow['verification_uri']} 输入代码 {flow['user_code']} 以登录授权。"
            )
            result = self.app.acquire_token_by_device_flow(flow)
            if "access_token" not in result:
                raise RuntimeError(f"Delegated auth failed: {result}")
            self._delegated_result = result
            return result["access_token"]

        result = self.app.acquire_token_for_client(scopes=self.settings.scopes)
        if "access_token" not in result:
            raise RuntimeError(f"Failed to acquire token: {result}")
        return result["access_token"]

    def request(self, method: str, path: str, **kwargs) -> requests.Response:
        token = self._acquire_token()
        headers = kwargs.pop("headers", {})
        headers.setdefault("Authorization", f"Bearer {token}")
        headers.setdefault("Content-Type", "application/json")
        url = self.base_url + path.lstrip("/")

        response = requests.request(
            method,
            url,
            headers=headers,
            timeout=self.settings.request_timeout,
            **kwargs,
        )
        if not response.ok:
            raise RuntimeError(
                f"Graph {method} {path} failed {response.status_code}: {response.text}"
            )
        return response

    def get(self, path: str, **kwargs) -> requests.Response:
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs) -> requests.Response:
        return self.request("POST", path, **kwargs)

    def patch(self, path: str, **kwargs) -> requests.Response:
        return self.request("PATCH", path, **kwargs)

    def delete(self, path: str, **kwargs) -> requests.Response:
        return self.request("DELETE", path, **kwargs)
