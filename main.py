import socket
import selectors
import threading
from threading import Event
# import ssl
import os
import json
import signal
import time

from ImageResize import ImageResize

'''
Serwer www, który umozliwia procesowanie w locie zapytań (HTTP -> POST -> multipart/form-data) w celu np. szybszej obróbki przesyłanych obrazów
'''
class HttpsSrv():
    HOST = "0.0.0.0"
    PORT = 8082

    # cerytfikaty dla HTTPS
    # SSL_CERT = "certs/fullchain3.pem"
    # SSL_KEY = "certs/privkey3.pem"

    def __init__(self, ws_pipe_w, datasets, debug=False):
        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #IPv4, TCP
        self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.ws_pipe_w = ws_pipe_w
        self.select = selectors.DefaultSelector()

        self.DATASETS_DIR = datasets
        self.debug = debug

        # uruchomienie serwera z obsługą HTTPS
        # self.server_sock = ssl.wrap_socket(
        #     self.server_sock, server_side=True, keyfile=self.SSL_KEY, certfile=self.SSL_CERT)

        self.event_stop = Event()
        self.server_thread = threading.Thread(target = self.start_server)
        self.server_thread.start()

        # self.json_output = {
        #     'datasets': {
        #         'command': 'upload_files',
        #         'status': 'ok',
        #         'message': '',
        #         'folders': []
        #     }
        # }


    '''
    Funkcja wywoływana w osobnym wątku przypisuje port i adres do
    gniazda oraz rozpoczyna nasłuchiwanie przychodzących połączeń
    '''
    def start_server(self):
        self.server_sock.bind((self.HOST, self.PORT))
        self.server_sock.listen()
        self.server_sock.setblocking(False)
        self.select.register(self.server_sock, selectors.EVENT_READ, data = "server_sock")

        while True:
            if self.event_stop.is_set():
                break
            events = self.select.select(timeout = 2) # timeout for event_stop
            for key, mask in events:
                if key.data == "server_sock":
                    client_connection, client_address = key.fileobj.accept()
                    client_connection.setblocking(False)

                    try:
                        header = self.get_header(client_connection)
                    except socket.error as e:
                        continue

                    # if not header:
                    #     continue

                    request_method = header.split(' ', 1)[0]
                    if request_method == "GET":
                        self.GET(client_connection, header)
                    elif request_method == "POST":
                        self.POST(client_connection, header)

        print('HTTPS_SERVER: END of start_server()')

    '''
    '''
    def POST(self, client: socket.socket, request):
        self.debug_print("START POST")
        total_length = int(self.get_content_len(request))
        type = self.get_content_type(request)
        boundary = self.get_boundary(request)

        # Pomiar czasu obsługi zapytania (parsowania)
        start = time.time()

        if type == "multipart/form-data":
            self.multipart_process(client, boundary, total_length)

        # Wyświetlenie czasu obsługi zapytania
        end = time.time()
        print(end - start)

        # CORS - Access-Control-Allow-Origin: *
        # response = 'HTTP/1.1 200 OK\r\n' + \
        #             'Access-Control-Allow-Origin: *\r\n' + \
        #             '\r\n'

        # response = 'HTTP/1.1 302 OK\r\n\r\n'
        response = 'HTTP/1.1 200 OK\r\n\r\n'

        client.sendall(response.encode())
        client.close()

        self.debug_print("END POST")

        # po pobraniu plików, wysyłam komunikat do klienta o odświeżeniu folderów
        # json_output_str = json.dumps(self.json_output)
        # os.write(self.ws_pipe_w, json_output_str.encode())


    '''
    Parsuje zapytanie POST -> multipart/form-data
    '''
    def multipart_process(self, client: socket.socket, boundary, total_length):
        # wyświatla całe żądanie bez dalszego parsowania 
        # self.debug_print("TOTAL LENGTH:", total_length)
        # self.debug_print("BONDUARY:", boundary)
        # try:
        #     c = client.recv(1024)
        #     while(c):
        #         print(c)
        #         c = client.recv(1024)
        # except socket.error as e:
        #     print("ERRROR: ", e)
        # return

        last_boundary = "--"+boundary+"--"
        self.debug_print("last_boundary: ", last_boundary)

        self.debug_print("B0: ", self.get_line(client), end="")
        self.debug_print("CD0: ", self.get_line(client), end="")
        self.debug_print("E0: ", self.get_line(client), end="")
        folder = self.get_line(client, 'rstrip')
        self.debug_print("FOLDER: ", folder)

        # usuwam wszytkie pliki w folderze
        full_path = os.path.join(self.DATASETS_DIR, folder)
        self.debug_print("full_path", full_path)
        for path in os.listdir(full_path):
            if os.path.isfile(os.path.join(full_path, path)):
                os.remove(os.path.join(full_path, path))

        try:
            for i in range(100):
                # boundary1
                boundary1 = self.get_line(client)
                # if last boundary
                if(boundary1 > last_boundary):
                    self.debug_print("LAST BOUNDARY")
                    break
                self.debug_print("B1: ", boundary1, end="")
                # content_disposition1
                self.debug_print("CD1: ", self.get_line(client), end="")
                # empty
                self.debug_print("E1: ", self.get_line(client), end="")
                #size
                size = int(self.get_line(client))
                self.debug_print("S: ", size)
                # boundary2
                self.debug_print("B2: ", self.get_line(client), end="")
                #content_disposition2
                content_disposition2 = self.get_line(client)
                self.debug_print("CD2: ", content_disposition2, end="")

                filename = self.get_filename(content_disposition2)

                # content_type
                self.debug_print("CT: ", self.get_line(client), end="")
                # empty2
                self.debug_print("E2: ", self.get_line(client), end="")

                #file = client.recv(size)

                file = bytearray()

                recv_len = 1024
                if(size <= recv_len):
                    file = client.recv(size)
                else:
                    while(size > 0):
                        if size < recv_len:
                            recv_len = size
                        ret = client.recv(recv_len)
                        file += ret
                        size -= recv_len

                full_path = os.path.join(self.DATASETS_DIR, folder, filename)
                with open(full_path, "wb") as binary_file:
                    binary_file.write(file)
                ImageResize(full_path, 28, False, True, True)

                # empty3
                self.debug_print("E3: ", self.get_line(client), end="")
        except socket.error as e:
            self.debug_print("ERRROR: ", e)

        # last boundary
        # print("LB: ", self.get_line(client), end="")  
        return 


    '''
    '''
    def get_header(self, client):
        header = ''
        mode = ''
        line = ''

        while(line != '\r\n'): # first empty(new) line after header request
            line = self.get_line(client, mode)
            header += line

        return header
    
    
    '''
    '''
    def get_line(self, client: socket.socket, strip_fun = None):
        line = ''
        l = ''

        while(l != '\n'):
            l = client.recv(1).decode()
            line += l

        if strip_fun == 'rstrip':
            line = line.rstrip()
        elif strip_fun == 'strip':
            line = line.strip()

        return line
        

    '''
    '''
    def get_filename(self, content: str):
        content = content.strip()
        filename = content.split("; ", 3)[2]
        filename = filename.split("=")[1]
        filename = filename.replace("\"", "")

        return filename


    '''
    '''
    def get_content_len(self, request: str):
        lines = request.splitlines()
        for l in lines:
            if "Content-Length" in l:
                key = l.split(": ", 1)
                return key[1]

    '''
    '''
    def get_content_type(self, request: str):
        lines = request.splitlines()
        for l in lines:
            if "Content-Type" in l:
                key = l.split(": ", 1)
                key = key[1].split("; ", 1)
                return key[0]
    
    '''
    '''
    def get_boundary(self, request: str):
        lines = request.splitlines()
        for l in lines:
            if "Content-Type" in l:
                key = l.split("=", 1)
                return key[1]


    '''
    Metoda GET nie jest obsługiwana, zwraca tylko Hello World
    Można dopisać serwowanie pliku index.html
    '''
    def GET(self, client: socket.socket, request):
        response = 'HTTP/1.1 200 OK\n\nHello World'
        client.sendall(response.encode())
        client.close()
            
    
                    
    '''
    Zamyka gniazdo serwera, zamyka selector,
    zatrzymuje pętlę główną w wątku start_server
    '''
    def stop_server(self):
        self.select.close()
        self.server_sock.close()
        self.event_stop.set()
        print('HTTPS_SERVER: stop_server()')

    def debug_print(self, *args, **kwargs):
        if(self.debug):
            print(*args, **kwargs)



if __name__ == "__main__":
    DATASETS_DIR = "datasets/"
    srv = HttpsSrv(None, DATASETS_DIR, True)
    
    try:
        while True:
            user_input = input("Enter Ctrl+C to exit...\n")
    except KeyboardInterrupt:
        srv.stop_server()
        print("\nProgram terminated by user.")