# from http.server import BaseHTTPRequestHandler,HTTPServer
# import json

# class MyAPI(BaseHTTPRequestHandler):

#     def do_GET(self): 
#         if self.path == "/test": 
#             self.send_response(200) 
#             self.send_header('Content-Type','application/json') 
#             self.end_headers() 
#             response = {"message": "Hello from pure Python!"}
#             self.wfile.write(json.dumps(response).encode('utf-8'))
#         else:
#             self.send_error(404, "Endpoint Not Found") 

# def run(port=8000):
#     server_address = ('', port)
#     httpd = HTTPServer(server_address, MyAPI)
#     print(f"Starting server on port {port}...")
#     httpd.serve_forever() 

# run()