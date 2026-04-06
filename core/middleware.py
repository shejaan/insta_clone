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
        try:
            response = self.get_response(request)
            return response
        except Exception as e:
            # ONLY intercept for /admin or if we want to debug everything
            if request.path.startswith('/admin'):
                exc_type, exc_value, exc_traceback = sys.exc_info()
                tb_string = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
                
                # Print aggressively to standard out so Render console catches it
                print("================ ADMIN CRASH ==================", file=sys.stderr)
                print(tb_string, file=sys.stderr)
                print("===============================================", file=sys.stderr)
                
                # Also return it to the browser screen AND the browser's DevTools console
                safe_tb = tb_string.replace("`", "\\`").replace("$", "\\$")
                return HttpResponse(
                    f"""
                    <html>
                    <body style="font-family: monospace; padding: 20px;">
                        <h2>Admin Page Crashed</h2>
                        <p style="color: red;">Check your Browser Console (F12) for the exact python error!</p>
                        <script>
                            console.error(`===== PYTHON SERVER CRASH =====\\n\\n${safe_tb}`);
                        </script>
                        <hr>
                        <pre>{tb_string}</pre>
                    </body>
                    </html>
                    """, 
                    status=500
                )
            
            # If not admin, just raise normally
            raise
