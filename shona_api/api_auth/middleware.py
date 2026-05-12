class RateLimitHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        headers = getattr(request, "api_rate_limit_headers", None)
        if headers:
            for name, value in headers.items():
                response[name] = value
            wait = getattr(request, "api_rate_limit_wait", None)
            if response.status_code == 429 and wait is not None:
                response["Retry-After"] = str(wait)
        return response
