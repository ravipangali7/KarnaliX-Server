"""
Middleware to exempt /api/ from CSRF so SPA (JWT) can POST without CSRF cookie.
"""


class DisableCSRFForAPIMiddleware:
    """
    Set csrf_processing_done so CsrfViewMiddleware skips checks for /api/ requests.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith("/api/"):
            request.csrf_processing_done = True
        return self.get_response(request)
