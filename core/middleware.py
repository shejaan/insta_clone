import traceback
import sys
from django.http import HttpResponse

class AdminDebugMiddleware:
    """
    Middleware to catch any exceptions, especially on /admin, 
    and print the exact traceback to both the console AND the browser.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        # Intercept before Django turns it into a generic 500 page
        if request.path.startswith('/admin'):
            exc_type, exc_value, exc_traceback = sys.exc_info()
            tb_string = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
            
            print("================ ADMIN CRASH ==================", file=sys.stderr)
            print(tb_string, file=sys.stderr)
            print("===============================================", file=sys.stderr)
            
            safe_tb = tb_string.replace("`", "\\`").replace("$", "\\$")
            return HttpResponse(
                f"""
                <html>
                <body style="font-family: monospace; padding: 20px;">
                    <h2>Admin Page Crashed</h2>
                    <p style="color: red;">Check your Browser Console (F12) for the exact python error!</p>
                    <script>
                        console.error(`===== PYTHON SERVER CRASH =====\\n\\n${{safe_tb}}`);
                    </script>
                    <hr>
                    <pre>{tb_string}</pre>
                </body>
                </html>
                """, 
                status=500
            )
        return None
